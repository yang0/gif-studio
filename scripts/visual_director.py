#!/usr/bin/env python3
"""Visual Director v2: semantic storyboard contracts, not a substitute for creativity.

This module makes proposals from explicit shot descriptions. It NEVER infers
unseen scientific facts, generates footage, or approves aesthetic quality.
A/B roll is narrative responsibility; media is independently chosen.
"""
import argparse
import json
import re
from pathlib import Path
from visual_plan import sha256_json

STRATEGIES={
    "scene_acting", "causal_visualization", "mechanism_breakdown",
    "comparison_experiment", "product_demonstration", "visual_metaphor",
}
FUNCTIONS={"hook","establish","question","explain_cause","explain_process",
           "compare","prove","transition","solution","conclude"}
MOVEMENT={"physical_action","visible_cause_effect","spatial_reveal",
          "meaningful_data_change","real_demonstration","meaningful_hold"}
MEDIA={"gpt_gif","screen_recording","screenshot","data_motion",
       "real_video","original_animation"}
VERSION=2

def _meaningful(value):
    return isinstance(value,str) and bool(value.strip())

def validate(plan, audio_timeline, visual_plan):
    issues=[]
    if not isinstance(plan,dict) or plan.get("version")!=VERSION:
        return ["Visual Director plan requires version 2"]
    if plan.get("audio_timeline_sha256")!=sha256_json(audio_timeline):
        issues.append("Director plan stale: audio timeline changed")
    if plan.get("visual_plan_sha256")!=sha256_json(visual_plan):
        issues.append("Director plan stale: visual plan changed")
    items=plan.get("shots")
    if not isinstance(items,list) or not items:
        return issues+["Director shots must be a nonempty list"]
    vs={s["id"]:s for s in visual_plan.get("shots",[]) if isinstance(s,dict) and "id" in s}
    ids=set()
    signatures=set()
    previous=None
    for i,shot in enumerate(items):
        label=f"director shot {i+1}"
        if not isinstance(shot,dict):
            issues.append(label+" must be an object")
            continue
        sid=shot.get("shot_id")
        if not isinstance(sid,str) or sid not in vs or sid in ids:
            issues.append(label+" has unknown or duplicate visual shot id")
            continue
        ids.add(sid)
        source=vs[sid]
        if shot.get("start_ms")!=source.get("start_ms") or shot.get("end_ms")!=source.get("end_ms"):
            issues.append(sid+": timestamps differ from aligned visual plan")
        if shot.get("narrative_function") not in FUNCTIONS:
            issues.append(sid+": invalid narrative function")
        if shot.get("visual_strategy") not in STRATEGIES:
            issues.append(sid+": unsupported visual strategy")
        if shot.get("movement_type") not in MOVEMENT:
            issues.append(sid+": missing meaningful movement type")
        for field in ("viewer_takeaway","scene_intent","visual_subject",
                      "initial_state","trigger_event","final_state",
                      "new_information","cut_reason"):
            if not _meaningful(shot.get(field)):
                issues.append(sid+": missing "+field)
        if shot.get("initial_state")==shot.get("final_state") and shot.get("movement_type")!="meaningful_hold":
            issues.append(sid+": visual state does not actually change")
        if shot.get("movement_type")=="meaningful_hold" and not _meaningful(shot.get("hold_justification")):
            issues.append(sid+": static hold needs an editorial justification")
        if shot.get("source_policy") not in ("use_existing","create_original","record_actual"):
            issues.append(sid+": ungrounded source policy")
        if shot.get("preferred_media") not in MEDIA:
            issues.append(sid+": unsupported media type")
        if source.get("roll")=="A":
            performance=shot.get("performance")
            if not isinstance(performance,dict):
                issues.append(sid+": A-roll requires a performance plan")
            elif any(not _meaningful(performance.get(x)) for x in ("character_id","intention","action","emotion_change","prop_interaction")):
                issues.append(sid+": A-roll character/action/emotion/prop details required")
        else:
            if shot.get("visual_strategy")=="comparison_experiment" and not _meaningful(shot.get("comparison_basis")):
                issues.append(sid+": B-roll comparison requires a grounded basis")
            if shot.get("preferred_media")=="data_motion" and not _meaningful(shot.get("data_provenance")):
                issues.append(sid+": information motion requires a data source or explicit illustrative label")
        signature=(shot.get("visual_strategy"),shot.get("visual_subject"),
                   shot.get("movement_type"),shot.get("initial_state"),shot.get("final_state"))
        if signature in signatures:
            issues.append(sid+": identical scene/action signature repeated")
        signatures.add(signature)
        if previous is not None and previous.get("visual_strategy")==shot.get("visual_strategy"):
            issues.append(sid+": consecutive identical visual strategy: review rhythm (warning)")
        previous=shot
    if ids != set(vs):
        issues.append("Director plan must cover each aligned visual-plan shot exactly once")
    return issues

def propose(visual_plan, audio_timeline, briefs, variant):
    """Build transparent editor DRAFTS from supplied human/agent creative briefs.

    Does not manufacture shot content, dialogue, scientific claims or performance.
    The caller supplies observable states, actions, knowledge gain, and sources.
    """
    if variant not in ("dramatic","explanatory"):
        raise ValueError("variant must be dramatic or explanatory")
    if not isinstance(briefs,dict):
        raise ValueError("Shot briefs must be an object keyed by visual shot IDs")
    drafts=[]
    for shot in visual_plan.get("shots",[]):
        sid=shot["id"]
        item=briefs.get(sid)
        if not isinstance(item,dict):
            raise ValueError("Missing supplied semantic brief for "+sid)
        draft=dict(item)
        draft.update({"shot_id":sid,"start_ms":shot["start_ms"],
                      "end_ms":shot["end_ms"]})
        alternatives=item.get("alternatives",{})
        if isinstance(alternatives,dict) and variant in alternatives:
            # Explicit alternatives, not arbitrary formulaic animation.
            change=alternatives[variant]
            if not isinstance(change,dict):
                raise ValueError("Alternative must be an object: "+sid)
            draft.update(change)
        draft.pop("alternatives",None)
        drafts.append(draft)
    return {"version":VERSION,"variant":variant,"status":"DIRECTOR_DRAFT_UNREVIEWED",
            "audio_timeline_sha256":sha256_json(audio_timeline),
            "visual_plan_sha256":sha256_json(visual_plan),"shots":drafts}

def compare(first,second):
    if set(x["shot_id"] for x in first["shots"])!=set(x["shot_id"] for x in second["shots"]):
        raise ValueError("Visual alternatives must describe the same real shots")
    a={s["shot_id"]:s for s in first["shots"]}
    b={s["shot_id"]:s for s in second["shots"]}
    changed=[]
    for sid in sorted(a):
        dimensions=("visual_strategy","visual_subject","initial_state",
                    "trigger_event","final_state","movement_type")
        delta=[x for x in dimensions if a[sid].get(x)!=b[sid].get(x)]
        if delta:
            changed.append({"shot_id":sid,"changed_dimensions":delta})
    return {"distinct_shots":len(changed),"total_shots":len(a),
            "meaningfully_different":bool(changed),"differences":changed}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--visual",required=True)
    p.add_argument("--timeline",required=True)
    p.add_argument("--briefs")
    p.add_argument("--out")
    p.add_argument("--variant",choices=("dramatic","explanatory"),default="dramatic")
    p.add_argument("--check")
    a=p.parse_args()
    read=lambda file:json.loads(Path(file).read_text(encoding="utf-8"))
    visual=read(a.visual);timeline=read(a.timeline)
    if a.check:
        result=read(a.check)
    else:
        if not a.briefs or not a.out:
            p.error("--briefs and --out required for proposal")
        if Path(a.out).exists():
            raise FileExistsError("Director plan exists; version explicitly")
        result=propose(visual,timeline,read(a.briefs),a.variant)
        Path(a.out).parent.mkdir(parents=True,exist_ok=True)
        Path(a.out).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    problems=validate(result,timeline,visual)
    warnings=[x for x in problems if x.endswith("(warning)")]
    errors=[x for x in problems if x not in warnings]
    print(json.dumps({"valid":not errors,"errors":errors,"warnings":warnings,
                      "status":result.get("status")},ensure_ascii=False,indent=2))
    raise SystemExit(bool(errors))

if __name__=="__main__":
    main()
