#!/usr/bin/env python3
"""Produce ONE continuous real narration using optional edge-tts; convert via ffmpeg.

No fake speech/no estimate-based timestamps. edge-tts network requirements
apply. It is an optional provider, not the only accepted voice source.
"""
import argparse
import asyncio
import json
import os
import subprocess
import tempfile
from pathlib import Path
from audio_timeline import script_text, sha256, probe_ms

DEFAULT_VOICE="zh-CN-XiaoxiaoNeural"

def make_audio(script, output, voice=DEFAULT_VOICE, rate="+0%"):
    text=script_text(script)
    if not text.strip():
        raise ValueError("A complete approved script is required")
    if not isinstance(voice,str) or not voice.strip():
        raise ValueError("A real TTS voice must be specified")
    if not isinstance(rate,str) or len(rate)>10:
        raise ValueError("Invalid TTS rate")
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("Optional dependency missing: pip install edge-tts") from exc
    dest=Path(output).resolve()
    if dest.exists():
        raise FileExistsError("Narration already exists; use a new version or remove explicitly")
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gif-studio-voice-") as temp:
        mp3=Path(temp)/"whole-narration.mp3"
        communicator=edge_tts.Communicate(text,voice,rate=rate)
        asyncio.run(communicator.save(str(mp3)))
        if not mp3.is_file() or mp3.stat().st_size==0:
            raise ValueError("TTS provider returned no actual audio")
        tmp=dest.with_name(dest.stem+".incomplete.wav")
        try:
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                 "-i",str(mp3),"-ac","1","-ar","24000",
                 "-c:a","pcm_s16le",str(tmp)],check=True)
            duration=probe_ms(tmp)
            if duration<500:
                raise ValueError("TTS returned implausibly short narration")
            os.replace(tmp,dest)
        finally:
            if tmp.exists():
                tmp.unlink()
    result={"version":1,"provider":"edge-tts","voice":voice,"rate":rate,
            "script_sha256":hashlib_json(script),"audio_sha256":sha256(dest),
            "duration_ms":duration,"status":"actual_synthesized_audio_unaligned",
            "note":"Whole script synthesized in one request; timestamps still require forced alignment or manual review."}
    manifest=dest.with_suffix(".tts.json")
    manifest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result

def hashlib_json(value):
    import hashlib
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,
            separators=(",",":")).encode("utf-8")).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--script",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--provider",default="edge-tts",choices=["edge-tts"])
    p.add_argument("--voice",default=DEFAULT_VOICE)
    p.add_argument("--rate",default="+0%")
    a=p.parse_args()
    script=json.loads(Path(a.script).read_text(encoding="utf-8"))
    print(json.dumps(make_audio(script,a.out,a.voice,a.rate),
                     ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
