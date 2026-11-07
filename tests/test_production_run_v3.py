import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from project_flow import init
from production_run import run,run_stage

class RunStateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        init(self.root)
        self.script={"paragraphs":[{"id":"p1","text":"测试完整口播"}]}
        (self.root/"script.json").write_text(json.dumps(self.script,ensure_ascii=False),encoding="utf-8")

    def test_network_required_and_resume_from_existing_audio(self):
        status=run(self.root,"voice")
        self.assertEqual("blocked",status["status"])
        self.assertEqual("voice",status["blocked_at"])
        self.assertFalse((self.root/"audio/voiceover.wav").exists())
        audio=self.root/"audio/voiceover.wav"
        audio.parent.mkdir(parents=True)
        with wave.open(str(audio),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
            w.writeframes(b"\x00\x00"*16000)
        resumed=run(self.root,"voice")
        self.assertEqual("inputs_ready_for_next_stage",resumed["status"])
        self.assertEqual("resumed_existing_audio",resumed["completed"][0]["status"])
        self.assertTrue((self.root/"build/workflow-status.json").exists())

    def test_model_opt_in_required(self):
        audio=self.root/"audio/voiceover.wav"
        audio.parent.mkdir(parents=True)
        with wave.open(str(audio),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
            w.writeframes(b"\x00\x00"*16000)
        result=run(self.root,"alignment")
        self.assertEqual("alignment",result["blocked_at"])
        self.assertIn("allow-alignment-model",result["error"])

    def test_bad_existing_alignment_refuses_resume(self):
        audio=self.root/"audio/voiceover.wav"
        audio.parent.mkdir(parents=True)
        with wave.open(str(audio),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
            w.writeframes(b"\x00\x00"*16000)
        (self.root/"audio-timeline.json").write_text('{"version":1,"segments":[]}',encoding="utf-8")
        report=run(self.root,"alignment")
        self.assertEqual("blocked",report["status"])
        self.assertIn("Existing voice/alignment changed",report["error"])

    def test_missing_approved_visual_plan_stops_before_sequence(self):
        audio=self.root/"audio/voiceover.wav"
        audio.parent.mkdir(parents=True)
        with wave.open(str(audio),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
            w.writeframes(b"\x00\x00"*16000)
        from audio_timeline import sha256
        timeline={"version":1,"source":{"method":"manual_verified",
                  "tool_or_reviewer":"actual-fixture-reviewer"},
                  "audio_sha256":sha256(audio),"duration_ms":1000,
                  "segments":[{"id":"s1","start_ms":0,"end_ms":1000,
                               "text":"测试完整口播"}]}
        (self.root/"audio-timeline.json").write_text(json.dumps(timeline,ensure_ascii=False),encoding="utf-8")
        result=run(self.root,"sequence")
        self.assertEqual("sequence",result["blocked_at"])
        self.assertFalse((self.root/"sequence.json").exists())
        self.assertEqual(2,len(result["completed"]))

if __name__=="__main__":
    unittest.main()
