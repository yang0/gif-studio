"""Video critic and local revision planner integration with *real decoded MP4*.

Generated color videos are only synthetic engineering fixtures.
They are not a human-reviewed, release-quality knowledge film.
"""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from video_critic import inspect,review,check_report
from revision_planner import compile_revision,verify_revision
from visual_plan import sha256_json

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg must be present to test actual MP4 frames")
class CriticAndRevisionTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.video=self.root/"test.mp4"
        # Constant images deliberately trigger detectable low-motion and
        # adjacent-duplicate risks; video has actual H264 frames + AAC audio.
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
          "-f","lavfi","-i","color=c=blue:s=320x480:r=12",
          "-f","lavfi","-i","sine=frequency=410:sample_rate=16000",
          "-t","4","-c:v","libx264","-pix_fmt","yuv420p",
          "-c:a","aac","-shortest",str(self.video)],check=True)
        self.plan={"version":1,"fps":12,"clips":[
          {"id":"cut-001","visual_plan_id":"v1","media_type":"screenshot",
           "start_frame":0,"duration_frames":24,"static_source":True},
          {"id":"cut-002","visual_plan_id":"v2","media_type":"gpt_gif",
           "start_frame":24,"duration_frames":24,"static_source":False}
        ]}
        self.report=inspect(self.video,self.plan)
        self.findings={"version":1,
            "critic_report_sha256":sha256_json(self.report),
            "source_plan_sha256":sha256_json(self.plan),
            "issues":[{"id":"I-001","issue_type":"narrative_redundancy",
             "severity":"high","shot_id":"v2",
             "evidence":"Second shot repeats a title card while narration asks for an explanation",
             "proposed_fix":"Replace second shot with a visible causal action that explains the interruption",
             "verification":"Review start, trigger, and outcome at two actual output timestamps"}]}

    def test_critic_is_unapproved_and_reports_duplicate_risk(self):
        self.assertFalse(self.report["approved"])
        self.assertEqual("TECHNICAL_RISK_REPORT_UNREVIEWED",self.report["status"])
        self.assertTrue(self.report["technical"]["video"])
        self.assertTrue(self.report["technical"]["audio"])
        self.assertTrue(any(x["kind"]=="adjacent_visual_similarity" for x in self.report["risks"]))
        self.assertIn("cut_seam_frame_difference",self.report["observations"][1])
        self.assertIn("knowledge truth",self.report["cannot_assess"])

    def test_review_needs_actual_attestation_and_cannot_auto_pass(self):
        scores={x:9 for x in ("content","visual","pacing","audio","continuity")}
        flags={x:False for x in ("knowledge_error","provenance_misrepresentation","severe_av_desync")}
        notes="Watched every scene and listened to the full generated test audio; this is only a simulated QA record."
        with self.assertRaisesRegex(ValueError,"full-video watch"):
            review(self.report,self.video,"test reviewer",notes,scores,flags)
        result=review(self.report,self.video,"test reviewer",notes,scores,flags,True)
        self.assertTrue(result["eligible_for_independent_final_review"])
        self.assertNotEqual("release_approved",result["status"])
        scores["audio"]=1
        result=review(self.report,self.video,"test reviewer",notes,scores,flags,True)
        self.assertEqual("HUMAN_REWORK_REQUIRED",result["status"])
        self.assertFalse(result["eligible_for_independent_final_review"])

    def test_critic_rejects_invalid_edl_before_decoding(self):
        invalid=[
            ({"start_frame":-1}, "Invalid clip frame bounds"),
            ({"start_frame":12}, "Non-contiguous clip timeline"),
            ({"start_frame":25}, "Non-contiguous clip timeline"),
            ({"duration_frames":0}, "Invalid clip frame bounds"),
            ({"duration_frames":1000}, "extends beyond actual decoded movie"),
        ]
        for patch,message in invalid:
            with self.subTest(patch=patch):
                plan=copy.deepcopy(self.plan)
                plan["clips"][0].update(patch)
                with self.assertRaisesRegex(ValueError,message):
                    inspect(self.video,plan)
        plan=copy.deepcopy(self.plan)
        plan["fps"]=True
        with self.assertRaisesRegex(ValueError,"integer positive fps"):
            inspect(self.video,plan)
        plan=copy.deepcopy(self.plan)
        plan["clips"][1]=None
        with self.assertRaisesRegex(ValueError,"must be an object"):
            inspect(self.video,plan)

    def test_changed_mp4_invalidates_evidence(self):
        mutated=self.root/"different.mp4"
        mutated.write_bytes(self.video.read_bytes()+b"changed")
        with self.assertRaisesRegex(ValueError,"stale"):
            check_report(self.report,mutated,self.plan)

    def test_revisions_keep_unaffected_sources_and_invalidate_previews(self):
        result=compile_revision(self.findings,self.report,self.video,self.plan,"rev-001")
        self.assertEqual(["v2"],result["regenerate_source_shots"])
        self.assertEqual(["v1"],result["reusable_source_shots"])
        self.assertIn("final_review",result["invalidate"])
        self.assertEqual("PLANNED_NOT_EXECUTED",result["status"])
        self.assertTrue(verify_revision(result,self.findings,self.report,self.video,self.plan))
        changed=copy.deepcopy(self.findings)
        changed["issues"][0]["evidence"]="Actual other observation from a different revision of the timeline"
        with self.assertRaisesRegex(ValueError,"different critic analysis|immutable source"):
            verify_revision(result,changed,self.report,self.video,self.plan)

    def test_audio_defect_invalidates_alignment_and_subtitles(self):
        findings=copy.deepcopy(self.findings)
        findings["issues"][0].update({"issue_type":"bad_narration","shot_id":None})
        result=compile_revision(findings,self.report,self.video,self.plan,"rev-audio")
        self.assertIn("audio_timeline",result["invalidate"])
        self.assertIn("subtitles",result["invalidate"])
        self.assertEqual(["v1","v2"],result["reusable_source_shots"])

if __name__=="__main__":
    unittest.main()
