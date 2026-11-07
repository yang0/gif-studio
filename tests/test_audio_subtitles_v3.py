"""Caption generation from a real-format audio timeline; audio itself is a test fixture."""
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from audio_subtitles import build,generate,stamp
from audio_timeline import sha256
from visual_plan import sha256_json
from release_sequence import v3_subtitle_provenance_issues

class AudioSubtitleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.audio=self.root/"voice.wav"
        with wave.open(str(self.audio),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
            w.writeframes(b"\x00\x00"*32000)
        self.script={"paragraphs":[{"id":"p1","text":"第一句。第二句。"}]}
        self.timeline={"version":1,
           "source":{"method":"manual_verified","tool_or_reviewer":"test-reviewer"},
           "audio_sha256":sha256(self.audio),"duration_ms":2000,
           "segments":[{"id":"s1","start_ms":100,"end_ms":810,"text":"第一句。"},
                       {"id":"s2","start_ms":920,"end_ms":1850,"text":"第二句。"}]}
        self.script_path=self.root/"script.json"
        self.timeline_path=self.root/"audio-timeline.json"
        self.script_path.write_text(json.dumps(self.script,ensure_ascii=False),encoding="utf-8")
        self.timeline_path.write_text(json.dumps(self.timeline,ensure_ascii=False),encoding="utf-8")

    def test_precise_sentence_srt_and_idempotent_export(self):
        output=self.root/"subtitles"/"captions.srt"
        first=generate(self.root,self.script_path,self.timeline_path,self.audio,output)
        self.assertEqual("created",first["status"])
        txt=output.read_text(encoding="utf-8")
        self.assertIn("00:00:00,100 --> 00:00:00,810",txt)
        self.assertIn("00:00:00,920 --> 00:00:01,850",txt)
        self.assertEqual("unchanged_verified",
                         generate(self.root,self.script_path,self.timeline_path,self.audio,output)["status"])
        self.assertEqual("sentence",first["level"])

    def test_rejects_unaligned_and_tampered_audio(self):
        bad=json.loads(json.dumps(self.timeline))
        bad["segments"][1]["start_ms"]=300
        with self.assertRaisesRegex(ValueError,"overlaps"):
            build(bad,self.script,self.audio)
        with (self.audio).open("ab") as f:
            f.write(b"changed")
        with self.assertRaisesRegex(ValueError,"checksum"):
            build(self.timeline,self.script,self.audio)

    def test_refuses_existing_unrelated_captions(self):
        output=self.root/"captions.srt"
        output.write_text("foreign subtitles",encoding="utf-8")
        with self.assertRaises(FileExistsError):
            generate(self.root,self.script_path,self.timeline_path,self.audio,output)

    def test_v3_formal_release_rejects_stale_caption_provenance(self):
        output=self.root/"subtitles"/"captions.srt"
        generate(self.root,self.script_path,self.timeline_path,self.audio,output)
        sequence={
            "audio_timeline_sha256":sha256_json(self.timeline),
            "audio_sha256":sha256(self.audio)}
        self.assertEqual([],v3_subtitle_provenance_issues(
            self.root,sequence,self.audio,output))
        output.write_text("Modified captions",encoding="utf-8")
        issues=v3_subtitle_provenance_issues(self.root,sequence,self.audio,output)
        self.assertTrue(any("srt_sha256" in x for x in issues),issues)

    def test_timestamp_format(self):
        self.assertEqual("01:02:03,004",stamp(3723004))

if __name__=="__main__":
    unittest.main()
