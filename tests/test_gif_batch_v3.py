"""Real subprocess/file-protocol tests. Synthetic fixtures are NOT GPT output."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from gif_batch import run
from audio_timeline import sha256
from candidate_pool import read
from reference_pack import ROLES

BACKEND_SCRIPT=r'''import json,sys
from pathlib import Path
from PIL import Image
if sys.argv[-1]=="--capabilities":
    print(json.dumps({"version":1,"gif":True,"explicit_prompt":True,
                      "reference_images":True}))
    sys.exit(0)
if sys.argv[-1]!="--generate":sys.exit(3)
payload=json.loads(sys.stdin.read())
work=Path(payload["output_directory"])
if "fail" in payload["candidate_id"]:
    (work/"failed-marker.txt").write_text("failure")
    print("Synthetic temporary error",file=sys.stderr)
    sys.exit(12)
if "wrong-hash" in payload["candidate_id"]:
    print(json.dumps({"version":1,"tool":"test-gif-generator",
                      "output_reference":"fixture","prompt_sha256":"wrong",
                      "reference_pack_sha256":payload["reference_pack_sha256"]}))
    sys.exit(0)
colors=["red","blue","green","yellow","purple","orange"]
frames=[Image.new("RGB",(270,480),color) for color in colors]
path=work/"generated.gif"
frames[0].save(path,format="GIF",save_all=True,append_images=frames[1:],
               duration=200,loop=0)
print(json.dumps({"version":1,"tool":"test-gif-generator","output_reference":
                  "synthetic-fixture-"+payload["candidate_id"],
                  "prompt_sha256":payload["prompt_sha256"],
                  "reference_pack_sha256":payload["reference_pack_sha256"],
                  "attached_reference_sha256":{k:v["sha256"]
                  for k,v in payload["references"].items()},
                  "gif_path":str(path)}))
'''

class BatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project=Path(self.tmp.name)
        self.backend=self.project/"backend_test.py"
        self.backend.write_text(BACKEND_SCRIPT,encoding="utf-8")
        self.command=[sys.executable,str(self.backend)]
        p=self.project/"prompts";p.mkdir()
        (p/"a.txt").write_text("Exact first prompt, different visual action",encoding="utf-8")
        (p/"b.txt").write_text("Exact second prompt, separate close-up",encoding="utf-8")
        self.tasks={"version":1,"tasks":[
             {"shot_id":"shot-01","candidate_id":"wide","prompt":"prompts/a.txt",
              "notes":"Wide establishing shot test"},
             {"shot_id":"shot-01","candidate_id":"detail","prompt":"prompts/b.txt",
              "notes":"Detail view test"}]}

    def test_two_real_gif_files_ingested_and_resumed(self):
        out=run(self.project,self.tasks,self.command,workers=2)
        self.assertEqual(2,out["ingested"],out)
        self.assertFalse(out["visual_approval"])
        catalog=read(self.project)
        self.assertEqual(2,len(catalog["candidates"]))
        self.assertEqual("explicit_tool_argument",
                         catalog["candidates"]["shot-01/wide"]["prompt_delivery"])
        again=run(self.project,self.tasks,self.command,workers=2)
        self.assertTrue(all(x["status"]=="already_ingested" for x in again["results"]))

    def test_one_fail_does_not_prevent_other_candidate_and_resume_budget(self):
        self.tasks["tasks"][0]["candidate_id"]="fail"
        out=run(self.project,self.tasks,self.command,workers=2,max_attempts=2)
        self.assertEqual(1,out["ingested"],out)
        failed=next(x for x in out["results"] if x["key"]=="shot-01/fail")
        self.assertEqual("failed",failed["status"])
        self.assertEqual(2,failed["attempts"])
        retried=run(self.project,self.tasks,self.command,max_attempts=2)
        self.assertEqual("attempts_exhausted",
                         next(x for x in retried["results"] if x["key"]=="shot-01/fail")["status"])

    def test_rejects_mismatched_receipt_and_changed_prompt(self):
        self.tasks["tasks"]=[dict(self.tasks["tasks"][0],candidate_id="wrong-hash")]
        out=run(self.project,self.tasks,self.command,max_attempts=2)
        self.assertEqual(0,out["ingested"])
        self.assertEqual("blocked",out["results"][0]["status"])
        self.assertEqual(0,len(read(self.project)["candidates"]))
        (self.project/"prompts"/"a.txt").write_text("Modified")
        out=run(self.project,self.tasks,self.command,max_attempts=2)
        self.assertEqual("blocked",out["results"][0]["status"])
        self.assertTrue("Input changed" in out["results"][0]["error"] or "Request exists and is different" in out["results"][0]["error"])

    def test_ref_pack_sent_with_all_five_sha(self):
        refs={}
        for role in ROLES:
            path=self.project/"refs"/(role+".png")
            path.parent.mkdir(exist_ok=True)
            Image.new("RGB",(256,256),"white").save(path)
            refs[role]={"file":"refs/"+role+".png","sha256":sha256(path)}
        pack=self.project/"pack.json"
        pack.write_text(json.dumps({"version":1,"character_id":"char-a",
             "character_description":"Stable original cartoon persona",
             "references":refs}),encoding="utf-8")
        self.tasks["tasks"]=self.tasks["tasks"][:1]
        self.tasks["tasks"][0]["reference_pack"]="pack.json"
        out=run(self.project,self.tasks,self.command,workers=1)
        self.assertEqual(1,out["ingested"],out)
        status=json.loads((self.project/"production"/"batch"/"shot-01"/"wide.json").read_text())
        self.assertEqual(sha256(pack),status["reference_sha256"])

    def test_invalid_manifest_rejected(self):
        task=self.tasks["tasks"][0]
        self.tasks["tasks"].append(dict(task))
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            run(self.project,self.tasks,self.command)

if __name__=="__main__":
    unittest.main()
