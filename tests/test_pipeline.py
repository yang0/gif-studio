"""Unit and smoke tests; synthetic GIFs avoid external image generation quotas."""
import json
import os
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


class PipelineTests(unittest.TestCase):
    def test_storyboard_examples(self):
        for relative in ("templates/storyboard.json",
                         "examples/compound-interest/storyboard.json",
                         "examples/ai-judgment/storyboard.json"):
            with self.subTest(relative=relative):
                data = json.loads((ROOT / relative).read_text(encoding="utf-8"))
                self.assertEqual([], validate(data))

    def test_rejects_invalid_storyboard(self):
        self.assertTrue(validate({"project_title": "bad", "width": 720,
                                  "height": 1280, "fps": 24,
                                  "shots": [{"id": "../oops", "duration_sec": -1}]}))

    def test_srt_timing(self):
        data = {"shots": [
            {"duration_sec": 1.25, "subtitle": "第一句"},
            {"duration_sec": 2.75, "subtitle": "第二句"}]}
        s = render(data)
        self.assertIn("00:00:01,250 --> 00:00:04,000", s)
        self.assertIn("第一句", s)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "ffmpeg/ffprobe not installed")
    def test_synthetic_gif_to_video(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            gifs = project / "gifs"
            gifs.mkdir()
            # Two images with real motion; identical length for determinism.
            frames = [Image.new("RGB", (90, 160), (255, 190, 50)),
                      Image.new("RGB", (90, 160), (200, 50, 50)),
                      Image.new("RGB", (90, 160), (255, 190, 50)),
                      Image.new("RGB", (90, 160), (200, 50, 50))]
            frames[0].save(gifs / "shot-01.gif", save_all=True, append_images=frames[1:],
                           duration=[200]*4, loop=0)
            report = inspect(gifs / "shot-01.gif", 1.0, 1.0)
            self.assertTrue(report["pass"], report)
            storyboard = {"project_title": "smoke test", "width": 180,
                          "height": 320, "fps": 24,
                          "shots": [{"id": "shot-01", "duration_sec": 2.0,
                                     "narration": "测试", "subtitle": "测试",
                                     "visual_goal": "sample", "visual_mode": "visual_metaphor",
                                     "motion_plan": ["first", "second"]}]}
            sb = project / "storyboard.json"
            sb.write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
            output = project / "final-video.mp4"
            subprocess.run([sys.executable, str(ROOT / "scripts/compose_video.py"),
                            "--project", str(project), "--storyboard", str(sb),
                            "--out", str(output)], check=True)
            self.assertTrue(output.is_file())
            self.assertTrue((project / "subtitles/captions.srt").is_file())
            probe = subprocess.check_output(["ffprobe", "-v", "error",
                  "-show_entries", "stream=width,height,codec_name:format=duration",
                  "-of", "json", str(output)], text=True)
            info = json.loads(probe)
            video = next(s for s in info["streams"] if "width" in s)
            self.assertEqual((180, 320), (video["width"], video["height"]))
            self.assertEqual("h264", video["codec_name"])
            self.assertAlmostEqual(2, float(info["format"]["duration"]), delta=0.15)


if __name__ == "__main__":
    unittest.main()
