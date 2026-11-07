#!/usr/bin/env python3
"""Convert documented audiovisual findings into a reproducible local rework plan.

A plan is not a claim that footage has been regenerated or quality improved.
Non-affected approved source footage remains reusable.
"""
import argparse
import json
from pathlib import Path
from audio_timeline import sha256
from visual_plan import sha256_json
from video_critic import check_report

SEVERITIES={"critical","high","medium","low"}
KINDS={"low_motion_risk","adjacent_visual_similarity","mechanical_equal_duration",
       "missing_audio","missing_subtitles","low_resolution","duration_mismatch",
       "small_subject","empty_composition","narrative_redundancy","weak_causality",
       "character_drift","bad_narration","subtitle_desync","invalid_data",
       "insufficient_information","other"}
REMEDIES={
    "low_motion_risk":"Rebuild the visible event with a meaningful causal state change; retain source only if justified static evidence",
    "adjacent_visual_similarity":"Find a distinct shot, framing or actual action; do not clone the previous image",
    "mechanical_equal_duration":"Re-cut at actual speech, semantic changes and action beats; do not use equal-length presets",
    "missing_audio":"Supply genuine narration and verify exact speech coverage before rendering",
    "missing_subtitles":"Generate subtitles from the locked real audio alignment",
    "character_drift":"Regenerate the affected shot from a verified character bible, then review against neighboring scenes",
    "narrative_redundancy":"Replace a paraphrased title card with a concrete scene, cause, proof or informative demonstration",
    "weak_causality":"Show observable start state, triggering action and resulting state",
    "bad_narration":"Replace narration with natural full-track speech then redo alignment and downstream timing",
    "subtitle_desync":"Realign actual narration and regenerate SRT, preview and final video",
}

def validate_findings(findings, critic, video, plan):
    check_report(critic,video,plan)
    clips=plan.get("clips",[])
    ids={x.get("visual_plan_id",x.get("id")) for x in clips}
    if not isinstance(findings,dict) or findings.get("version")!=1:
        raise ValueError("Findings version must be 1")
    if findings.get("critic_report_sha256")!=sha256_json(critic):
        raise ValueError("Findings tied to a different critic analysis")
    if findings.get("source_plan_sha256")!=sha256_json(plan):
        raise ValueError("Findings source edit plan changed")
    issues=findings.get("issues")
    if not isinstance(issues,list) or not issues:
        raise ValueError("At least one recorded defect is required")
    seen=set()
    for defect in issues:
        if not isinstance(defect,dict):
            raise ValueError("Issue must be an object")
        ident=defect.get("id")
        if not isinstance(ident,str) or not ident or ident in seen:
            raise ValueError("Issue IDs must be unique nonempty strings")
        seen.add(ident)
        if defect.get("issue_type") not in KINDS or defect.get("severity") not in SEVERITIES:
            raise ValueError(ident+": unknown issue type or severity")
        shot=defect.get("shot_id")
        if shot is not None and shot not in ids:
            raise ValueError(ident+": unknown shot ID")
        if not isinstance(defect.get("evidence"),str) or len(defect["evidence"].strip())<12:
            raise ValueError(ident+": concrete observed evidence required")
        if not isinstance(defect.get("proposed_fix"),str) or len(defect["proposed_fix"].strip())<12:
            raise ValueError(ident+": actionable proposed fix required")
        if not isinstance(defect.get("verification"),str) or len(defect["verification"].strip())<12:
            raise ValueError(ident+": objective follow-up check required")
    return issues

def compile_revision(findings,critic,video,plan,revision_id):
    issues=validate_findings(findings,critic,video,plan)
    if not isinstance(revision_id,str) or not revision_id or not all(x.isalnum() or x in "-_" for x in revision_id):
        raise ValueError("Safe nonempty revision id required")
    clips=plan["clips"]
    affected={x["shot_id"] for x in issues if x.get("shot_id")}
    global_defects=[x for x in issues if x.get("shot_id") is None]
    global_audio=any(x["issue_type"] in ("missing_audio","bad_narration","subtitle_desync") for x in global_defects)
    structural=any(x["issue_type"] in ("mechanical_equal_duration","duration_mismatch") for x in global_defects)
    # Keep source assets unless actually affected by a defect; all edits need
    # an updated EDL and rendered preview once any one shot is changed.
    regenerate=[]
    reusable=[]
    for clip in clips:
        sid=clip.get("visual_plan_id",clip.get("id"))
        if sid in affected:
            regenerate.append(sid)
        else:
            reusable.append(sid)
    tasks=[]
    for issue in issues:
        tasks.append({"issue_id":issue["id"],"shot_id":issue.get("shot_id"),
                      "severity":issue["severity"],"action":issue["proposed_fix"],
                      "verification":issue["verification"],"state":"open"})
    return {"version":1,"revision_id":revision_id,"status":"PLANNED_NOT_EXECUTED",
            "source_video_sha256":sha256(video),
            "source_plan_sha256":sha256_json(plan),
            "critic_report_sha256":sha256_json(critic),
            "findings_sha256":sha256_json(findings),
            "regenerate_source_shots":sorted(regenerate),
            "reusable_source_shots":sorted(reusable),
            "invalidate":["audio_timeline","subtitles","visual_plan","edit_plan",
                          "video_preview","formal_release","final_review"] if global_audio else
                         (["visual_plan","edit_plan","video_preview","formal_release","final_review"] if structural else
                          ["edit_plan","video_preview","formal_release","final_review"]),
            "notes":"Invalidate downstream composites/reviews, not unrelated candidate footage. If audio or narrative changes, revalidate all shot timing.",
            "tasks":tasks}

def verify_revision(record,findings,critic,video,plan):
    expected=compile_revision(findings,critic,video,plan,record["revision_id"])
    if record!=expected:
        raise ValueError("Revision differs from its immutable source evidence")
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--video",required=True)
    p.add_argument("--plan",required=True)
    p.add_argument("--critic",required=True)
    p.add_argument("--findings",required=True)
    p.add_argument("--revision-id",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--verify",action="store_true")
    a=p.parse_args()
    load=lambda f:json.loads(Path(f).read_text(encoding="utf-8"))
    inputs=(load(a.findings),load(a.critic),a.video,load(a.plan))
    if a.verify:
        verify_revision(load(a.out),*inputs)
        print(json.dumps({"status":"verified","revision_id":a.revision_id}))
    else:
        result=compile_revision(*inputs,a.revision_id)
        path=Path(a.out)
        if path.exists():
            raise FileExistsError("Existing revision cannot be silently overwritten")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
