#!/usr/bin/env python3
"""Character acting and shot-continuity contract, not an identity detector."""
import argparse
import json
from pathlib import Path
from visual_plan import sha256_json

REQUIRED=("character_id","intention","action","emotion_change","prop_interaction")
BEATS=("setup","action","reaction","resolution")

def validate(director, visual):
    errors=[]; observations=[]; history={}
    shots={s["id"]:s for s in visual.get("shots",[]) if isinstance(s,dict) and "id" in s}
    for item in director.get("shots",[]):
        sid=item.get("shot_id")
        source=shots.get(sid,{})
        if source.get("roll")!="A":
            continue
        p=item.get("performance",{})
        if not isinstance(p,dict):
            errors.append(f"{sid}: performance is not a record")
            continue
        for field in REQUIRED:
            if not isinstance(p.get(field),str) or not p[field].strip():
                errors.append(f"{sid}: missing actual acting field {field}")
        character=p.get("character_id")
        if not character:
            continue
        if item.get("viewpoint")=="first_person" and (source.get("source_perspective")!="verified_first_person" or source.get("camera_preset","native")!="native"):
            errors.append(f"{sid}: fabricated first-person camera not allowed")
        breakdown=p.get("action_beats")
        if breakdown is not None and (not isinstance(breakdown,dict) or
            any(not isinstance(breakdown.get(k),str) or not breakdown[k].strip() for k in BEATS)):
            errors.append(f"{sid}: action_beats need actual setup/action/reaction/resolution")
        appearance=p.get("appearance_lock",{})
        if appearance is not None and not isinstance(appearance,dict):
            errors.append(f"{sid}: appearance_lock must be a record")
            continue
        appearance=appearance or {}
        if character in history:
            first=history[character]
            for field in ("face","hair","clothing","proportions","signature_prop"):
                before=first.get(field)
                after=appearance.get(field)
                if before and after and before!=after:
                    observations.append({"shot_id":sid,"character_id":character,
                        "kind":"appearance_mismatch","field":field,
                        "previous":before,"current":after,
                        "review_required":True})
        else:
            history[character]=appearance
        if source.get("viewpoint")=="supporting_character" and not character:
            errors.append(f"{sid}: supporting role requires character identity")
    return {"version":1,"director_sha256":sha256_json(director),
            "errors":errors,"manual_continuity_risks":observations,
            "automatic_identity_verification":False,
            "status":"BLOCKED" if errors else "NEEDS_REAL_FOOTAGE_REVIEW"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--director",required=True);p.add_argument("--visual",required=True)
    p.add_argument("--out")
    a=p.parse_args()
    load=lambda f:json.loads(Path(f).read_text(encoding="utf-8"))
    result=validate(load(a.director),load(a.visual))
    if a.out:
        path=Path(a.out)
        if path.exists():raise FileExistsError("Never overwrite character review")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(bool(result["errors"]))
if __name__=="__main__":main()
