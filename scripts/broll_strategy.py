#!/usr/bin/env python3
"""Six non-template strategies for semantically useful B-roll.

This is a planning check; it never claims animated visuals or data sources exist.
"""
import argparse
import json
from pathlib import Path

REQUIREMENTS={
 "scene_acting":("visual_subject","initial_state","trigger_event","final_state"),
 "causal_visualization":("initial_state","trigger_event","final_state","new_information"),
 "mechanism_breakdown":("visual_subject","initial_state","trigger_event","final_state","new_information"),
 "comparison_experiment":("comparison_basis","initial_state","final_state","new_information"),
 "product_demonstration":("visual_subject","trigger_event","final_state","new_information"),
 "visual_metaphor":("visual_subject","initial_state","trigger_event","final_state","new_information"),
}
DATA_MEDIA={"data_motion"}
FORBIDDEN_UNGROUNDED=("statistically proven","research shows","科学证明","数据显示")

def review(director,visual):
    shots={x["id"]:x for x in visual.get("shots",[]) if isinstance(x,dict) and "id" in x}
    risks=[];errors=[]
    for item in director.get("shots",[]):
        sid=item.get("shot_id")
        source=shots.get(sid,{})
        if source.get("roll")!="B":
            continue
        strategy=item.get("visual_strategy")
        for key in REQUIREMENTS.get(strategy,()):
            if not isinstance(item.get(key),str) or not item[key].strip():
                errors.append(f"{sid}: {strategy} requires {key}")
        if item.get("preferred_media") in DATA_MEDIA:
            evidence=item.get("data_provenance")
            if not isinstance(evidence,str) or not evidence.strip():
                errors.append(f"{sid}: real numerical graphic requires data provenance or explicit illustrative label")
        sentence=" ".join(str(item.get(k,"")) for k in ("viewer_takeaway","new_information"))
        if any(phrase in sentence.lower() for phrase in FORBIDDEN_UNGROUNDED) and not item.get("factual_source"):
            risks.append({"shot_id":sid,"kind":"unverified_claim",
                          "why":"Claims statistical/scientific support without an explicit factual source"})
        if item.get("movement_type")=="meaningful_data_change" and item.get("data_provenance","").strip().lower() in ("示意","illustrative","demo"):
            risks.append({"shot_id":sid,"kind":"illustrative_data",
                          "why":"Numbers are illustrative and must be marked as such in the actual video"})
    return {"errors":errors,"risks":risks,"status":"BLOCKED" if errors else "NEEDS_EDITORIAL_REVIEW"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--director",required=True);p.add_argument("--visual",required=True)
    a=p.parse_args()
    read=lambda x:json.loads(Path(x).read_text(encoding="utf-8"))
    result=review(read(a.director),read(a.visual))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(bool(result["errors"]))
if __name__=="__main__":main()
