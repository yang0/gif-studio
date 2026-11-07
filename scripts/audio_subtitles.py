#!/usr/bin/env python3
"""Create verifiable SRT from an authenticated audio timeline.

Does not estimate timestamps or derive them from a storyboard. This produces
sentence-level captions as supplied by a real aligner/manual reviewer; it
does not claim word-level timestamps.
"""
import argparse
import json
from pathlib import Path
from audio_timeline import validate as validate_timeline, sha256
from visual_plan import sha256_json

def stamp(ms):
    if type(ms) is not int or ms<0:
        raise ValueError("Subtitle timestamp must be a nonnegative integer")
    hours,rest=divmod(ms,3600000)
    minutes,rest=divmod(rest,60000)
    seconds,milliseconds=divmod(rest,1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def build(timeline,script,audio):
    errors=validate_timeline(timeline,script,audio)
    if errors:
        raise ValueError("Cannot create subtitles from invalid real alignment: "+"; ".join(errors))
    chunks=[]
    for idx,segment in enumerate(timeline["segments"],1):
        caption=segment["text"].strip()
        if "\n" in caption:
            caption=caption.replace("\n"," ")
        chunks.append(f"{idx}\n{stamp(segment['start_ms'])} --> {stamp(segment['end_ms'])}\n{caption}\n")
    return "\n".join(chunks)+"\n"

def generate(project,script_path,timeline_path,audio_path,out):
    project=Path(project).resolve()
    script_path=Path(script_path).resolve()
    timeline_path=Path(timeline_path).resolve()
    audio_path=Path(audio_path).resolve()
    out=Path(out).resolve()
    if not all(p.is_file() for p in (script_path,timeline_path,audio_path)):
        raise FileNotFoundError("Actual script, alignment and narration required")
    timeline=json.loads(timeline_path.read_text(encoding="utf-8"))
    script=json.loads(script_path.read_text(encoding="utf-8"))
    srt=build(timeline,script,audio_path)
    if out.is_file():
        if out.read_text(encoding="utf-8")!=srt:
            raise FileExistsError("Existing SRT differs from real alignment; archive old revision first")
        status="unchanged_verified"
    else:
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(srt,encoding="utf-8")
        status="created"
    provenance={
      "version":1,"status":status,
      "script_sha256":sha256(script_path),
      "audio_sha256":sha256(audio_path),
      "audio_timeline_sha256":sha256_json(timeline),
      "srt_sha256":sha256(out),
      "segments":len(timeline["segments"]),
      "level":"sentence",
      "not_word_level":True,
      "review_required":"Check caption readability and actual audio sync"
    }
    report=out.with_suffix(out.suffix+".provenance.json")
    report.write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return provenance

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--script")
    p.add_argument("--timeline")
    p.add_argument("--audio")
    p.add_argument("--out")
    a=p.parse_args()
    root=Path(a.project)
    result=generate(root,
                    a.script or root/"script.json",
                    a.timeline or root/"audio-timeline.json",
                    a.audio or root/"audio"/"voiceover.wav",
                    a.out or root/"subtitles"/"captions.srt")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
