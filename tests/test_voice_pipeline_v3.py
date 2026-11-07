"""External voice-command adapter tests use SYNTHETIC fixtures, not real narration."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from voice_pipeline import run,load_config
from audio_timeline import sha256

class VoiceProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.script={"title":"Unit test","central_question":"Why","thesis":"Because",
                     "structure":"Simple","paragraphs":[
                       {"id":"p1","text":"第一句。"},
                       {"id":"p2","text":"第二句。"}]}
        (self.root/"script.json").write_text(json.dumps(self.script,ensure_ascii=False),encoding="utf-8")
        self.provider=self.root/"dummy_provider.py"
        self.provider.write_text(r'''
import json,sys,wave,hashlib
from pathlib import Path
kind=sys.argv[1]
if kind=="tts":
    text=Path(sys.argv[2]).read_text(encoding="utf-8")
    if text!="第一句。第二句。":
        raise RuntimeError("TTS was called by sentence instead of with full script")
    with wave.open(sys.argv[3],"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
        f.writeframes(b"\x00\x00"*16000)
elif kind=="alignment":
    audio=Path(sys.argv[2]);out=Path(sys.argv[4])
    data={"version":1,
          "source":{"method":"forced_alignment","tool_or_reviewer":"fixture-aligner"},
          "audio_sha256":hashlib.sha256(audio.read_bytes()).hexdigest(),
          "duration_ms":1000,
          "segments":[
            {"id":"s1","start_ms":0,"end_ms":500,"text":"第一句。"},
            {"id":"s2","start_ms":500,"end_ms":1000,"text":"第二句。"}]}
    out.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
''',encoding="utf-8")
        self.config={"version":1,
           "tts":{"name":"fixture-tts","argv":[sys.executable,str(self.provider),
                      "tts","{text_file}","{audio_out}"]},
           "alignment":{"name":"fixture-aligner","argv":[sys.executable,str(self.provider),
                      "alignment","{audio_file}","{text_file}","{timeline_out}"]}}

    def test_end_to_end_whole_track_and_resume(self):
        result=run(self.root,self.config)
        self.assertEqual("aligned",result["status"])
        self.assertFalse(result["verified_voice_quality"])
        path=self.root/"audio/voiceover.wav"
        original=sha256(path)
        second=run(self.root,self.config,reuse_audio=True)
        self.assertEqual("already_aligned",second["status"])
        self.assertEqual(original,sha256(path))
        self.assertEqual("第一句。第二句。",(self.root/"audio/voiceover-fulltext.txt").read_text(encoding="utf-8"))
        self.assertTrue((self.root/"audio-timeline.json").is_file())

    def test_failed_alignment_can_retry_without_regenerating_voice(self):
        missing=dict(self.config)
        missing["alignment"]=None
        first=run(self.root,missing)
        self.assertEqual("audio_ready_alignment_required",first["status"])
        with self.assertRaises(FileExistsError):
            run(self.root,self.config)
        resumed=run(self.root,self.config,reuse_audio=True)
        self.assertEqual("aligned",resumed["status"])

    def test_rejects_changed_script_and_tampered_audio(self):
        run(self.root,self.config)
        changed=dict(self.script)
        changed["paragraphs"]=[{"id":"p1","text":"不同内容。"}]
        (self.root/"script.json").write_text(json.dumps(changed,ensure_ascii=False),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"Script changed"):
            run(self.root,self.config,reuse_audio=True)
        (self.root/"script.json").write_text(json.dumps(self.script,ensure_ascii=False),encoding="utf-8")
        with (self.root/"audio/voiceover.wav").open("ab") as f:
            f.write(b"tamper")
        with self.assertRaisesRegex(ValueError,"Audio changed"):
            run(self.root,self.config,reuse_audio=True)

    def test_provider_config_does_not_accept_credential_placeholders(self):
        path=self.root/"provider.json"
        config=json.loads(json.dumps(self.config))
        config["tts"]["argv"].append("{api_key}")
        path.write_text(json.dumps(config),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"credentials"):
            load_config(path)

if __name__=="__main__":
    unittest.main()
