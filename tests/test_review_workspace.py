"""Review workspace tests use synthetic GIFs only, never fake GPT generations."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from candidate_pool import add,select,selection_status
from review_workspace import make_html
from render_edit_preview import render

def make_gif(path, colors):
    frames=[Image.new("RGB",(270,480),c) for c in colors]
    frames[0].save(path,format="GIF",save_all=True,
                   append_images=frames[1:],duration=200,loop=0)

def board():
    return {"project_title":"Synthetic clips","width":270*2,"height":480*2,"fps":24,
            "shots":[{"id":"shot-01","duration_sec":1.2,"narration":"这是真实字幕占位",
                      "visual_goal":"Show movement","visual_mode":"visual_metaphor",
                      "motion_plan":["enter","change","leave"]}]}

class ReviewWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.prompt=self.root/"actual-prompt.txt"
        self.prompt.write_text("Specific source prompt",encoding="utf-8")
        self.a=self.root/"actual-take.gif"
        make_gif(self.a,["red","green","blue","yellow","purple","orange"])
        add(self.root,"shot-01","take-a",self.a,self.prompt,
            "test-gif-generator","actual-operation-1",
            "Synthetic video unit test, no claim about GPT")
        self.sb=self.root/"storyboard.json"
        self.sb.write_text(json.dumps(board(),ensure_ascii=False),encoding="utf-8")

    def test_gallery_shows_actual_gif_and_selected_state(self):
        gallery=make_html(self.root,self.sb)
        text=gallery.read_text(encoding="utf-8")
        self.assertIn("candidates/shot-01/take-a.gif",text)
        self.assertIn("read-only",text.lower())
        self.assertIn("ALTERNATIVE",text)
        self.assertNotIn("release_approved",text)
        select(self.root,"shot-01","take-a","Best fit with narrative action")
        text=make_html(self.root,self.sb).read_text(encoding="utf-8")
        self.assertIn("SELECTED",text)
        self.assertIn("Best fit with narrative action",text)

    def test_gallery_escapes_untrusted_notes(self):
        second=self.root/"b.gif"
        make_gif(second,["blue","red","yellow","green","orange","purple"])
        add(self.root,"shot-01","take-b",second,self.prompt,
            "test-gif-generator","actual-operation-2",
            '<img src=x onerror="alert(1)">')
        html=make_html(self.root,self.sb).read_text(encoding="utf-8")
        self.assertIn("&lt;img src=x",html)
        self.assertNotIn('<img src=x onerror=',html)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg unavailable")
    def test_preview_requires_real_selection_and_marks_unreviewed(self):
        out=self.root/"build"/"preview.mp4"
        with self.assertRaisesRegex(ValueError,"No candidate"):
            render(self.root,self.sb,out)
        select(self.root,"shot-01","take-a","Fits narrative motion better")
        report=render(self.root,self.sb,out)
        self.assertTrue(out.is_file())
        self.assertEqual("UNREVIEWED_EDITORIAL_PREVIEW",report["status"])
        self.assertFalse(report["formal_visual_qa_enforced"])
        self.assertTrue(report["candidate_selection_verified"])
        self.assertEqual("take-a",report["shot_candidates"][0]["candidate"])
        self.assertTrue((self.root/"build/editorial-preview-report.json").is_file())

    def test_preview_rejects_tampered_selection(self):
        select(self.root,"shot-01","take-a","Fits narrative motion better")
        with (self.root/"gifs/shot-01.gif").open("ab") as f:
            f.write(b"tampered")
        self.assertFalse(selection_status(self.root,"shot-01")[0])
        with self.assertRaisesRegex(ValueError,"mismatch"):
            render(self.root,self.sb,self.root/"build/preview.mp4")

if __name__=="__main__":
    unittest.main()
