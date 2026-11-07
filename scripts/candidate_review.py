#!/usr/bin/env python3
"""Independent review records for every immutable GPT GIF candidate.

Candidate QA is separate from the legacy selected-shot QA. Technical analysis
is automatic; semantic approval needs a reviewer who actually watched the GIF.
A declaration of an external GPT tool call is NOT cryptographic attestation.
"""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from candidate_pool import read as read_catalog
from inspect_gif import digest, inspect
from production_contract import fingerprint
from verify_gif_asset import validate as strict_check

CHECKS = ("semantic", "motion", "style", "composition", "continuity")
TOKEN = re.compile(r"^[A-Za-z0-9_-]+$")

def paths(project, shot, candidate):
    if not TOKEN.fullmatch(shot) or not TOKEN.fullmatch(candidate):
        raise ValueError("Invalid candidate identifier")
    base=Path(project).resolve()/"qa"/"candidates"/shot
    return base/(candidate+".technical.json"), base/(candidate+".approval.json")

def identity(project, shot, candidate):
    root=Path(project).resolve()
    rec=read_catalog(root)["candidates"].get(shot+"/"+candidate)
    if rec is None:
        raise ValueError("Candidate not in library")
    gif=root/rec["file"]
    prompt=root/rec["prompt"]
    if not gif.is_file() or digest(gif)!=rec["sha256"]:
        raise ValueError("Candidate GIF bytes differ from library")
    if not prompt.is_file() or digest(prompt)!=rec["prompt_sha256"]:
        raise ValueError("Candidate prompt differs from library")
    if not rec.get("tool") or not rec.get("reference"):
        raise ValueError("Candidate has no declared generation origin")
    return rec,gif

def context(project, storyboard, shot):
    root=Path(project).resolve()
    board=json.loads(Path(storyboard).read_text(encoding="utf-8"))
    item=next((x for x in board.get("shots",[]) if x.get("id")==shot),None)
    if item is None:
        raise ValueError("Candidate's shot absent from storyboard")
    director=root/"director-plan.json"
    style=root/"style-lock.json"
    if not director.is_file() or not style.is_file():
        raise FileNotFoundError("Director plan and style lock required")
    plan=json.loads(director.read_text(encoding="utf-8"))
    decision=next((x for x in plan.get("shots",[]) if x.get("id")==shot),None)
    if decision is None or decision.get("asset_policy")!="new_gpt_gif":
        raise ValueError("Candidate shot must have new_gpt_gif director decision")
    return {"shot_sha256":fingerprint(item),
            "director_sha256":fingerprint(decision),
            "style_sha256":digest(style)}

def inspect_candidate(project, storyboard, shot, candidate):
    rec,gif=identity(project,shot,candidate)
    ctx=context(project,storyboard,shot)
    technical,approval=paths(project,shot,candidate)
    technical.parent.mkdir(parents=True,exist_ok=True)
    sheet=technical.parent/(candidate+"-sheet.jpg")
    strict=strict_check(gif)
    visual=inspect(gif,0,1e9,sheet)
    problems=list(strict.get("issues",[]))+list(visual.get("issues",[]))
    report={"shot_id":shot,"candidate_id":candidate,
            "source_sha256":rec["sha256"],
            "prompt_sha256":rec["prompt_sha256"],
            "tool":rec["tool"],"reference":rec["reference"],
            "prompt_delivery":rec.get("prompt_delivery","context_only_unverified"),
            "context":ctx,"technical_pass":not problems,
            "issues":problems,"warnings":visual.get("warnings",[]),
            "contact_sheet":str(sheet.resolve()),
            "contact_sheet_sha256":digest(sheet) if sheet.is_file() else None,
            "gif_duration_sec":visual.get("duration_sec"),
            "width":visual.get("width"),"height":visual.get("height"),
            "review_status":"pending_human_visual_review"}
    technical.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Re-inspection is not approval. Existing approval can remain only if
    # it is still bound to *exactly* the same source and review evidence.
    return report

def status(project,storyboard,shot,candidate):
    try:
        rec,gif=identity(project,shot,candidate)
        ctx=context(project,storyboard,shot)
        tech,approved=paths(project,shot,candidate)
        if not tech.is_file():
            return "uninspected","No technical report"
        technical=json.loads(tech.read_text(encoding="utf-8"))
        if (not technical.get("technical_pass") or
            technical.get("source_sha256")!=rec["sha256"] or
            technical.get("prompt_sha256")!=rec["prompt_sha256"] or
            technical.get("context")!=ctx):
            return "stale","Technical report failed or no longer matches source/director"
        sheet=Path(technical.get("contact_sheet",""))
        if not sheet.is_file() or digest(sheet)!=technical.get("contact_sheet_sha256"):
            return "stale","Contact sheet missing or modified"
        if not approved.is_file():
            return "technical_passed","Independent visual approval missing"
        review=json.loads(approved.read_text(encoding="utf-8"))
        if (review.get("source_sha256")!=rec["sha256"] or
            review.get("prompt_sha256")!=rec["prompt_sha256"] or
            review.get("context")!=ctx or
            review.get("technical_sha256")!=digest(tech)):
            return "stale","Visual approval no longer matches technical report or source"
        if any(review.get("checks",{}).get(key) is not True for key in CHECKS):
            return "stale","Incomplete visual approval"
        if review.get("prompt_delivery")!=rec.get("prompt_delivery","context_only_unverified"):
            return "stale","Candidate prompt delivery changed in catalog"
        if not review.get("reviewer") or not review.get("notes"):
            return "stale","Reviewer evidence missing"
        if review.get("prompt_delivery")!="explicit_tool_argument":
            return "blocked","Exact GPT prompt delivery not confirmed"
        return "ready","Candidate has matching technical/provenance/visual review"
    except (OSError,ValueError,KeyError,TypeError) as err:
        return "stale",str(err)

def approve_candidate(project,storyboard,shot,candidate,reviewer,notes,checks,
                      prompt_delivery):
    if not reviewer or len(notes.strip())<24:
        raise ValueError("Named reviewer and substantive observed visual notes required")
    if any(checks.get(k) is not True for k in CHECKS):
        raise ValueError("All five candidate visual checks must be explicitly true")
    tech,approval=paths(project,shot,candidate)
    rec,_=identity(project,shot,candidate)
    if prompt_delivery!="explicit_tool_argument" or rec.get("prompt_delivery","context_only_unverified")!="explicit_tool_argument":
        raise ValueError("Formal GPT GIF candidate requires explicitly documented prompt delivery at library ingestion")
    ctx=context(project,storyboard,shot)
    if not tech.is_file():
        raise ValueError("Run candidate review --inspect before approval")
    data=json.loads(tech.read_text(encoding="utf-8"))
    if (not data.get("technical_pass") or
        data.get("source_sha256")!=rec["sha256"] or
        data.get("prompt_sha256")!=rec["prompt_sha256"] or
        data.get("context")!=ctx or
        not Path(data.get("contact_sheet","")).is_file() or
        digest(data["contact_sheet"])!=data.get("contact_sheet_sha256")):
        raise ValueError("Candidate technical review stale or failed")
    record={"shot_id":shot,"candidate_id":candidate,
            "source_sha256":rec["sha256"],
            "prompt_sha256":rec["prompt_sha256"],"context":ctx,
            "prompt_delivery":prompt_delivery,
            "technical_sha256":digest(tech),
            "reviewer":reviewer.strip(),"notes":notes.strip(),
            "checks":{key:True for key in CHECKS},
            "approved_at":datetime.now(timezone.utc).isoformat()}
    approval.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return record

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--storyboard",required=True)
    p.add_argument("--shot",required=True)
    p.add_argument("--candidate",required=True)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect",action="store_true")
    mode.add_argument("--approve",action="store_true")
    mode.add_argument("--status",action="store_true")
    p.add_argument("--reviewer")
    p.add_argument("--notes")
    p.add_argument("--prompt-delivery",default="context_only_unverified",
                   choices=("explicit_tool_argument","context_only_unverified"))
    for key in CHECKS:
        p.add_argument("--"+key+"-pass",action="store_true")
    a=p.parse_args()
    if a.inspect:
        result=inspect_candidate(a.project,a.storyboard,a.shot,a.candidate)
    elif a.approve:
        result=approve_candidate(a.project,a.storyboard,a.shot,a.candidate,
                    a.reviewer or "",a.notes or "",
                    {k:getattr(a,k+"_pass") for k in CHECKS},a.prompt_delivery)
    else:
        state,why=status(a.project,a.storyboard,a.shot,a.candidate)
        result={"status":state,"reason":why}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
