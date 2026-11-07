#!/usr/bin/env python3
"""Validate a narration-timed A/B-roll decision plan.

A/B-roll describes storytelling role, not rendering technology.
This module does not invent audio timing, GIFs, or clip approvals.
"""
import argparse
import json
import re
from pathlib import Path
from audio_timeline import validate as validate_audio, normalize, sha256

ROLLS={"A","B"}
MEDIA={"gpt_gif","screen_recording","screenshot","data_motion","text_overlay"}
B_KINDS={"mechanism","comparison","process","evidence","data","text","demo"}
A_KINDS={"presenter","character_action","supporting_character","emotion","transition","point_of_view"}

def validate(plan,timeline,script,audio,probe=True):
    issues=validate_audio(timeline,script,audio,probe=probe)
    if not isinstance(plan,dict) or plan.get("version")!=1:
        return issues+["Visual plan must be version 1"]
    if plan.get("audio_sha256")!=timeline.get("audio_sha256"):
        issues.append("Visual plan audio hash differs from sound timeline")
    if plan.get("timeline_sha256")!=sha256_json(timeline):
        issues.append("Visual plan references a different audio timeline version")
    segments=timeline.get("segments",[])
    rows=plan.get("shots",[])
    if not isinstance(rows,list) or not rows:
        return issues+["Visual plan shots missing"]
    by_id={x["id"]:x for x in segments if isinstance(x,dict) and isinstance(x.get("id"),str)}
    seen=set()
    previous_end=None
    consecutive_rolls=0
    previous_roll=None
    coverage=[]
    for index,shot in enumerate(rows):
        tag=f"visual shot {index+1}"
        if not isinstance(shot,dict):
            issues.append(tag+" must be object")
            continue
        sid=shot.get("id")
        if not isinstance(sid,str) or not re.fullmatch(r"[A-Za-z0-9_-]+",sid) or sid in seen:
            issues.append(tag+" invalid/duplicate id")
        seen.add(sid)
        roll=shot.get("roll")
        media=shot.get("media_type")
        role=shot.get("role")
        if roll not in ROLLS:
            issues.append(tag+" roll must be A or B")
        if media not in MEDIA:
            issues.append(tag+" unknown media_type")
        if roll=="A" and role not in A_KINDS or roll=="B" and role not in B_KINDS:
            issues.append(tag+" invalid role for selected A/B-roll")
        if not str(shot.get("visual_event","")).strip():
            issues.append(tag+" needs visible change or information")
        if not str(shot.get("cut_reason","")).strip():
            issues.append(tag+" needs an editorial cut reason")
        for key in ("start_ms","end_ms"):
            if type(shot.get(key))!=int:
                issues.append(tag+" needs integer "+key)
        start,end=shot.get("start_ms"),shot.get("end_ms")
        if type(start)!=int or type(end)!=int:
            continue
        if start<0 or end<=start:
            issues.append(tag+" invalid time interval")
        if end>timeline.get("duration_ms",0):
            issues.append(tag+" beyond audio length")
        if previous_end is not None and start!=previous_end:
            issues.append(tag+" contains gap/overlap; visual timeline must be continuous")
        previous_end=end
        anchors=shot.get("audio_segment_ids")
        if not isinstance(anchors,list) or not anchors:
            issues.append(tag+" missing speech anchor segment IDs")
        else:
            if any(x not in by_id for x in anchors):
                issues.append(tag+" anchors unknown speech segment")
            else:
                if not any(start < by_id[x]["end_ms"] and end > by_id[x]["start_ms"] for x in anchors):
                    issues.append(tag+" not timed to its referenced speech")
        if roll==previous_roll:
            consecutive_rolls+=1
        else:
            previous_roll=roll
            consecutive_rolls=1
        if consecutive_rolls>=4:
            issues.append(tag+" four or more consecutive A/B rolls: director must vary rhythm or document exception")
        coverage.append((start,end))
    # Natural lead/trailing silence is allowed, but missing all voiced time is not.
    for seg in segments:
        if not isinstance(seg,dict) or type(seg.get("start_ms"))!=int or type(seg.get("end_ms"))!=int:
            continue
        if not any(a<=seg["start_ms"] and b>=seg["end_ms"] for a,b in coverage):
            # A sentence may span multiple visual shots: require union coverage.
            cursor=seg["start_ms"]
            for a,b in sorted(coverage):
                if a<=cursor<b:
                    cursor=b
                if cursor>=seg["end_ms"]:
                    break
            if cursor<seg["end_ms"]:
                issues.append("Speech segment "+seg["id"]+" not fully covered by visual timeline")
    if coverage and coverage[0][0]>segments[0]["start_ms"]:
        issues.append("Visual timeline starts after narration begins")
    if coverage and coverage[-1][1]<segments[-1]["end_ms"]:
        issues.append("Visual timeline ends before narration finishes")
    return issues

def sha256_json(obj):
    import hashlib
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,
            separators=(",",":")).encode("utf-8")).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--plan",required=True)
    p.add_argument("--timeline",required=True)
    p.add_argument("--script",required=True)
    p.add_argument("--audio",required=True)
    a=p.parse_args()
    plan=json.loads(Path(a.plan).read_text(encoding="utf-8"))
    timeline=json.loads(Path(a.timeline).read_text(encoding="utf-8"))
    script=json.loads(Path(a.script).read_text(encoding="utf-8"))
    issues=validate(plan,timeline,script,a.audio)
    print(json.dumps({"pass":not issues,"issues":issues,
                      "shots":len(plan.get("shots",[]))},ensure_ascii=False,indent=2))
    raise SystemExit(bool(issues))

if __name__=="__main__":
    main()
