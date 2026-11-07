#!/usr/bin/env python3
"""Draft semantic cut decisions anchored to actually measured speech timestamps.

No equal-interval split, guessed timecodes, phantom camera or fake audio.
"""
import argparse
import json
from pathlib import Path
from visual_plan import sha256_json

CUT_EVENTS={"action_start","action_complete","reveal","contrast","speech_emphasis",
            "meaning_shift","emotional_reaction","pause","match_action"}
def recommend(director,timeline,visual):
    timeline_ids={x["id"]:x for x in timeline.get("segments",[])}
    visual_ids={x["id"]:x for x in visual.get("shots",[])}
    out=[];risks=[]
    last_end=None
    for i,shot in enumerate(director.get("shots",[])):
        sid=shot.get("shot_id")
        source=visual_ids.get(sid)
        if source is None:
            raise ValueError(f"Director shot {sid} not found in source visual plan")
        a,b=source["start_ms"],source["end_ms"]
        if last_end is not None and a!=last_end:
            raise ValueError("Real aligned visual clips have a timeline gap")
        last_end=b
        anchor_ids=source.get("audio_segment_ids",[])
        anchors=[timeline_ids[x] for x in anchor_ids if x in timeline_ids]
        if not anchors:
            raise ValueError(f"{sid}: missing actual speech anchors")
        cue=shot.get("cut_cue",{})
        if not isinstance(cue,dict) or cue.get("event") not in CUT_EVENTS:
            risks.append({"shot_id":sid,"kind":"missing_cut_cue",
                          "message":"Supply actual semantic/action cut cue instead of a fixed interval"})
            time=a
            provenance="visual_plan_start_only"
        else:
            time=cue.get("at_ms")
            if type(time)!=int or not a<=time<b:
                raise ValueError(f"{sid}: cut cue must fall within real visual shot")
            if not any(x["start_ms"]<=time<=x["end_ms"] for x in anchors):
                raise ValueError(f"{sid}: cut cue is not grounded in anchored real speech")
            provenance="director_explicit_event"
        out.append({"shot_id":sid,"start_ms":a,"end_ms":b,
                    "cut_at_ms":time,"cue_provenance":provenance,
                    "cue_event":cue.get("event") if isinstance(cue,dict) else None,
                    "meaning":shot.get("cut_reason"),
                    "duration_ms":b-a,
                    "roll":source.get("roll")})
    lengths=[x["duration_ms"] for x in out]
    if len(lengths)>=4 and max(lengths)-min(lengths)<=150:
        risks.append({"shot_id":None,"kind":"uniform_shot_pacing",
                      "message":"Near-equal duration for every shot; verify real semantic/action beats"})
    return {"version":1,"status":"SEMANTIC_CUT_DRAFT_UNREVIEWED",
            "director_sha256":sha256_json(director),
            "audio_timeline_sha256":sha256_json(timeline),
            "visual_plan_sha256":sha256_json(visual),
            "decisions":out,"risks":risks}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--director",required=True);p.add_argument("--timeline",required=True)
    p.add_argument("--visual",required=True);p.add_argument("--out",required=True)
    a=p.parse_args()
    read=lambda path:json.loads(Path(path).read_text(encoding="utf-8"))
    result=recommend(read(a.director),read(a.timeline),read(a.visual))
    out=Path(a.out)
    if out.exists():raise FileExistsError("Do not overwrite original cut decisions")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
