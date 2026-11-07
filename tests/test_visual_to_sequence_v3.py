"""A real audio timeline drives two distinct GIF candidates in a single narration."""
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
from candidate_pool import add
from visual_to_sequence import compile_sequence

class AudioToEditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.audio=self.root/"voice.wav"
        with wave.open(str(self.audio),"wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"\x00\x00"*16000)
        self.script={"title":"Example","central_question":"Why?","thesis":"Because","structure":"Explain",
                     "paragraphs":[{"id":"p1","text":"第一句第二句"}]}
        self.timeline={"version":1,"source":{"method":"manual_verified",
                       "tool_or_reviewer":"Test operator"},
                       "audio_sha256":sha256(self.audio),"duration_ms":1000,
                       "segments":[{"id":"s1","start_ms":0,"end_ms":500,"text":"第一句"},
                                   {"id":"s2","start_ms":500,"end_ms":1000,"text":"第二句"}]}
        prompt=self.root/"prompt.txt"
        prompt.write_text("Specific real visual event",encoding="utf-8")
        for name,colors in (("take-a",["red","blue","green","yellow","purple","orange"]),
                            ("take-b",["purple","orange","yellow","green","blue","red"])):
            gif=self.root/(name+".gif")
            frames=[Image.new("RGB",(270,480),c) for c in colors]
            frames[0].save(gif,format="GIF",save_all=True,
                           append_images=frames[1:],duration=200,loop=0)
            add(self.root,"shot-01",name,gif,prompt,"test-generator",
                "actual-synthetic-fixture-"+name,"Distinct test GIF")
        from candidate_pool import read
        catalog=read(self.root)
        self.visual={"version":1,"audio_sha256":sha256(self.audio),
                     "timeline_sha256":sha256_json(self.timeline),
                     "shots":[
              {"id":"v1","start_ms":0,"end_ms":500,"audio_segment_ids":["s1"],
               "roll":"A","role":"character_action","media_type":"gpt_gif",
               "visual_event":"Person entering frame","cut_reason":"Establish subject",
               "source_shot_id":"shot-01","candidate_id":"take-a"},
              {"id":"v2","start_ms":500,"end_ms":1000,"audio_segment_ids":["s2"],
               "roll":"B","role":"mechanism","media_type":"gpt_gif",
               "visual_event":"Explained detail appears","cut_reason":"Reveal mechanism",
               "source_shot_id":"shot-01","candidate_id":"take-b"}]}
        self.board={"project_title":"V3 test","width":540,"height":960,"fps":24,
                    "shots":[{"id":"shot-01","duration_sec":1.0,
                              "narration":"第一句第二句","visual_goal":"Test",
                              "visual_mode":"mechanism_breakdown",
                              "motion_plan":["start","end"]}]}
        (self.root/"storyboard.json").write_text(json.dumps(self.board,ensure_ascii=False),encoding="utf-8")
        (self.root/"audio-timeline.json").write_text(json.dumps(self.timeline,ensure_ascii=False),encoding="utf-8")
        (self.root/"visual-plan.json").write_text(json.dumps(self.visual,ensure_ascii=False),encoding="utf-8")

    def test_two_different_candidates_are_compiled_from_audio(self):
        seq=compile_sequence(self.root,self.script,self.audio,self.timeline,self.visual,self.board)
        self.assertEqual(24,seq["total_frames"])
        self.assertEqual([0,12],[x["start_frame"] for x in seq["clips"]])
        self.assertEqual(["take-a","take-b"],[x["candidate_id"] for x in seq["clips"]])
        self.assertEqual(sha256_json(self.visual),seq["visual_plan_sha256"])

    def test_cannot_fake_missing_candidate_or_media(self):
        visual=json.loads(json.dumps(self.visual))
        visual["shots"][1]["candidate_id"]="missing"
        with self.assertRaisesRegex(ValueError,"missing actual GIF"):
            compile_sequence(self.root,self.script,self.audio,self.timeline,visual,self.board)
        visual=json.loads(json.dumps(self.visual))
        visual["shots"][1]["media_type"]="data_motion"
        with self.assertRaisesRegex(ValueError,"mixed-media renderer"):
            compile_sequence(self.root,self.script,self.audio,self.timeline,visual,self.board)

    def test_audio_outside_visual_range_is_rejected(self):
        visual=json.loads(json.dumps(self.visual))
        visual["shots"][1]["end_ms"]=900
        with self.assertRaises(ValueError):
            compile_sequence(self.root,self.script,self.audio,self.timeline,visual,self.board)

if __name__=="__main__":
    unittest.main()
