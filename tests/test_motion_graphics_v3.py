"""Genuine original information motion templates, not fake GPT animations."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from motion_graphics import validate,render
from audio_timeline import sha256
from PIL import Image

class MotionGraphicsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def spec(self,kind):
        if kind=="metric":
            return {"version":1,"template":"metric","title":"Actual statistic",
                    "value":42,"start_value":0,"unit":"%"}
        return {"version":1,"template":kind,"title":"A real informative title",
                "items":[{"label":"First","value":42},{"label":"Second","value":79}]}

    def test_four_distinct_template_variants_validate(self):
        for kind in ("process","comparison","timeline","metric"):
            with self.subTest(kind=kind):
                self.assertEqual(kind,validate(self.spec(kind))["template"])

    def test_unproven_numbers_and_missing_title_rejected(self):
        s=self.spec("comparison")
        s["items"][0]["value"]="42"
        with self.assertRaisesRegex(ValueError,"nonnegative numbers"):
            validate(s)
        s=self.spec("metric")
        s["title"]=""
        with self.assertRaisesRegex(ValueError,"title"):
            validate(s)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg required to exercise actual motion video output")
    def test_four_templates_export_real_videos_and_provenance(self):
        for kind in ("process","comparison","timeline","metric"):
            with self.subTest(kind=kind):
                out=self.root/(kind+".mp4")
                report=render(self.spec(kind),out,fps=12,width=360,
                              height=640,duration=.75)
                self.assertTrue(out.is_file())
                self.assertEqual(sha256(out),report["source_sha256"])
                self.assertTrue(report["not_character_animation"])
                self.assertEqual(9,report["duration_frames"])
                self.assertTrue(out.with_suffix(".mp4.motion.json").is_file())
                with self.assertRaises(FileExistsError):
                    render(self.spec(kind),out,fps=12,width=360,
                           height=640,duration=.75)

if __name__=="__main__":
    unittest.main()
