"""Tests real file hashing and explicit generator handoff, never model fidelity."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audio_timeline import sha256
from reference_pack import ROLES, validate as validate_pack
from generator_adapter import request, ingest
from candidate_pool import read

class GeneratorHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.prompt=self.root/"real-prompt.txt"
        self.prompt.write_text("A person with a specified outfit walking in one original scene",
                               encoding="utf-8")
        self.images={}
        for role in ROLES:
            p=self.root/"refs"/(role+".png")
            p.parent.mkdir(exist_ok=True)
            Image.new("RGB",(256,256),"white").save(p)
            self.images[role]={"file":"refs/"+role+".png","sha256":sha256(p)}
        self.pack=self.root/"reference-pack.json"
        self.pack.write_text(json.dumps({
            "version":1,"character_id":"char-1",
            "character_description":"Fixed identity and consistent outfit",
            "references":self.images}),encoding="utf-8")
        self.gif=self.root/"actual.gif"
        frames=[Image.new("RGB",(270,480),c)
                for c in ("red","green","blue","yellow","purple","orange")]
        frames[0].save(self.gif,format="GIF",save_all=True,
                       append_images=frames[1:],duration=180,loop=0)
        self.receipt=self.root/"tool-receipt.json"

    def receipt_write(self,delivery="explicit_tool_argument"):
        request_data=json.loads((self.root/"production/requests/shot-01/take-01.json").read_text())
        self.receipt.write_text(json.dumps({
            "version":1,"tool":"fixture-model-adapter",
            "output_reference":"synthetic-file-001",
            "prompt_sha256":request_data["prompt_sha256"],
            "reference_pack_sha256":request_data["reference_pack_sha256"],
            "prompt_delivery":delivery}),encoding="utf-8")

    def test_reference_pack_detects_modified_image(self):
        self.assertEqual([],validate_pack(self.root,json.loads(self.pack.read_text())))
        img=self.root/"refs"/"front.png"
        Image.new("RGB",(256,256),"black").save(img)
        self.assertTrue(any("hash" in x for x in validate_pack(
            self.root,json.loads(self.pack.read_text()))))

    def test_generator_handoff_and_candidate_import(self):
        req=request(self.root,"shot-01","take-01",self.prompt,self.pack)
        self.assertEqual("awaiting_actual_generator_call",req["status"])
        self.receipt_write()
        record=ingest(self.root,"shot-01","take-01",self.gif,self.receipt,
                      "Actual GIF fixture only, not vision approval")
        self.assertEqual("candidate_recorded_unreviewed",record["status"])
        self.assertTrue(record["gif_technical_check"]["pass"])
        self.assertEqual("explicit_tool_argument",read(self.root)["candidates"]["shot-01/take-01"]["prompt_delivery"])
        self.assertTrue(record["tool_receipt_is_unverified_external_declaration"])

    def test_refuse_receipt_with_wrong_prompt_or_changed_reference(self):
        request(self.root,"shot-01","take-01",self.prompt,self.pack)
        self.receipt_write()
        value=json.loads(self.receipt.read_text())
        value["prompt_sha256"]="deadbeef"
        self.receipt.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,"prompt hash"):
            ingest(self.root,"shot-01","take-01",self.gif,self.receipt,"real GIF fixture")
        self.receipt_write()
        Image.new("RGB",(256,256),"red").save(self.root/"refs"/"scene.png")
        with self.assertRaisesRegex(ValueError,"Reference images changed"):
            ingest(self.root,"shot-01","take-01",self.gif,self.receipt,"real GIF fixture")

    def test_protects_candidate_ids(self):
        with self.assertRaises(ValueError):
            request(self.root,"../outside","take",self.prompt)
        with self.assertRaises(ValueError):
            request(self.root,"shot","../outside",self.prompt)

if __name__=="__main__":
    unittest.main()
