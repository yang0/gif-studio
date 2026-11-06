import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audit_script import audit

class NarrativeTests(unittest.TestCase):
    def setUp(self):
        self.script=json.loads((ROOT/"templates/script.json").read_text(encoding="utf-8"))
    def test_example_valid(self):
        self.assertTrue(audit(self.script)["pass"])
    def test_storyboard_text_unchanged(self):
        text="".join(p["text"] for p in self.script["paragraphs"])
        board={"shots":[{"narration":text[:20]},{"narration":text[20:]}]}
        self.assertTrue(audit(self.script,board)["pass"])
        board["shots"][1]["narration"]="不同的口播"
        self.assertFalse(audit(self.script,board)["pass"])
    def test_duplicate_id(self):
        self.script["paragraphs"][1]["id"]="p1"
        self.assertFalse(audit(self.script)["pass"])
