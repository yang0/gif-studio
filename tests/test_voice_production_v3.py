"""Provider boundary tests; fake voice fixture NEVER counted as real speech QA."""
import asyncio
import json
import sys
import shutil
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from voice_production import make_audio
from forced_align import align
from audio_timeline import sha256

class VoiceProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.audio=self.root/"audio.wav"
        with wave.open(str(self.audio),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
            w.writeframes(b"\x00\x00"*16000)
        self.script={"paragraphs":[{"id":"p1","text":"第一句话。"},
                                   {"id":"p2","text":"第二句话。"}]}

    def test_true_alignment_source_and_transcript(self):
        class MockModel:
            def align(self,audio,text,language,original_split):
                self.text=text
                self.language=language
                self.original_split=original_split
                return SimpleNamespace(segments=[
                    SimpleNamespace(text="第一句话。",start=0.0,end=.45),
                    SimpleNamespace(text="第二句话。",start=.46,end=1.0)])
        model=MockModel()
        result=align(self.script,self.audio,model_loader=lambda _:model)
        self.assertEqual("forced_alignment",result["source"]["method"])
        self.assertEqual(sha256(self.audio),result["audio_sha256"])
        self.assertEqual(["第一句话。","第二句话。"],[s["text"] for s in result["segments"]])
        self.assertTrue(model.original_split)

    def test_reject_model_text_drift(self):
        class WrongModel:
            def align(self,*args,**kwargs):
                return SimpleNamespace(segments=[
                    SimpleNamespace(text="不匹配",start=0,end=.5),
                    SimpleNamespace(text="第二句话。",start=.5,end=1)])
        with self.assertRaisesRegex(ValueError,"text drift"):
            align(self.script,self.audio,model_loader=lambda _:WrongModel())

    def test_reject_model_missing_sentence(self):
        class MissingModel:
            def align(self,*args,**kwargs):
                return SimpleNamespace(segments=[SimpleNamespace(text="第一句话。",start=0,end=1)])
        with self.assertRaisesRegex(ValueError,"segments"):
            align(self.script,self.audio,model_loader=lambda _:MissingModel())

    def test_no_fake_narration_if_edge_tts_missing(self):
        with patch.dict(sys.modules,{"edge_tts":None}):
            with self.assertRaisesRegex(RuntimeError,"Optional dependency"):
                make_audio(self.script,self.root/"output.wav")
        self.assertFalse((self.root/"output.wav").exists())

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg required to verify actual WAV produced")
    def test_real_wav_output_from_mocked_tts_transport(self):
        # This fixture exercises the real MP3->WAV conversion, not speech quality.
        calls=[]
        class DummyCommunicate:
            def __init__(self,text,voice,rate):
                calls.append((text,voice,rate))
            async def save(self,path):
                subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i",
                                "sine=frequency=330:sample_rate=24000","-t","1.4",
                                "-codec:a","libmp3lame",path],check=True)
        module=SimpleNamespace(Communicate=DummyCommunicate)
        with patch.dict(sys.modules,{"edge_tts":module}):
            out=self.root/"whole.wav"
            report=make_audio(self.script,out,voice="zh-CN-XiaoxiaoNeural")
        self.assertTrue(out.is_file())
        self.assertGreater(out.stat().st_size,5000)
        self.assertEqual("actual_synthesized_audio_unaligned",report["status"])
        self.assertEqual("第一句话。第二句话。",calls[0][0])
        self.assertEqual(1,len(calls))
        self.assertEqual(sha256(out),report["audio_sha256"])

    def test_refuse_overwrite_existing_audio(self):
        with self.assertRaises(FileExistsError):
            make_audio(self.script,self.audio)

if __name__=="__main__":
    unittest.main()
