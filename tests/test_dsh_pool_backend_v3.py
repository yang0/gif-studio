"""Loopback fake DSH server tests: verifies HTTP protocol, not real GPT quality."""
import base64
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"scripts"/"backends"))
from audio_timeline import sha256
from dsh_pool_gif import generate, local_endpoint
from gif_batch import run
from candidate_pool import read
from reference_pack import ROLES

def fixture_gif():
    import io
    frames=[Image.new("RGB",(270,480),color)
            for color in ("red","blue","green","yellow","purple","orange")]
    out=io.BytesIO()
    frames[0].save(out,format="GIF",save_all=True,
                   append_images=frames[1:],duration=180,loop=0)
    return out.getvalue()

class FakeAPI(BaseHTTPRequestHandler):
    requests=[]
    payload=fixture_gif()
    code=200
    def log_message(self,*args):
        pass
    def do_POST(self):
        length=int(self.headers["Content-Length"])
        body=json.loads(self.rfile.read(length))
        self.__class__.requests.append({
            "path":self.path,"body":body,
            "auth":self.headers.get("Authorization")})
        result={"data":[{"b64_json":base64.b64encode(self.__class__.payload).decode("ascii")}]}
        encoded=json.dumps(result).encode("utf-8")
        self.send_response(self.__class__.code)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

class DSHBackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project=Path(self.tmp.name)
        self.server=ThreadingHTTPServer(("127.0.0.1",0),FakeAPI)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        FakeAPI.requests=[]
        FakeAPI.payload=fixture_gif()
        FakeAPI.code=200
        self.settings=patch.dict(os.environ,{
            "GIF_STUDIO_DSH_BASE_URL":f"http://127.0.0.1:{self.server.server_port}/v1",
            "GIF_STUDIO_DSH_API_KEY":"test-key",
            "GIF_STUDIO_DSH_MODEL":"gpt-image-2.6",
            "GIF_STUDIO_GIF_FRAMES":"9",
            "GIF_STUDIO_GIF_FRAME_MS":"200"},clear=False)
        self.settings.start()
        self.addCleanup(self.settings.stop)
        prompts=self.project/"prompts"
        prompts.mkdir()
        (prompts/"wide.txt").write_text("A distinct camera action for this GIF",encoding="utf-8")
        self.tasks={"version":1,"tasks":[{
            "shot_id":"shot-01","candidate_id":"wide",
            "prompt":"prompts/wide.txt",
            "notes":"Actual local HTTP protocol fixture only"}]}

    def test_real_http_bytes_integrated_with_batch_ingestion(self):
        backend=[sys.executable,str(ROOT/"scripts"/"backends"/"dsh_pool_gif.py")]
        result=run(self.project,self.tasks,backend,workers=1,max_attempts=1)
        self.assertEqual(1,result["ingested"],result)
        self.assertFalse(result["visual_approval"])
        self.assertEqual(1,len(FakeAPI.requests))
        r=FakeAPI.requests[0]
        self.assertEqual("/v1/images/generations",r["path"])
        self.assertEqual("Bearer test-key",r["auth"])
        self.assertEqual("gif",r["body"]["output_format"])
        self.assertEqual("9:16",r["body"]["aspect_ratio"])
        self.assertEqual("gpt-image-2.6",r["body"]["model"])
        self.assertEqual("A distinct camera action for this GIF",r["body"]["prompt"])
        entry=read(self.project)["candidates"]["shot-01/wide"]
        self.assertEqual("explicit_tool_argument",entry["prompt_delivery"])
        self.assertTrue((self.project/entry["file"]).is_file())

    def test_static_bytes_rejected_even_if_encoded_as_image(self):
        FakeAPI.payload=b"\x89PNG\r\n\x1a\n"+"not-gif".encode()
        backend=[sys.executable,str(ROOT/"scripts"/"backends"/"dsh_pool_gif.py")]
        result=run(self.project,self.tasks,backend,workers=1,max_attempts=1)
        self.assertEqual(0,result["ingested"])
        self.assertEqual(0,len(read(self.project)["candidates"]))

    def test_reference_image_requests_are_blocked_before_http(self):
        refs={}
        for role in ROLES:
            p=self.project/"refs"/(role+".png")
            p.parent.mkdir(exist_ok=True)
            Image.new("RGB",(256,256),"white").save(p)
            refs[role]={"file":"refs/"+role+".png","sha256":sha256(p)}
        (self.project/"pack.json").write_text(json.dumps({
            "version":1,"character_id":"ip-character",
            "character_description":"Maintain stable design",
            "references":refs}),encoding="utf-8")
        self.tasks["tasks"][0]["reference_pack"]="pack.json"
        backend=[sys.executable,str(ROOT/"scripts"/"backends"/"dsh_pool_gif.py")]
        result=run(self.project,self.tasks,backend,workers=1,max_attempts=1)
        self.assertEqual("blocked",result["results"][0]["status"])
        self.assertIn("does not support reference",result["results"][0]["error"])
        self.assertFalse(FakeAPI.requests)

    def test_nonloopback_endpoint_not_permitted(self):
        with patch.dict(os.environ,{"GIF_STUDIO_DSH_BASE_URL":"https://not-local.example/v1"}):
            with self.assertRaisesRegex(ValueError,"loopback"):
                local_endpoint()

if __name__=="__main__":
    unittest.main()
