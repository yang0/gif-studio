"""No fake generator: real substitute footage, immutable subproject, clip cache."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audio_timeline import sha256
from visual_plan import sha256_json
from video_cut import compile_plan,render
from video_critic import inspect
from revision_planner import compile_revision
from revision_execute import create

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg required for real edited MP4 tests")
class ActualRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/"media").mkdir()
        Image.new("RGB",(360,640),"navy").save(self.root/"media"/"a.png")
        Image.new("RGB",(360,640),"beige").save(self.root/"media"/"b.png")
        Image.new("RGB",(360,640),"green").save(self.root/"media"/"rework-b.png")
        (self.root/"audio").mkdir()
        self.audio=self.root/"audio"/"voiceover.wav"
        with wave.open(str(self.audio),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
            w.writeframes(b"\0\0"*48000)
        self.script={"title":"Test","paragraphs":[{"text":"第一句。第二句。"}]}
        self.timeline={"version":1,"source":{"method":"manual_verified","tool_or_reviewer":"fixture"},
              "audio_sha256":sha256(self.audio),"duration_ms":3000,
              "segments":[{"id":"s1","start_ms":0,"end_ms":1500,"text":"第一句。"},
                          {"id":"s2","start_ms":1500,"end_ms":3000,"text":"第二句。"}]}
        self.visual={"version":1,"audio_sha256":sha256(self.audio),
             "timeline_sha256":sha256_json(self.timeline),
             "shots":[
                {"id":"v1","roll":"B","role":"evidence","media_type":"screenshot",
                 "start_ms":0,"end_ms":1500,"audio_segment_ids":["s1"],
                 "source_file":"media/a.png","source_sha256":sha256(self.root/"media"/"a.png"),
                 "visual_event":"Observe original screenshot","cut_reason":"Show input"},
                {"id":"v2","roll":"B","role":"evidence","media_type":"screenshot",
                 "start_ms":1500,"end_ms":3000,"audio_segment_ids":["s2"],
                 "source_file":"media/b.png","source_sha256":sha256(self.root/"media"/"b.png"),
                 "visual_event":"Observe second screenshot","cut_reason":"Show result"}]}
        self.board={"fps":12,"width":360,"height":640,"shots":[]}
        for name,obj in (("script.json",self.script),("audio-timeline.json",self.timeline),
                         ("visual-plan.json",self.visual),("storyboard.json",self.board)):
            (self.root/name).write_text(json.dumps(obj,ensure_ascii=False),encoding="utf-8")
        self.plan=compile_plan(self.root,self.script,self.timeline,self.visual,
                               self.audio,self.board,True)
        (self.root/"video-plan.json").write_text(json.dumps(self.plan),encoding="utf-8")
        self.movie=self.root/"build"/"mixed-preview.mp4"
        render(self.root,self.plan,self.script,self.timeline,self.visual,self.audio,
               self.board,self.movie,allow_mixed=True)
        self.critic=inspect(self.movie,self.plan)
        self.findings={"version":1,"critic_report_sha256":sha256_json(self.critic),
             "source_plan_sha256":sha256_json(self.plan),
             "issues":[{"id":"I-001","shot_id":"v2","issue_type":"narrative_redundancy",
                        "severity":"high","evidence":"Second still shows redundant information without causal change",
                        "proposed_fix":"Replace second still with an actual different factual image",
                        "verification":"View both before and after exported movie and compare the relevant action"}]}
        self.rev=compile_revision(self.findings,self.critic,self.movie,self.plan,"rev-001")
    def test_rework_only_changed_source_and_keep_clip_cache(self):
        payload={"version":1,"revision_id":"rev-001","replacements":{
            "v2":{"source_file":"media/rework-b.png",
                  "source_sha256":sha256(self.root/"media"/"rework-b.png")}}}
        before={(p.name,sha256(p)) for p in (self.root/"build"/"video-preview"/"clips").glob("*.mp4")}
        result=create(self.root,self.rev,self.findings,self.critic,self.movie,self.plan,payload)
        dest=Path(result["project"])
        self.assertEqual(["v1"],result["reused_sources"])
        self.assertEqual(["v2"],result["regenerated_sources"])
        self.assertTrue((dest/"revision-receipt.json").exists())
        self.assertFalse((dest/"quality").exists())
        self.assertEqual("media/b.png",self.visual["shots"][1]["source_file"])
        self.assertNotEqual(read_json(dest/"visual-plan.json")["shots"][1]["source_file"],
                            self.visual["shots"][1]["source_file"])
        self.assertEqual(before,{(p.name,sha256(p)) for p in
                         (dest/"build"/"video-preview"/"clips").glob("*.mp4")})
        revised_plan=read_json(dest/"video-plan.json")
        output=dest/"build"/"new-preview.mp4"
        render(dest,revised_plan,read_json(dest/"script.json"),
               read_json(dest/"audio-timeline.json"),read_json(dest/"visual-plan.json"),
               dest/"audio"/"voiceover.wav",read_json(dest/"storyboard.json"),
               output,allow_mixed=True)
        after={p.name for p in (dest/"build"/"video-preview"/"clips").glob("*.mp4")}
        self.assertEqual(len(before)+1,len(after))
        self.assertTrue(output.stat().st_size>1000)
        with self.assertRaises(FileExistsError):
            create(self.root,self.rev,self.findings,self.critic,self.movie,self.plan,payload)
    def test_real_semantic_recut_creates_new_timeline_without_new_assets(self):
        from semantic_recut import recut
        defect=copy.deepcopy(self.findings)
        defect["issues"][0].update({"issue_type":"mechanical_equal_duration","shot_id":None})
        structural=compile_revision(defect,self.critic,self.movie,self.plan,"rev-retime")
        visual=recut(self.visual,self.timeline,self.script,self.audio,[0,1280,3000])
        payload={"version":1,"revision_id":"rev-retime","replacements":{},
                 "revised_visual_plan":visual}
        result=create(self.root,structural,defect,self.critic,self.movie,self.plan,payload)
        created=Path(result["project"])
        self.assertEqual([],result["regenerated_sources"])
        self.assertEqual(1280,read_json(created/"visual-plan.json")["shots"][0]["end_ms"])
        self.assertEqual(3000,read_json(created/"visual-plan.json")["shots"][-1]["end_ms"])
        self.assertFalse((created/"qa").exists())
        self.assertEqual(1500,self.visual["shots"][0]["end_ms"])
    def test_forged_media_is_blocked(self):
        payload={"version":1,"revision_id":"rev-001","replacements":{
            "v2":{"source_file":"media/rework-b.png","source_sha256":"fake"}}}
        with self.assertRaisesRegex(ValueError,"SHA mismatch"):
            create(self.root,self.rev,self.findings,self.critic,self.movie,self.plan,payload)
        self.assertFalse((self.root/"revisions"/"rev-001"/"project").exists())

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
if __name__=="__main__":
    unittest.main()
