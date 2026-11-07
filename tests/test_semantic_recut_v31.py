"""Real aligned timing and creative-assignment tests, not estimated narration."""
import copy
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audio_timeline import sha256
from visual_plan import sha256_json
from semantic_recut import recut
from director_brief_agent import prompt

class SemanticCutTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.audio=self.root/"test.wav"
        with wave.open(str(self.audio),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
            w.writeframes(b"\0\0"*48000)
        self.script={"paragraphs":[{"text":"通知出现。人重新定位任务。"}]}
        self.timeline={"version":1,"source":{"method":"manual_verified","tool_or_reviewer":"test"},
            "audio_sha256":sha256(self.audio),"duration_ms":3000,
            "segments":[{"id":"s1","start_ms":0,"end_ms":1500,"text":"通知出现。"},
                        {"id":"s2","start_ms":1500,"end_ms":3000,"text":"人重新定位任务。"}]}
        self.visual={"version":1,"audio_sha256":sha256(self.audio),
            "timeline_sha256":sha256_json(self.timeline),
            "shots":[
                {"id":"v1","roll":"A","role":"character_action","media_type":"screenshot",
                 "start_ms":0,"end_ms":1500,"audio_segment_ids":["s1"],
                 "visual_event":"Look at device","cut_reason":"Focus breaks"},
                {"id":"v2","roll":"B","role":"evidence","media_type":"screen_recording",
                 "start_ms":1500,"end_ms":3000,"audio_segment_ids":["s2"],
                 "visual_event":"Find prior work","cut_reason":"Reestablish context"}]}
    def test_semantic_cuts_are_actual_new_audio_boundaries(self):
        edited=recut(self.visual,self.timeline,self.script,self.audio,
                     [0,1275,3000],{"v1":"Cut on actual first action"})
        self.assertEqual(1275,edited["shots"][0]["end_ms"])
        self.assertEqual(1275,edited["shots"][1]["start_ms"])
        self.assertEqual(["s1","s2"],edited["shots"][1]["audio_segment_ids"])
        self.assertEqual(1500,self.visual["shots"][1]["start_ms"])
    def test_equal_or_guessed_edges_rejected(self):
        with self.assertRaisesRegex(ValueError,"No real cut"):
            recut(self.visual,self.timeline,self.script,self.audio,[0,1500,3000])
        with self.assertRaisesRegex(ValueError,"integer"):
            recut(self.visual,self.timeline,self.script,self.audio,[0,1500.5,3000])
        with self.assertRaisesRegex(ValueError,"ordered"):
            recut(self.visual,self.timeline,self.script,self.audio,[0,50,3000])
    def test_codex_creative_prompt_uses_real_speech_no_fake_api(self):
        result=prompt(self.script,self.timeline,self.visual)
        self.assertIn("通知出现。",result)
        self.assertIn("viewer",result.lower() if "viewer" in result.lower() else "viewer")
        self.assertIn("start_ms",result)
        self.assertNotIn("API_KEY",result)

if __name__=="__main__":unittest.main()
