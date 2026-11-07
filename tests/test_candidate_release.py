"""Formal candidate+sequence release gates. Synthetic GIF/audio fixtures are NOT a film."""
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
from candidate_pool import add, read, select
from candidate_review import inspect_candidate, approve_candidate, status
from release_sequence import preflight, release
from final_review import sheet as inspect_final, approve as approve_final
from sequence_cut import initialize

FLAGS={key:True for key in ("semantic","motion","style","composition","continuity")}

def make_gif(path,colors):
    images=[Image.new("RGB",(270,480),color) for color in colors]
    images[0].save(path,format="GIF",save_all=True,
                   append_images=images[1:],duration=200,loop=0)

class CandidateReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        r=self.root
        self.board={"project_title":"Synthetic","width":540,"height":960,"fps":24,
                    "shots":[{"id":"shot-01","duration_sec":1.0,
                              "narration":"The mechanism changes now",
                              "visual_goal":"Visual change",
                              "visual_mode":"visual_metaphor",
                              "motion_plan":["begin","change","end"]}]}
        self.storyboard=r/"storyboard.json"
        self.storyboard.write_text(json.dumps(self.board),encoding="utf-8")
        (r/"style-lock.json").write_text('{"style_id":"hand-drawn"}',encoding="utf-8")
        (r/"director-plan.json").write_text(json.dumps({
            "version":1,"creative_thesis":"Specific causal process shown visually",
            "shots":[{"id":"shot-01","asset_policy":"new_gpt_gif",
                       "visual_proof":"A visible cause leads to a changed result"}]}),encoding="utf-8")
        prompt=r/"source-prompt.txt"
        prompt.write_text("Full exact text tool prompt",encoding="utf-8")
        a=r/"a.gif"; b=r/"b.gif"
        make_gif(a,["red","green","blue","yellow","purple","orange"])
        make_gif(b,["purple","yellow","orange","blue","green","red"])
        add(r,"shot-01","a",a,prompt,"test-gif-tool","synthetic-a",
            "Test coverage A",prompt_delivery="explicit_tool_argument")
        add(r,"shot-01","b",b,prompt,"test-gif-tool","synthetic-b",
            "Test coverage B",prompt_delivery="explicit_tool_argument")
        select(r,"shot-01","a","The first framing fits the setup")
        self.seq=initialize(r,self.storyboard)
        self.seq["clips"][0]["duration_frames"]=12
        self.seq["clips"][0]["cut_reason"]="Establish the context at the start"
        rec=read(r)["candidates"]["shot-01/b"]
        self.seq["clips"].append({
            "id":"cut-002","shot_id":"shot-01","candidate_id":"b",
            "source_sha256":rec["sha256"],"start_frame":12,"in_frame":0,
            "duration_frames":12,"cut_reason":"Switch to mechanism at the turn",
            "narration_anchor":"The mechanism changes now"})
        self.seq["total_frames"]=24
        self.seq["status"]="approved"
        self.seq["review_notes"]="Viewed two-cut sequence and checked the cut reason and pacing"
        self.sequence_file=r/"sequence.json"
        self.sequence_file.write_text(json.dumps(self.seq),encoding="utf-8")
        self.subtitles=r/"captions.srt"
        self.subtitles.write_text("1\n00:00:00,000 --> 00:00:00,950\nThe mechanism changes now\n",
                                  encoding="utf-8")
        self.audio=r/"narration.wav"

    def approve(self,take):
        report=inspect_candidate(self.root,self.storyboard,"shot-01",take)
        self.assertTrue(report["technical_pass"],report)
        result=approve_candidate(self.root,self.storyboard,"shot-01",take,
             "test reviewer","Viewed actual complete synthetic animation, checked all five items",
             FLAGS,"explicit_tool_argument")
        self.assertIn("technical_sha256",result)

    def test_unreviewed_alternative_is_blocked(self):
        self.approve("a")
        state,reason=status(self.root,self.storyboard,"shot-01","b")
        self.assertNotEqual("ready",state)
        faults=preflight(self.root,self.storyboard,self.seq,None,self.subtitles)
        self.assertTrue(any("shot-01/b" in x for x in faults),faults)

    def test_individual_candidate_review_and_hash_invalidation(self):
        self.approve("a")
        self.assertEqual("ready",status(self.root,self.storyboard,"shot-01","a")[0])
        p=self.root/"library"/"prompts"/"shot-01"/"a.txt"
        p.write_text("Tampered candidate prompt",encoding="utf-8")
        self.assertNotEqual("ready",status(self.root,self.storyboard,"shot-01","a")[0])

    def test_context_only_cannot_be_formally_approved(self):
        root=self.root
        source=root/"other.gif"
        make_gif(source,["red","blue","yellow","green","purple","orange"])
        prompt=root/"source-prompt.txt"
        add(root,"shot-01","unverified",source,prompt,"test","context-only-test",
            "No explicit prompt field")
        inspect_candidate(root,self.storyboard,"shot-01","unverified")
        with self.assertRaisesRegex(ValueError,"explicitly documented"):
            approve_candidate(root,self.storyboard,"shot-01","unverified",
                "test reviewer","Observed every full frame of generated GIF in test",
                FLAGS,"explicit_tool_argument")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg is needed for audio + video fixture")
    def test_release_rejects_missing_review_then_renders_pending(self):
        # Silent synthetic audio contains NO speech; verifies only track/timeline behavior.
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                        "-f","lavfi","-i","anullsrc=r=16000:cl=mono",
                        "-t","1.0","-c:a","pcm_s16le",str(self.audio)],check=True)
        self.approve("a")
        with self.assertRaisesRegex(ValueError,"shot-01/b"):
            release(self.root,self.storyboard,self.sequence_file,self.audio,
                    self.subtitles,self.root/"final.mp4")
        self.approve("b")
        result=release(self.root,self.storyboard,self.sequence_file,self.audio,
                       self.subtitles,self.root/"final.mp4")
        self.assertEqual("PENDING_FINAL_VIDEO_REVIEW",result["status"])
        self.assertEqual(2,len(result["sources"]))
        self.assertTrue((self.root/"final.mp4").is_file())
        self.assertTrue(result["has_audio"])
        self.assertTrue(result["burned_subtitles"])
        # The final approval cannot silently reuse review results after
        # a producer changes narration/captions on disk.
        inspect_final(self.root,self.root/"final.mp4")
        self.subtitles.write_text("1\n00:00:00,000 --> 00:00:00,900\nChanged caption\n",
                                  encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"subtitles_source"):
            approve_final(self.root,self.root/"final.mp4","test reviewer",
                          "Reviewed every frame in synthetic fixture; not a production movie",
                          {"semantic":True,"pacing":True,"continuity":True,
                           "subtitles":True,"audio":True})

if __name__=="__main__":
    unittest.main()
