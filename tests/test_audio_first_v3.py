"""v3 sound-first contracts. Audio WAV is a test fixture, NOT TTS quality evidence."""
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audio_timeline import sha256, validate as check_audio
from visual_plan import validate as check_visual, sha256_json
from project_flow import init, state, resolve

class AudioFirstContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        path=self.root/"audio"/"voiceover.wav"
        path.parent.mkdir(parents=True,exist_ok=True)
        with wave.open(str(path),"wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"\x00\x00"*16000)
        self.audio=path
        self.script={
            "title":"Test narration","central_question":"Why?",
            "thesis":"Because","structure":"cause and effect",
            "paragraphs":[{"id":"p1","text":"第一句，第二句。"}]}
        self.timeline={
            "version":1,
            "source":{"method":"manual_verified","tool_or_reviewer":"unit-test-reviewer"},
            "audio_sha256":sha256(path),"duration_ms":1000,
            "segments":[
                {"id":"s1","start_ms":0,"end_ms":450,"text":"第一句，"},
                {"id":"s2","start_ms":450,"end_ms":1000,"text":"第二句。"}
            ]}
        self.plan={
            "version":1,"audio_sha256":sha256(path),
            "timeline_sha256":sha256_json(self.timeline),
            "shots":[
              {"id":"v1","start_ms":0,"end_ms":450,
               "audio_segment_ids":["s1"],"roll":"A","role":"character_action",
               "media_type":"gpt_gif","visual_event":"Person poses the question",
               "cut_reason":"Establish causal question"},
              {"id":"v2","start_ms":450,"end_ms":1000,
               "audio_segment_ids":["s2"],"roll":"B","role":"mechanism",
               "media_type":"gpt_gif","visual_event":"Show mechanism change",
               "cut_reason":"Explain the actual cause"}
            ]}

    def test_real_audio_and_visual_plan_validate(self):
        self.assertEqual([],check_audio(self.timeline,self.script,self.audio))
        self.assertEqual([],check_visual(self.plan,self.timeline,self.script,self.audio))

    def test_rejects_transcript_drift_and_unverified_alignment(self):
        t=json.loads(json.dumps(self.timeline))
        t["segments"][1]["text"]="第三句。"
        self.assertTrue(any("differs" in x for x in check_audio(t,self.script,self.audio)))
        t=json.loads(json.dumps(self.timeline))
        t["source"]["method"]="estimated_by_character_count"
        self.assertTrue(any("Alignment source" in x for x in check_audio(t,self.script,self.audio)))

    def test_rejects_overlapping_and_noninteger_timestamps(self):
        t=json.loads(json.dumps(self.timeline))
        t["segments"][1]["start_ms"]=400
        self.assertTrue(any("overlaps" in x for x in check_audio(t,self.script,self.audio)))
        t=json.loads(json.dumps(self.timeline))
        t["segments"][0]["start_ms"]=0.2
        self.assertTrue(any("integer" in x for x in check_audio(t,self.script,self.audio)))

    def test_rejects_speech_not_covered_by_visual_edl(self):
        p=json.loads(json.dumps(self.plan))
        p["shots"][1]["start_ms"]=500
        self.assertTrue(any("gap/overlap" in x or "not fully covered" in x for x in
                            check_visual(p,self.timeline,self.script,self.audio)))

    def test_rejects_bad_roll_role_and_stale_audio_hash(self):
        p=json.loads(json.dumps(self.plan))
        p["shots"][1]["roll"]="A"
        p["audio_sha256"]="bad"
        issues=check_visual(p,self.timeline,self.script,self.audio)
        self.assertTrue(any("invalid role" in x for x in issues))
        self.assertTrue(any("audio hash" in x for x in issues))

    def test_project_entrypoint_stages(self):
        init(self.root)
        cfg=json.loads((self.root/"project.json").read_text(encoding="utf-8"))
        self.assertEqual(3,cfg["version"])
        report=state(self.root)
        self.assertFalse(report["ready_for_publication"])
        self.assertEqual("missing",report["stages"][0]["status"])
        (self.root/"script.json").write_text(json.dumps(self.script,ensure_ascii=False),encoding="utf-8")
        (self.root/"audio-timeline.json").write_text(json.dumps(self.timeline,ensure_ascii=False),encoding="utf-8")
        (self.root/"visual-plan.json").write_text(json.dumps(self.plan,ensure_ascii=False),encoding="utf-8")
        report=state(self.root)
        self.assertEqual("ready",report["stages"][0]["status"])
        self.assertEqual("ready",report["stages"][1]["status"])
        self.assertEqual("ready",report["stages"][2]["status"])

    def test_non_gif_video_does_not_require_gif_account_or_candidate_pool(self):
        init(self.root)
        (self.root/"script.json").write_text(
            json.dumps(self.script,ensure_ascii=False),encoding="utf-8")
        (self.root/"audio-timeline.json").write_text(
            json.dumps(self.timeline,ensure_ascii=False),encoding="utf-8")
        plan=json.loads(json.dumps(self.plan))
        plan["shots"][0]["media_type"]="screen_recording"
        plan["shots"][1]["media_type"]="screenshot"
        (self.root/"visual-plan.json").write_text(
            json.dumps(plan,ensure_ascii=False),encoding="utf-8")
        report=state(self.root)
        stages={x["stage"]:x for x in report["stages"]}
        self.assertEqual("ready",stages["asset_production"]["status"])
        self.assertEqual("ready",stages["asset_library"]["status"])
        self.assertEqual("missing",stages["edit_sequence"]["status"])
        self.assertFalse(report["ready_for_publication"])

    def test_project_paths_reject_escape(self):
        with self.assertRaises(ValueError):
            resolve(self.root,"../outside.wav")
        with self.assertRaises(ValueError):
            resolve(self.root,"/tmp/absolute")
        init(self.root)
        with self.assertRaises(FileExistsError):
            init(self.root)

if __name__=="__main__":
    unittest.main()
