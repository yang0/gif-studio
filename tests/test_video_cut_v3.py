"""Audio-first mixed-media preview tests: actual GIF/video/screenshot file bytes.

Synthetic fixtures demonstrate timeline/FFmpeg behavior ONLY, not real video quality.
"""
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
from candidate_pool import add
from video_cut import compile_plan, render, validate_compiled
from audio_subtitles import generate as generate_srt

class MixedMediaEditorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.audio=self.root/"voice.wav"
        with wave.open(str(self.audio),"wb") as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
            f.writeframes(b"\x00\x00"*32000)
        self.script={"paragraphs":[{"id":"p1","text":"开始演示解释步骤"}]}
        self.timeline={"version":1,"source":{"method":"manual_verified","tool_or_reviewer":"Fixture test"},
                       "audio_sha256":sha256(self.audio),"duration_ms":2000,
                       "segments":[{"id":"s001","start_ms":0,"end_ms":600,"text":"开始"},
                                   {"id":"s002","start_ms":600,"end_ms":1300,"text":"演示"},
                                   {"id":"s003","start_ms":1300,"end_ms":2000,"text":"解释步骤"}]}
        gif=self.root/"original.gif"
        frames=[Image.new("RGB",(270,480),x) for x in
                ["red","blue","green","yellow","purple","orange"]]
        frames[0].save(gif,format="GIF",save_all=True,
                       append_images=frames[1:],duration=200,loop=0)
        prompt=self.root/"prompt.txt"
        prompt.write_text("A visible physical action in real GIF frames",encoding="utf-8")
        add(self.root,"shot-01","actual-gif",gif,prompt,"fixture","fixture-01",
            "Real animated GIF file test fixture")
        self.video=self.root/"media"/"real-recording.mp4"
        self.video.parent.mkdir()
        self.still=self.root/"media"/"real-screenshot.png"
        Image.new("RGB",(320,240),"orange").save(self.still)
        self.visual={"version":1,"audio_sha256":sha256(self.audio),
                     "timeline_sha256":sha256_json(self.timeline),
                     "shots":[
          {"id":"v1","start_ms":0,"end_ms":600,"audio_segment_ids":["s001"],
           "roll":"A","role":"character_action","media_type":"gpt_gif",
           "source_shot_id":"shot-01","candidate_id":"actual-gif",
           "visual_event":"Animated scene establishes a character","cut_reason":"Establish scene"},
          {"id":"v2","start_ms":600,"end_ms":1300,"audio_segment_ids":["s002"],
           "roll":"B","role":"demo","media_type":"screen_recording",
           "source_file":"media/real-recording.mp4","source_sha256":None,
           "visual_event":"Actual recording demonstrates action","cut_reason":"Show proof"},
          {"id":"v3","start_ms":1300,"end_ms":2000,"audio_segment_ids":["s003"],
           "roll":"B","role":"evidence","media_type":"screenshot",
           "source_file":"media/real-screenshot.png","source_sha256":sha256(self.still),
           "visual_event":"Still screenshot provides exact evidence","cut_reason":"Show original document"}]}
        self.board={"project_title":"Fixture","fps":20,"width":540,"height":960,
                    "shots":[{"id":"shot-01","duration_sec":2,"narration":"开始演示解释步骤"}]}
        (self.root/"script.json").write_text(json.dumps(self.script,ensure_ascii=False),encoding="utf-8")
        (self.root/"storyboard.json").write_text(json.dumps(self.board,ensure_ascii=False),encoding="utf-8")
        (self.root/"audio-timeline.json").write_text(json.dumps(self.timeline,ensure_ascii=False),encoding="utf-8")
        (self.root/"visual-plan.json").write_text(json.dumps(self.visual,ensure_ascii=False),encoding="utf-8")

    def create_video(self):
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
            "-f","lavfi","-i","testsrc=size=320x240:rate=20",
            "-t","1.2","-pix_fmt","yuv420p",str(self.video)],check=True)
        self.visual["shots"][1]["source_sha256"]=sha256(self.video)
        (self.root/"visual-plan.json").write_text(json.dumps(self.visual,ensure_ascii=False),encoding="utf-8")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg required for actual video fixture")
    def test_compile_and_render_three_distinct_media_types(self):
        self.create_video()
        plan=compile_plan(self.root,self.script,self.timeline,self.visual,
                          self.audio,self.board,allow_mixed=True)
        self.assertEqual(["gpt_gif","screen_recording","screenshot"],
                         [x["media_type"] for x in plan["clips"]])
        self.assertEqual([0,12,26],[x["start_frame"] for x in plan["clips"]])
        self.assertEqual(40,plan["total_frames"])
        srt=self.root/"captions.srt"
        generate_srt(self.root,self.root/"script.json",self.root/"audio-timeline.json",self.audio,srt)
        result=render(self.root,plan,self.script,self.timeline,self.visual,
                      self.audio,self.board,self.root/"preview.mp4",subtitles=srt,
                      allow_mixed=True)
        self.assertTrue((self.root/"preview.mp4").is_file())
        self.assertEqual("UNREVIEWED_MIXED_PREVIEW",result["status"])
        self.assertTrue(result["contains_explicit_stills"])
        self.assertTrue(result["subtitles_burned"])
        self.assertFalse(result["formal_approval"])
        raw=subprocess.check_output(["ffprobe","-v","error","-show_streams",
                                     "-of","json",str(self.root/"preview.mp4")],text=True)
        streams=json.loads(raw)["streams"]
        self.assertIn("audio",[s["codec_type"] for s in streams])
        self.assertIn("video",[s["codec_type"] for s in streams])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg required for actual video fixture")
    def test_refuses_subtitle_tampering(self):
        self.create_video()
        plan=compile_plan(self.root,self.script,self.timeline,self.visual,
                          self.audio,self.board,allow_mixed=True)
        srt=self.root/"captions.srt"
        generate_srt(self.root,self.root/"script.json",self.root/"audio-timeline.json",
                     self.audio,srt)
        srt.write_text("1\n00:00:00,000 --> 00:00:00,600\nChanged words\n",
                       encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"Invalid SRT"):
            render(self.root,plan,self.script,self.timeline,self.visual,
                   self.audio,self.board,self.root/"tampered.mp4",subtitles=srt,
                   allow_mixed=True)
        self.assertFalse((self.root/"tampered.mp4").exists())

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg required for actual video fixture")
    def test_reject_stale_source_and_visual_plan(self):
        self.create_video()
        plan=compile_plan(self.root,self.script,self.timeline,self.visual,
                          self.audio,self.board,allow_mixed=True)
        Image.new("RGB",(320,240),"blue").save(self.still)
        with self.assertRaisesRegex(ValueError,"source changed"):
            validate_compiled(self.root,plan,self.audio,self.script,
                              self.timeline,self.visual,self.board,True)
        Image.new("RGB",(320,240),"orange").save(self.still)
        altered=json.loads(json.dumps(self.visual))
        altered["shots"][2]["cut_reason"]="Different edit interpretation"
        with self.assertRaisesRegex(ValueError,"differs"):
            validate_compiled(self.root,plan,self.audio,self.script,
                              self.timeline,altered,self.board,True)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg required for actual video fixture")
    def test_mixed_media_needs_explicit_permission(self):
        self.create_video()
        with self.assertRaisesRegex(ValueError,"allow-mixed-media"):
            compile_plan(self.root,self.script,self.timeline,self.visual,
                         self.audio,self.board,allow_mixed=False)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg required")
    def test_real_information_motion_and_camera_presets(self):
        from motion_graphics import render as render_graphic
        graphic=self.root/"media"/"real-information.mp4"
        render_graphic({"version":1,"template":"process","title":"Three steps",
                        "items":[{"label":"See"},{"label":"Compare"},{"label":"Verify"}]},
                       graphic,fps=20,width=360,height=640,duration=1.1)
        self.visual["shots"][1]["media_type"]="data_motion"
        self.visual["shots"][1]["role"]="process"
        self.visual["shots"][1]["source_file"]="media/real-information.mp4"
        self.visual["shots"][1]["source_sha256"]=sha256(graphic)
        self.visual["shots"][0]["camera_preset"]="closeup"
        self.visual["shots"][0]["character_id"]="one-real-character"
        plan=compile_plan(self.root,self.script,self.timeline,self.visual,
                          self.audio,self.board,allow_mixed=True)
        self.assertEqual("data_motion",plan["clips"][1]["media_type"])
        self.assertEqual("closeup",plan["clips"][0]["camera_preset"])
        result=render(self.root,plan,self.script,self.timeline,self.visual,
                      self.audio,self.board,self.root/"motion-preview.mp4",
                      allow_mixed=True)
        self.assertIn("data_motion",result["media_types"])
        self.assertFalse(result["formal_approval"])
        meta=graphic.with_suffix(".mp4.motion.json")
        meta.unlink()
        with self.assertRaisesRegex(ValueError,"provenance"):
            validate_compiled(self.root,plan,self.audio,self.script,
                              self.timeline,self.visual,self.board,True)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg required")
    def test_mixed_release_requires_each_real_shot_review(self):
        from mixed_release import source_review, release,verify_release,CHECKS
        from final_review import sheet as inspect_final,approve as approve_final
        self.create_video()
        # v3.1 opt-in requires a semantic director decision *and* a separate
        # explicitly declared full-video quality review before final signing.
        from visual_director import validate as validate_director
        from video_critic import inspect as critic_inspect, review as critic_review
        from visual_plan import sha256_json
        director_shots=[]
        for i,base in enumerate(self.visual["shots"]):
            director_shots.append({
              "shot_id":base["id"],"start_ms":base["start_ms"],
              "end_ms":base["end_ms"],
              "narrative_function":"establish" if i==0 else "explain_process",
              "visual_strategy":["scene_acting","product_demonstration","mechanism_breakdown"][i],
              "viewer_takeaway":f"Knowledge gained from actual scene {i}",
              "scene_intent":f"Show meaningful activity in actual footage {i}",
              "visual_subject":f"Real test source {i}",
              "initial_state":f"Before actual action {i}",
              "trigger_event":f"Physical action or reveal {i}",
              "final_state":f"After observable action {i}",
              "new_information":f"New information from image sequence {i}",
              "cut_reason":f"Audio semantics require cut {i}",
              "movement_type":"physical_action" if i==0 else "real_demonstration",
              "source_policy":"use_existing",
              "preferred_media":base["media_type"],
              **({"performance":{"character_id":"fixture-character",
                    "intention":"Work","action":"Do a real action",
                    "emotion_change":"Focused to engaged",
                    "prop_interaction":"Use an actual phone"}} if i==0 else {})
            })
        director={"version":2,"status":"DIRECTOR_DRAFT_UNREVIEWED",
            "audio_timeline_sha256":sha256_json(self.timeline),
            "visual_plan_sha256":sha256_json(self.visual),
            "shots":director_shots}
        self.assertEqual([],validate_director(director,self.timeline,self.visual))
        (self.root/"director-v2.json").write_text(
            json.dumps(director,ensure_ascii=False),encoding="utf-8")
        plan=compile_plan(self.root,self.script,self.timeline,self.visual,
                          self.audio,self.board,allow_mixed=True)
        self.assertEqual(sha256_json(director),plan["director_plan_sha256"])
        # Changing the director decisions after clip compilation rejects reuse.
        changed=json.loads(json.dumps(director))
        changed["shots"][1]["preferred_media"]="screenshot"
        (self.root/"director-v2.json").write_text(json.dumps(changed),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"editor media"):
            validate_compiled(self.root,plan,self.audio,self.script,self.timeline,
                              self.visual,self.board,True)
        (self.root/"director-v2.json").write_text(json.dumps(director),encoding="utf-8")
        (self.root/"video-plan.json").write_text(json.dumps(plan),encoding="utf-8")
        srt=self.root/"subtitles"/"captions.srt"
        srt.parent.mkdir()
        generate_srt(self.root,self.root/"script.json",self.root/"audio-timeline.json",
                     self.audio,srt)
        movie=self.root/"build"/"mixed-preview.mp4"
        render(self.root,plan,self.script,self.timeline,self.visual,self.audio,self.board,
               movie,subtitles=srt,allow_mixed=True)
        with self.assertRaisesRegex(ValueError,"Unreviewed mixed shot"):
            release(self.root,plan,self.script,self.timeline,self.visual,self.audio,
                    self.board,srt,movie)
        checks={k:True for k in CHECKS}
        for clip in plan["clips"]:
            source_review(self.root,clip,plan,"fixture reviewer",
                          "Observed source media and checked footage, legibility and continuity",
                          checks)
        report=release(self.root,plan,self.script,self.timeline,self.visual,self.audio,
                       self.board,srt,movie)
        self.assertEqual("PENDING_FINAL_VIDEO_REVIEW",report["status"])
        self.assertEqual(3,len(report["shots"]))
        formal=self.root/"build"/"formal-mixed"/"final.mp4"
        self.assertTrue(formal.is_file())
        self.assertNotEqual(formal,movie)
        inspect_final(self.root,formal,frames=3)
        (self.root/"sequence.json").write_text('{"version":2}',encoding="utf-8")
        checks={key:True for key in ("semantic","pacing","continuity","subtitles","audio")}
        with self.assertRaisesRegex(ValueError,"v3.1 final approval requires"):
            approve_final(self.root,formal,"fixture reviewer",
                "Checked entire synthetic movie, this remains a fixture",checks)
        critic=critic_inspect(formal,plan)
        quality=self.root/"quality"
        quality.mkdir()
        (quality/"critic.json").write_text(json.dumps(critic),encoding="utf-8")
        human=critic_review(critic,formal,"CI fixture reviewer",
            "This is a signed fixture observation, not true evidence of publishable creative quality.",
            {key:9 for key in ("content","visual","pacing","audio","continuity")},
            {key:False for key in
             ("knowledge_error","provenance_misrepresentation","severe_av_desync")},
            watched_entire_video=True)
        (quality/"human-review.json").write_text(json.dumps(human),encoding="utf-8")
        forged=dict(human,weighted_score=2)
        (quality/"human-review.json").write_text(json.dumps(forged),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"weighted score"):
            approve_final(self.root,formal,"fixture reviewer",
                          "Observed synthetic full video but should not permit a changed score",checks)
        (quality/"human-review.json").write_text(json.dumps(human),encoding="utf-8")
        signed=approve_final(self.root,formal,"fixture reviewer",
            "Observed full synthetic test video and all placeholder tracks; CI does not prove quality",checks)
        self.assertEqual("release_approved",signed["status"])
        # Touch the existing screenshot: the recorded director and video
        # approval must no longer be usable.
        Image.new("RGB",(320,240),"purple").save(self.still)
        with self.assertRaisesRegex(ValueError,"source changed"):
            verify_release(self.root,formal)
        with self.assertRaises(ValueError):
            approve_final(self.root,formal,"fixture reviewer",
                          "Reviewed complete synthetic preview, not a publishable film",
                          {key:True for key in
                           ("semantic","pacing","continuity","subtitles","audio")})

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg required")
    def test_first_person_is_not_faked_by_crop(self):
        self.create_video()
        shot=self.visual["shots"][0]
        shot["role"]="point_of_view"
        shot["viewpoint"]="first_person"
        shot["camera_preset"]="closeup"
        shot["character_id"]="presenter"
        with self.assertRaisesRegex(ValueError,"First-person"):
            compile_plan(self.root,self.script,self.timeline,self.visual,
                         self.audio,self.board,allow_mixed=True)
        shot["camera_preset"]="native"
        with self.assertRaisesRegex(ValueError,"First-person"):
            compile_plan(self.root,self.script,self.timeline,self.visual,
                         self.audio,self.board,allow_mixed=True)
        shot["source_perspective"]="verified_first_person"
        plan=compile_plan(self.root,self.script,self.timeline,self.visual,
                          self.audio,self.board,allow_mixed=True)
        self.assertEqual("first_person",plan["clips"][0]["viewpoint"])
        self.assertEqual("native",plan["clips"][0]["camera_preset"])

    def test_data_motion_requires_real_export_and_provenance(self):
        self.visual["shots"][1]["media_type"]="data_motion"
        with self.assertRaisesRegex(ValueError,"Source missing|provenance"):
            compile_plan(self.root,self.script,self.timeline,self.visual,
                         self.audio,self.board,allow_mixed=True)

if __name__=="__main__":
    unittest.main()
