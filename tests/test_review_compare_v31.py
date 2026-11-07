"""Functional offline A/B review page check using real, distinct MP4 bytes."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from review_compare import generate
from video_critic import inspect

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg needed for real MP4 inspection")
class ReviewWorkspaceTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.a=self.root/"before.mp4"
        self.b=self.root/"after.mp4"
        for name,color in ((self.a,"red"),(self.b,"blue")):
            subprocess.run(["ffmpeg","-v","error","-y",
               "-f","lavfi","-i",f"color=c={color}:s=320x480:r=12",
               "-f","lavfi","-i","sine=frequency=330:sample_rate=16000",
               "-t","1.5","-c:v","libx264","-pix_fmt","yuv420p",
               "-c:a","aac","-shortest",str(name)],check=True)
        self.plan={"fps":12,"clips":[{"id":"c1","visual_plan_id":"v1","start_frame":0,
              "duration_frames":18,"media_type":"screenshot","static_source":True}]}
        self.critic=inspect(self.a,self.plan)
    def test_page_links_real_media_and_exports_issue_schema(self):
        out=self.root/"review"/"ab.html"
        result=generate(self.root,self.a,self.b,self.critic,self.plan,out)
        self.assertEqual("READ_ONLY_USER_REVIEW",result["status"])
        text=out.read_text(encoding="utf-8")
        self.assertIn("before.mp4",text)
        self.assertIn("after.mp4",text)
        self.assertIn("defects.json",text)
        self.assertIn("critic_report_sha256",text)
        self.assertIn("v1",text)
        self.assertNotIn("release_approved",text)
    def test_prevent_identical_or_outside_video_review(self):
        with self.assertRaisesRegex(ValueError,"distinct"):
            generate(self.root,self.a,self.a,self.critic,self.plan,self.root/"same.html")
        with self.assertRaises(ValueError):
            generate(self.root,self.a,Path("/etc/hosts"),self.critic,self.plan,self.root/"wrong.html")
    def test_critic_audio_is_evidence_not_speech_proof(self):
        levels=self.critic["loudness_evidence"]
        self.assertTrue(levels["available"])
        self.assertFalse(levels["natural_narration_verified"])
        self.assertTrue(any(x["kind"]=="subtitles_not_provided" for x in self.critic["risks"]))
if __name__=="__main__":unittest.main()
