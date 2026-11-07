#!/usr/bin/env python3
"""Apply an approved selective rework plan as a NEW video project revision.

No fake generation. Replacements are already-existing, hash-verified real media.
Global narration or timeline defects block until audio is actually re-recorded.
Unchanged FFmpeg clip-cache entries are carried forward and validated on use.
"""
import argparse
import json
import shutil
from pathlib import Path
from audio_timeline import sha256
from revision_planner import verify_revision
from video_cut import compile_plan,inside
from visual_plan import sha256_json

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def create(project,revision,findings,critic,original_video,original_plan,replacements):
    source=Path(project).resolve()
    verify_revision(revision,findings,critic,original_video,original_plan)
    if replacements.get("version")!=1 or replacements.get("revision_id")!=revision["revision_id"]:
        raise ValueError("Replacement list has wrong revision identity")
    items=replacements.get("replacements")
    affected=set(revision["regenerate_source_shots"])
    if not isinstance(items,dict) or set(items)!=affected:
        raise ValueError("Exactly one actual replacement per affected shot required")
    if "audio_timeline" in revision["invalidate"]:
        raise ValueError("Narration/timecode defect needs new real full-track audio and alignment; cannot reuse old timeline")
    if revision["status"]!="PLANNED_NOT_EXECUTED":
        raise ValueError("Only verified unexecuted revision plans can be applied")
    original_visual=read(source/"visual-plan.json")
    proposed=replacements.get("revised_visual_plan")
    visual=json.loads(json.dumps(proposed if proposed is not None else original_visual))
    if proposed is not None:
        from visual_plan import validate as validate_visual
        previous={x["id"]:x for x in original_visual["shots"]}
        if set(x["id"] for x in visual.get("shots",[]))!=set(previous) or len(visual["shots"])!=len(original_visual["shots"]):
            raise ValueError("Re-cut cannot silently remove or duplicate existing source shot IDs")
        problems=validate_visual(visual,read(source/"audio-timeline.json"),
                                 read(source/"script.json"),source/"audio"/"voiceover.wav")
        if problems:
            raise ValueError("Re-cut not aligned to real narration: "+"; ".join(problems))
        for shot in visual["shots"]:
            old=previous[shot["id"]]
            if shot["id"] not in affected:
                for field in ("source_file","source_sha256","source_shot_id","candidate_id","media_type"):
                    if shot.get(field)!=old.get(field):
                        raise ValueError("Re-cut changed an unaffected source without a registered replacement")
        if "visual_plan" not in revision["invalidate"]:
            raise ValueError("Revision plan does not authorize changing the real visual timeline")
    elif not affected and "visual_plan" in revision["invalidate"]:
        raise ValueError("Structural rework requires an explicitly revised, real-audio-aligned visual plan")
    by_id={x["id"]:x for x in visual["shots"]}
    for sid,entry in items.items():
        if sid not in by_id or not isinstance(entry,dict):
            raise ValueError("Replacement shot missing from original visual timeline")
        shot=by_id[sid]
        if shot.get("media_type")=="gpt_gif":
            # Existing candidate-pool mechanism: never fabricate a new GPT GIF.
            if not isinstance(entry.get("candidate_id"),str) or not entry["candidate_id"]:
                raise ValueError("Real GIF replacement requires a registered new candidate ID")
            from candidate_pool import read as catalog
            key=str(shot.get("source_shot_id",""))+"/"+entry["candidate_id"]
            if key not in catalog(source)["candidates"]:
                raise ValueError("Replacement GIF not in the actual candidate catalog: "+key)
            if entry["candidate_id"]==shot.get("candidate_id"):
                raise ValueError("Old GIF candidate cannot be reused as a supposedly reworked shot")
            shot["candidate_id"]=entry["candidate_id"]
        else:
            newpath=entry.get("source_file")
            if not isinstance(newpath,str) or not newpath:
                raise ValueError("Non-GIF replacement requires real source_file")
            actual=inside(source,newpath)
            if sha256(actual)!=entry.get("source_sha256"):
                raise ValueError("Replacement SHA mismatch; no invented assets")
            if newpath==shot.get("source_file"):
                raise ValueError("Source filename must change to preserve the prior approved revision")
            shot["source_file"]=newpath
            shot["source_sha256"]=sha256(actual)
            if shot["media_type"]=="data_motion":
                proof=Path(str(actual)+".motion.json")
                if not proof.is_file() or read(proof).get("source_sha256")!=sha256(actual):
                    raise ValueError("Replacement information motion has no valid real source proof")
        shot["cut_reason"]=entry.get("cut_reason",shot["cut_reason"])
    # The director hash is bound to old visual structure. A reworked shot changes
    # visual metadata; a genuine new director decision MUST be supplied and
    # reviewed separately, never synthesized by this executor.
    newdirector=replacements.get("director_plan")
    if (source/"director-v2.json").is_file():
        if not isinstance(newdirector,dict):
            raise ValueError("v3.1 revision needs an explicit revised semantic director plan")
        from visual_director import validate as validate_director
        timeline=read(source/"audio-timeline.json")
        problems=[x for x in validate_director(newdirector,timeline,visual)
                  if not x.endswith("(warning)")]
        if problems:
            raise ValueError("New creative direction invalid: "+"; ".join(problems))
    target=source/"revisions"/revision["revision_id"]/"project"
    if target.exists():
        raise FileExistsError("Revision project already exists and will not be overwritten")
    staged=source/"revisions"/(revision["revision_id"]+".staging")
    if staged.exists():
        raise FileExistsError("Unfinished staging project exists; inspect before retrying")
    staged.parent.mkdir(parents=True,exist_ok=True)
    def ignore(directory,names):
        if Path(directory).resolve()==source:
            return set(names)&{"revisions","build","qa","quality","video-plan.json"}
        return set()
    try:
        shutil.copytree(source,staged,ignore=ignore)
        (staged/"visual-plan.json").write_text(
            json.dumps(visual,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        if newdirector is not None:
            (staged/"director-v2.json").write_text(
                json.dumps(newdirector,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        original_cache=source/"build"/"video-preview"/"clips"
        if original_cache.is_dir():
            shutil.copytree(original_cache,staged/"build"/"video-preview"/"clips")
        output=compile_plan(staged,read(staged/"script.json"),
                            read(staged/"audio-timeline.json"),visual,
                            staged/"audio"/"voiceover.wav",
                            read(staged/"storyboard.json"),True)
        (staged/"video-plan.json").write_text(
            json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        record={"version":1,"status":"REVISION_READY_FOR_NEW_PREVIEW",
                "revision_id":revision["revision_id"],
                "source_video_sha256":revision["source_video_sha256"],
                "source_plan_sha256":revision["source_plan_sha256"],
                "new_visual_plan_sha256":sha256_json(visual),
                "new_edit_plan_sha256":sha256_json(output),
                "regenerated_sources":sorted(affected),
                "reused_sources":revision["reusable_source_shots"],
                "review_state":"NO_REVIEW_CARRIED_FORWARD",
                "instructions":"Render a new preview, run critic/human review, then formal mixed approval"}
        (staged/"revision-receipt.json").write_text(
            json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        target.parent.mkdir(parents=True,exist_ok=True)
        staged.rename(target)
        return {"project":str(target),"status":record["status"],
                "regenerated_sources":sorted(affected),
                "reused_sources":revision["reusable_source_shots"]}
    except Exception:
        if staged.exists():
            shutil.rmtree(staged)
        raise

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True);p.add_argument("--revision",required=True)
    p.add_argument("--findings",required=True);p.add_argument("--critic",required=True)
    p.add_argument("--source-video",required=True);p.add_argument("--plan",required=True)
    p.add_argument("--replacements",required=True)
    a=p.parse_args()
    result=create(a.project,read(a.revision),read(a.findings),read(a.critic),
                  a.source_video,read(a.plan),read(a.replacements))
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
