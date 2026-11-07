#!/usr/bin/env python3
"""Re-cut actual shot boundaries using human/agent-confirmed audible event times.

Never manufactures timestamps, resamples the narration, or assumes all scenes
have equal lengths. Produces a NEW visual-plan revision; source shots and GPT
footage must still have sufficient actual runtime.
"""
import argparse
import json
from pathlib import Path
from visual_plan import validate as validate_visual,sha256_json

def recut(original,timeline,script,audio,boundaries,notes=None):
    shots=original.get("shots",[])
    if not shots or not isinstance(boundaries,list) or len(boundaries)!=len(shots)+1:
        raise ValueError("Provide one integer boundary per shot edge")
    if any(type(t)!=int for t in boundaries):
        raise ValueError("All cut edges must be real integer milliseconds")
    if boundaries[0]!=shots[0]["start_ms"] or boundaries[-1]!=shots[-1]["end_ms"]:
        raise ValueError("Do not crop the actual full voiceover")
    if any(b-a<250 for a,b in zip(boundaries,boundaries[1:])):
        raise ValueError("Cuts must be ordered with at least 250ms screen time")
    if all(a==b["start_ms"] for a,b in zip(boundaries,shots)):
        raise ValueError("No real cut was changed")
    timecodes={x["id"]:x for x in timeline["segments"]}
    updated=json.loads(json.dumps(original))
    for i,shot in enumerate(updated["shots"]):
        start,end=boundaries[i],boundaries[i+1]
        prior=shot["start_ms"]
        shot["start_ms"],shot["end_ms"]=start,end
        anchors=[sid for sid,seg in timecodes.items()
                 if start<seg["end_ms"] and end>seg["start_ms"]]
        if not anchors:
            raise ValueError(f"{shot['id']}: cut has no real speech segment")
        shot["audio_segment_ids"]=anchors
        # When an existing video is extended into earlier time, one must
        # manually choose the source in-point. Never invent negative trims.
        if "source_in_ms" in shot and start!=prior and shot.get("media_type")!="screenshot":
            raise ValueError(f"{shot['id']}: source in-point needs director validation after cut change")
        shot["cut_reason"]=((notes or {}).get(shot["id"]) or
                 shot.get("cut_reason","") + " [re-cut on observed audio/action event]")
    issues=validate_visual(updated,timeline,script,audio)
    if issues:
        raise ValueError("Re-cut fails actual speech alignment: "+"; ".join(issues))
    return updated

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--visual",required=True);p.add_argument("--timeline",required=True)
    p.add_argument("--script",required=True);p.add_argument("--audio",required=True)
    p.add_argument("--boundaries",required=True,help="JSON array of actual milliseconds")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    read=lambda p:json.loads(Path(p).read_text(encoding="utf-8"))
    changed=recut(read(a.visual),read(a.timeline),read(a.script),a.audio,
                  read(a.boundaries))
    dest=Path(a.out)
    if dest.exists():raise FileExistsError("Use a new revision filename")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(changed,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"RECUT_DRAFT_NEEDS_DIRECTOR_REVIEW",
                      "visual_plan_sha256":sha256_json(changed),
                      "shots":len(changed["shots"])},ensure_ascii=False))
if __name__=="__main__":main()
