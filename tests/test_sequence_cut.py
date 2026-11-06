"""Multi-cut EDL regression tests using real, synthetic-fixture GIF files."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from candidate_pool import add, select, read
from sequence_cut import initialize, verify, render

def gif(path, colors):
    images=[Image.new("RGB",(270,480),c) for c in colors]
    images[0].save(path,format="GIF",save_all=True,
                   append_images=images[1:],duration=200,loop=0)

class SequenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        prompt=self.root/"prompt.txt"
        prompt.write_text("Exact generation prompt",encoding="utf-8")
        a=self.root/"a.gif"; b=self.root/"b.gif"
        gif(a,["red","green","blue","yellow","purple","orange"])
        gif(b,["purple","yellow","orange","blue","green","red"])
        add(self.root,"shot-01","wide",a,prompt,"test-tool","synthetic-a","Wide establishing coverage")
        add(self.root,"shot-01","detail",b,prompt,"test-tool","synthetic-b","Action close-up coverage")
        select(self.root,"shot-01","wide","Good initial perspective")
        self.board=self.root/"storyboard.json"
        self.board.write_text(json.dumps({
            "project_title":"Synthetic EDL","width":540,"height":960,"fps":24,
            "shots":[{"id":"shot-01","duration_sec":1.0,
                      "narration":"One narration split into two visual shots",
                      "visual_goal":"Explain a process",
                      "visual_mode":"visual_metaphor",
                      "motion_plan":["open","move","final"]}]}),encoding="utf-8")

    def split(self):
        seq=initialize(self.root,self.board)
        first=seq["clips"][0]
        first["duration_frames"]=12
        first["cut_reason"]="First show the complete space"
        rec=read(self.root)["candidates"]["shot-01/detail"]
        seq["clips"].append({
            "id":"cut-002","shot_id":"shot-01","candidate_id":"detail",
            "source_sha256":rec["sha256"],"start_frame":12,
            "in_frame":3,"duration_frames":12,
            "narration_anchor":"One narration split into two visual shots",
            "cut_reason":"Cut close when mechanism is revealed"})
        seq["total_frames"]=24
        return seq

    def test_one_narration_two_gif_clips(self):
        seq=self.split()
        self.assertEqual([],verify(self.root,seq))
        self.assertNotEqual(seq["clips"][0]["source_sha256"],seq["clips"][1]["source_sha256"])

    def test_stale_and_out_of_bounds_fails(self):
        seq=self.split()
        seq["clips"][1]["in_frame"]=30
        self.assertTrue(any("exceeds real GIF" in x for x in verify(self.root,seq)))
        seq=self.split()
        seq["clips"][1]["source_sha256"]="0"*64
        self.assertTrue(any("stale" in x for x in verify(self.root,seq)))

    def test_gaps_and_duplicate_ids_fail(self):
        seq=self.split()
        seq["clips"][1]["start_frame"]=20
        seq["clips"][1]["id"]="cut-001"
        issues=verify(self.root,seq)
        self.assertTrue(any("gap" in x for x in issues))
        self.assertTrue(any("duplicate clip" in x for x in issues))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg not installed")
    def test_mp4_preview_is_explicitly_unreviewed(self):
        seq=self.split()
        output=self.root/"build"/"sequence-preview.mp4"
        report=render(self.root,seq,output)
        self.assertTrue(output.is_file())
        self.assertEqual(2,report["clips"])
        self.assertEqual("UNREVIEWED_SEQUENCE_PREVIEW",report["status"])
        self.assertFalse(report["formal_approval"])
        self.assertTrue((self.root/"build/sequence/report.json").is_file())

if __name__=="__main__":
    unittest.main()
