#!/usr/bin/env python3
"""Validate real sentence-level acoustic alignment; never fabricate timestamps.

The alignment JSON is imported from a documented manual/forced aligner,
not manufactured from estimated speaking rate or storyboard durations.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SOURCES={"forced_alignment","manual_verified"}
SILENCE_LIMIT_MS=1500

def normalize(value):
    return re.sub(r"\s+","",value or "")

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def probe_ms(audio):
    obj=json.loads(subprocess.check_output(
        ["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(audio)],
        text=True))
    if not any(s.get("codec_type")=="audio" for s in obj.get("streams",[])):
        raise ValueError("No audio stream in supplied file")
    duration=float(obj.get("format",{}).get("duration",0))
    if duration<=0:
        raise ValueError("Unable to determine audio duration")
    return round(duration*1000)

def script_text(script):
    paragraphs=script.get("paragraphs",[])
    if not isinstance(paragraphs,list) or not paragraphs:
        raise ValueError("Approved script paragraphs missing")
    if any(not isinstance(p,dict) or not isinstance(p.get("text"),str) or not p["text"].strip() for p in paragraphs):
        raise ValueError("Invalid script paragraph")
    return "".join(p["text"] for p in paragraphs)

def validate(timeline,script,audio,probe=True):
    problems=[]
    if not isinstance(timeline,dict) or timeline.get("version")!=1:
        return ["Audio timeline must be version 1"]
    meta=timeline.get("source",{})
    if not isinstance(meta,dict) or meta.get("method") not in SOURCES:
        problems.append("Alignment source must be forced_alignment or manual_verified")
    elif not str(meta.get("tool_or_reviewer","")).strip():
        problems.append("Alignment source must identify the tool or actual human reviewer")
    path=Path(audio)
    if not path.is_file():
        return problems+["Audio file is missing"]
    if timeline.get("audio_sha256")!=sha256(path):
        problems.append("Audio checksum differs from aligned recording")
    if not isinstance(timeline.get("duration_ms"),int) or timeline["duration_ms"]<=0:
        problems.append("Valid positive duration_ms required")
    elif probe:
        try:
            duration=probe_ms(path)
            if abs(duration-timeline["duration_ms"])>120:
                problems.append(f"Recorded duration {duration}ms differs from alignment duration {timeline['duration_ms']}ms")
        except (ValueError,subprocess.CalledProcessError,OSError) as exc:
            problems.append("Audio probe failed: "+str(exc))
    segments=timeline.get("segments",[])
    if not isinstance(segments,list) or not segments:
        return problems+["At least one real timed speech segment required"]
    expected=normalize(script_text(script))
    transcript=""
    previous=0
    seen=set()
    for index,segment in enumerate(segments):
        tag=f"segment {index+1}"
        if not isinstance(segment,dict):
            problems.append(tag+" must be object")
            continue
        identifier=segment.get("id")
        if not isinstance(identifier,str) or not re.fullmatch(r"[A-Za-z0-9_-]+",identifier) or identifier in seen:
            problems.append(tag+" has invalid or duplicate id")
        seen.add(identifier)
        start,end=segment.get("start_ms"),segment.get("end_ms")
        if type(start)!=int or type(end)!=int:
            problems.append(tag+" needs integer millisecond offsets")
            continue
        if start<0 or end<=start:
            problems.append(tag+" has invalid bounds")
        if start<previous:
            problems.append(tag+" overlaps previous segment")
        if end>timeline.get("duration_ms",0):
            problems.append(tag+" exceeds audio length")
        if index==0 and start>SILENCE_LIMIT_MS:
            problems.append("Opening silence exceeds 1500ms: inspect narration")
        if index>0 and start-previous>SILENCE_LIMIT_MS:
            problems.append(tag+" has unexplained >1500ms silence")
        value=segment.get("text")
        if not isinstance(value,str) or not value.strip():
            problems.append(tag+" is missing transcribed spoken text")
        else:
            transcript+=value
        previous=max(previous,end)
    if normalize(transcript)!=expected:
        problems.append("Aligned transcript differs from locked full narration script")
    return problems

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--timeline",required=True)
    p.add_argument("--script",required=True)
    p.add_argument("--audio",required=True)
    p.add_argument("--no-probe",action="store_true",help="For offline fixture testing only")
    a=p.parse_args()
    timeline=json.loads(Path(a.timeline).read_text(encoding="utf-8"))
    script=json.loads(Path(a.script).read_text(encoding="utf-8"))
    issues=validate(timeline,script,a.audio,probe=not a.no_probe)
    print(json.dumps({"pass":not issues,"issues":issues,
                      "segments":len(timeline.get("segments",[]))},ensure_ascii=False,indent=2))
    raise SystemExit(bool(issues))

if __name__=="__main__":
    main()
