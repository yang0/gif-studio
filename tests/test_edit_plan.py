"""Synthetic edit-decision tests; these do not evaluate creative quality."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from edit_plan import create_plan,validate_plan

def make_gif(path,frames=8,delay=200):
    colors=["#cc5544","#4488cc","#44aa66","#aaaa44"]*3
    ims=[Image.new("RGB",(270,480),color) for color in colors[:frames]]
    ims[0].save(path,format="GIF",save_all=True,
                append_images=ims[1:],duration=delay,loop=0)

def board(seconds=2):
    return {"project_title":"Synthetic editorial test","width":720,"height":1280,
            "fps":24,"shots":[{"id":"shot-01","duration_sec":seconds,
                  "narration":"An actual narration anchor for the cut",
                  "visual_goal":"Show a real visual change",
                  "visual_mode":"visual_metaphor","motion_plan":["begin","move","end"]}]}

def approve_plan(plan):
    plan["review_status"]="approved"
    plan["review_notes"]="Reviewed whole sequence and continuity in a separate video preview"
    for shot in plan["shots"]:
        shot["cut_reason"]="The narration turns to its cause, so the visual event changes"
    return plan

class EditPlanTests(unittest.TestCase):
    def test_long_hold_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            (p/"gifs").mkdir()
            make_gif(p/"gifs/shot-01.gif",frames=5,delay=200)
            script=board(seconds=5)
            plan=approve_plan(create_plan(p,script))
            issues=validate_plan(p,script,plan,require_audio=False)
            self.assertTrue(any("frozen end-frame" in x for x in issues),issues)

    def test_reasoned_edit_plan_passes_preview(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            (p/"gifs").mkdir()
            make_gif(p/"gifs/shot-01.gif",frames=8,delay=200)
            script=board(seconds=2)
            plan=approve_plan(create_plan(p,script))
            self.assertEqual([],validate_plan(p,script,plan,require_audio=False))

    def test_stale_timing_fails(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            (p/"gifs").mkdir()
            make_gif(p/"gifs/shot-01.gif",frames=8,delay=200)
            script=board(seconds=2)
            plan=approve_plan(create_plan(p,script))
            script["shots"][0]["duration_sec"]=2.5
            issues=validate_plan(p,script,plan,require_audio=False)
            self.assertTrue(any("Storyboard changed" in x for x in issues),issues)

    def test_missing_edit_review_fails(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            (p/"gifs").mkdir()
            make_gif(p/"gifs/shot-01.gif",frames=8,delay=200)
            script=board(seconds=2)
            plan=create_plan(p,script)
            issues=validate_plan(p,script,plan,require_audio=False)
            self.assertTrue(any("approved" in x for x in issues),issues)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "ffmpeg tools missing")
    def test_real_audio_duration_mismatch(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            (p/"gifs").mkdir()
            make_gif(p/"gifs/shot-01.gif",frames=8,delay=200)
            script=board(seconds=2)
            # Synthetic sound fixture: NOT speech, only for timeline validation.
            audio=p/"test.wav"
            subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i",
                             "anullsrc=r=16000:cl=mono","-t","3.5",
                             "-c:a","pcm_s16le",str(audio)],check=True)
            plan=approve_plan(create_plan(p,script,audio=audio))
            issues=validate_plan(p,script,plan,audio=audio)
            self.assertTrue(any("Voiceover duration" in x for x in issues),issues)

if __name__=="__main__":
    unittest.main()
