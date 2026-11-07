"""Audio-first visual plan schedules *different* GIF candidates, not recycled art."""
import json
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
from visual_assets import prepare,check,plan

class VisualAssetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        root=self.root
        audio=root/"audio"/"voiceover.wav"
        audio.parent.mkdir()
        with wave.open(str(audio),"wb") as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
            f.writeframes(b"\0\0"*16000)
        self.script={"title":"Test narration","central_question":"Why","thesis":"Because",
                     "structure":"Sequence","paragraphs":[{"id":"p1","text":"为什么？"},{"id":"p2","text":"看这里。"}]}
        self.timeline={"version":1,"source":{"method":"manual_verified",
            "tool_or_reviewer":"fixture operator"},"audio_sha256":sha256(audio),
            "duration_ms":1000,"segments":[
              {"id":"s1","start_ms":0,"end_ms":500,"text":"为什么？"},
              {"id":"s2","start_ms":500,"end_ms":1000,"text":"看这里。"}]}
        refs={}
        for role in ("front","side","back","stroke_detail","scene"):
            path=root/"refs"/(role+".png")
            path.parent.mkdir(exist_ok=True)
            Image.new("RGB",(256,256),"white").save(path)
            refs[role]={"file":"refs/"+role+".png","sha256":sha256(path)}
        pack={"version":1,"character_id":"original","character_description":"Original character, fixed outfit and proportions","references":refs}
        (root/"reference-pack.json").write_text(json.dumps(pack),encoding="utf-8")
        self.style={"style_id":"hand-drawn","line_weight":"thin","light":"soft"}
        self.board={"project_title":"Testing","fps":24,"width":540,"height":960,
                    "shots":[{"id":"shot-a"},{"id":"shot-b"}]}
        def candidate(id,frame,motion):
            return {"candidate_id":id,"framing":frame,"distinctive_motion":motion,
                    "must_show":["phone on table","original character moves their hand"],
                    "must_not_show":["brain icon","fake letters"],"notes":"Actually distinct shot setup"}
        self.visual={"version":1,"audio_sha256":sha256(audio),
            "timeline_sha256":sha256_json(self.timeline),
            "shots":[
              {"id":"v1","start_ms":0,"end_ms":500,"audio_segment_ids":["s1"],
               "roll":"A","role":"character_action","media_type":"gpt_gif",
               "source_shot_id":"shot-a","visual_event":"Person asks a question",
               "cut_reason":"Character establishes setup",
               "production":{"reference_pack":"reference-pack.json",
                             "candidates":[candidate("wide","wide shot","A person's hand reaches for the phone"),
                                           candidate("detail","close shot","Hand pauses above the illuminated phone")]}},
              {"id":"v2","start_ms":500,"end_ms":1000,"audio_segment_ids":["s2"],
               "roll":"B","role":"mechanism","media_type":"gpt_gif",
               "source_shot_id":"shot-b","visual_event":"Visual explanation mechanism",
               "cut_reason":"Show causal explanation",
               "production":{"candidates":[candidate("mechanism","macro","Phone notification visibly lights up")]}},
              {"id":"v3","start_ms":1000,"end_ms":1000,"audio_segment_ids":["s2"],
               "roll":"B","role":"demo","media_type":"screen_recording",
               "source_file":"media/real-demo.mp4","source_sha256":"fixed",
               "visual_event":"real demo","cut_reason":"show evidence"}]}
        # v3 is an optional external media demonstration; remove zero-duration invalid row.
        self.visual["shots"].pop()
        for path,data in (("script.json",self.script),
                          ("audio-timeline.json",self.timeline),
                          ("visual-plan.json",self.visual),
                          ("style-lock.json",self.style),
                          ("storyboard.json",self.board)):
            (root/path).write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")

    def test_prepare_three_distinct_prompts_and_resume(self):
        result=prepare(self.root)
        self.assertEqual(3,result["task_count"])
        batch=json.loads((self.root/"production"/"visual-asset-plan.json").read_text())
        self.assertEqual(3,len(batch["batch"]["tasks"]))
        contents=[(self.root/x["prompt"]).read_text(encoding="utf-8")
                  for x in batch["batch"]["tasks"]]
        self.assertEqual(3,len(set(contents)))
        self.assertIn("phone",contents[0])
        self.assertIn("REFERENCE PACK",contents[0])
        self.assertEqual("prepared_not_generated",prepare(self.root)["status"])
        state=check(self.root)
        self.assertEqual("awaiting_generation",state["status"])
        self.assertEqual(3,len(state["pending"]))
        self.assertFalse(state["visual_approval"])

    def test_reference_missing_blocks_a_roll(self):
        self.visual["shots"][0]["production"].pop("reference_pack")
        with self.assertRaisesRegex(ValueError,"reference pack"):
            plan(self.root,self.script,self.timeline,self.visual,
                 self.root/"audio"/"voiceover.wav",self.style,self.board)

    def test_duplicate_candidate_and_missing_distinct_motion(self):
        self.visual["shots"][1]["source_shot_id"]="shot-a"
        self.visual["shots"][1]["production"]["candidates"][0]["candidate_id"]="wide"
        with self.assertRaisesRegex(ValueError,"Duplicate candidate"):
            plan(self.root,self.script,self.timeline,self.visual,
                 self.root/"audio"/"voiceover.wav",self.style,self.board)
        self.visual["shots"][1]["production"]["candidates"][0]["candidate_id"]="new"
        self.visual["shots"][1]["production"]["candidates"][0]["distinctive_motion"]="vague"
        with self.assertRaisesRegex(ValueError,"concrete motion"):
            plan(self.root,self.script,self.timeline,self.visual,
                 self.root/"audio"/"voiceover.wav",self.style,self.board)

    def test_changed_visual_plan_rejects_stale_prepared_tasks(self):
        prepare(self.root)
        self.visual["shots"][1]["visual_event"]="A different knowledge mechanism"
        (self.root/"visual-plan.json").write_text(json.dumps(self.visual),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"stale"):
            prepare(self.root)
        self.assertEqual("blocked",check(self.root)["status"])

    def test_changed_reference_image_is_blocked(self):
        prepare(self.root)
        Image.new("RGB",(256,256),"black").save(self.root/"refs/front.png")
        self.assertEqual("blocked",check(self.root)["status"])

    def test_existing_prompt_is_not_overwritten(self):
        prepare(self.root)
        p=self.root/"prompts/v3/shot-a/wide.txt"
        p.write_text("Bad manual prompt edit",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"prompt changed"):
            prepare(self.root)
        self.assertEqual("blocked",check(self.root)["status"])

if __name__=="__main__":
    unittest.main()
