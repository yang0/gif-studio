"""Synthetic tests validate QA enforcement and video output, not GPT image generation."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_srt import render
from inspect_gif import inspect
from validate_storyboard import validate
from qa_gate import shot_quality
from approve_shot import approve


def make_gif(path):
    frames = [Image.new("RGB", (90,160), color) for color in
              ("#efc350", "#3b7f9c", "#be4e47", "#2d634d")]
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=[200]*6, loop=0)


class PipelineTests(unittest.TestCase):
    def test_storyboards(self):
        for name in ("templates/storyboard.json",
                     "examples/ai-judgment/storyboard.json",
                     "examples/compound-interest/storyboard.json"):
            with self.subTest(name=name):
                self.assertEqual([], validate(json.loads(
                    (ROOT/name).read_text(encoding="utf-8"))))

    def test_bad_storyboard(self):
        self.assertTrue(validate({"project_title": "bad", "width":720,
                                  "height":1280, "fps":24,
                                  "shots":[{"id":"../bad","duration_sec":-1}]}))

    def test_timed_subtitles(self):
        data = {"shots":[{"duration_sec":2, "subtitle_cues":[
            {"start_sec":0.5,"end_sec":1.3,"text":"你好"},
            {"start_sec":1.3,"end_sec":2,"text":"世界"}]}]}
        output = render(data)
        self.assertIn("00:00:00,500 --> 00:00:01,300", output)
        self.assertIn("00:00:01,300 --> 00:00:02,000", output)

    def test_qa_hash_and_contact_sheet(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            (p/"gifs").mkdir()
            make_gif(p/"gifs/shot-01.gif")
            status, _ = shot_quality(p, "shot-01")
            self.assertEqual("generated", status)
            result = inspect(p/"gifs/shot-01.gif", .8, .5,
                             p/"qa/sheet.jpg")
            self.assertTrue(result["pass"])
            self.assertTrue((p/"qa/sheet.jpg").is_file())
            (p/"qa").mkdir(exist_ok=True)
            (p/"qa/shot-01.json").write_text(json.dumps(result), encoding="utf-8")
            self.assertEqual("technical_passed", shot_quality(p,"shot-01")[0])
            approve(p, "shot-01", "unit test reviewer", "frames manually checked")
            self.assertEqual("ready", shot_quality(p,"shot-01")[0])
            make_gif(p/"gifs/shot-01.gif")
            # The source might be byte-for-byte identical; alter bytes deterministically.
            with open(p/"gifs/shot-01.gif","ab") as handle:
                handle.write(b"extra")
            self.assertNotEqual("ready", shot_quality(p,"shot-01")[0])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg unavailable")
    def test_hold_and_qa_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            (p/"gifs").mkdir()
            make_gif(p/"gifs/shot-01.gif")
            storyboard={"project_title":"test","width":180,"height":320,"fps":24,
                        "shots":[{"id":"shot-01","duration_sec":2,
                                  "narration":"test","subtitle":"测试",
                                  "visual_goal":"demo",
                                  "visual_mode":"visual_metaphor",
                                  "motion_plan":["reveal","hold"]}]}
            sb=p/"storyboard.json"
            sb.write_text(json.dumps(storyboard),encoding="utf-8")
            cmd=[sys.executable,str(ROOT/"scripts/compose_video.py"),
                 "--project",str(p),"--storyboard",str(sb),
                 "--out",str(p/"final.mp4")]
            result=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(0,result.returncode,"Unreviewed GIF must be blocked")
            qa=inspect(p/"gifs/shot-01.gif", 2, 1.5)
            (p/"qa").mkdir()
            (p/"qa/shot-01.json").write_text(json.dumps(qa),encoding="utf-8")
            approve(p,"shot-01","test reviewer","reviewed synthetic frames")
            subprocess.run(cmd+["--allow-unreviewed"],check=True)
            probe=json.loads(subprocess.check_output(
                ["ffprobe","-v","error","-show_entries",
                 "stream=width,height,codec_name:format=duration",
                 "-of","json",str(p/"final.mp4")],text=True))
            stream=next(s for s in probe["streams"] if "width" in s)
            self.assertEqual((180,320),(stream["width"],stream["height"]))
            self.assertEqual("h264",stream["codec_name"])
            self.assertAlmostEqual(2,float(probe["format"]["duration"]),delta=.15)
            # Hold-frame should retain the last GIF color at the end of the movie.
            raw=subprocess.check_output(
                ["ffmpeg","-v","error","-sseof","-0.15","-i",
                 str(p/"final.mp4"),"-frames:v","1","-f","rawvideo",
                 "-pix_fmt","rgb24","-"])
            self.assertGreater(len(raw),0)


if __name__ == "__main__":
    unittest.main()
