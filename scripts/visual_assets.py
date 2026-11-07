#!/usr/bin/env python3
"""Turn a verified A/B-roll plan into DISTINCT real GIF candidate production jobs.

Never generates substitute art. It writes exact scene-specific prompts and an
input-bound gif_batch manifest, then delegates only to an actual GIF backend.
Every existing output is checked against its immutable prompt and source.
"""
import argparse
import json
from pathlib import Path

from audio_timeline import sha256
from visual_plan import validate as validate_visual, sha256_json
from candidate_pool import read as read_catalog, safe
from reference_pack import validate as validate_refs

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def inside(root,relative):
    root=Path(root).resolve()
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute():
        raise ValueError("Asset path must be project-relative")
    target=(root/relative).resolve()
    if root not in target.parents:
        raise ValueError("Asset path escapes project")
    return target

def candidate_specs(scene):
    prod=scene.get("production")
    if not isinstance(prod,dict) or not isinstance(prod.get("candidates"),list) or not prod["candidates"]:
        raise ValueError(scene["id"]+": GIF requires production.candidates with independent treatments")
    return prod

def text_prompt(scene,take,style,speech,ref_id):
    must=take.get("must_show")
    if not isinstance(must,list) or len(must)<2 or any(not isinstance(x,str) or not x.strip() for x in must):
        raise ValueError(scene["id"]+": every candidate needs >=2 concrete must_show actions/objects")
    motion=take.get("distinctive_motion")
    framing=take.get("framing")
    if not isinstance(motion,str) or len(motion.strip())<12:
        raise ValueError(scene["id"]+": candidate requires its OWN concrete motion")
    if not isinstance(framing,str) or not framing.strip():
        raise ValueError(scene["id"]+": candidate requires a framing treatment")
    avoids=take.get("must_not_show",[])
    if not isinstance(avoids,list) or any(not isinstance(x,str) for x in avoids):
        raise ValueError(scene["id"]+": invalid must_not_show")
    return "\n".join([
       "Create one ORIGINAL animated GPT GIF. The following is the exact requested shot, not a collage.",
       "EDIT ROLE: "+scene["roll"]+"-roll / "+scene["role"],
       "ORIGINAL NARRATION: "+speech,
       "NARRATIVE GOAL: "+scene["visual_event"],
       "CANDIDATE: "+take["candidate_id"],
       "CAMERA AND FRAMING: "+framing,
       "ON-SCREEN MOTION (ACTUAL VISUAL CHANGE): "+motion,
       "MUST SHOW:\n"+"\n".join("- "+x for x in must),
       "MUST NOT SHOW:\n"+"\n".join("- "+x for x in avoids) if avoids else "MUST NOT SHOW: generic stock symbols, unrelated objects, text, logos.",
       "DURATION COVERAGE: "+str((scene["end_ms"]-scene["start_ms"])/1000)+" seconds; no static filler.",
       "ROLE RULE: A-roll conveys character/emotion/story; B-roll must explain the actual information.",
       "CHARACTER REFERENCE PACK: "+(ref_id or "none required for this shot"),
       "REFERENCE ATTACHMENT RULE: attach actual reference images if specified; never claim use if unsupported.",
       "STYLE LOCK:\n"+json.dumps(style,ensure_ascii=False,sort_keys=True,indent=2),
       "OUTPUT: one actual animated GIF with visible motion, not text, SVG, PPT or a story-board grid.",
       "Keep the objects, style, proportions and identity consistent across all frames.",
       ""
    ])

def plan(project,script,timeline,visual,audio,style,storyboard):
    root=Path(project).resolve()
    issues=validate_visual(visual,timeline,script,audio)
    if issues:
        raise ValueError("Audio/visual timeline invalid: "+"; ".join(issues))
    if not isinstance(style,dict) or not style.get("style_id"):
        raise ValueError("Actual style-lock.json with style_id required")
    board_ids={s["id"] for s in storyboard.get("shots",[])}
    if not board_ids:
        raise ValueError("Storyboard shots required for candidate review")
    words={s["id"]:s["text"] for s in timeline["segments"]}
    jobs=[]
    keys=set()
    unsupported=[]
    for scene in visual["shots"]:
        medium=scene["media_type"]
        if medium!="gpt_gif":
            unsupported.append({"scene":scene["id"],"media_type":medium,
                                "reason":"External real media handled by video_cut.py; never fabricate GIF"})
            continue
        prod=candidate_specs(scene)
        shot=safe(scene.get("source_shot_id"))
        if shot not in board_ids:
            raise ValueError(scene["id"]+": source_shot_id not present in storyboard")
        ref_rel=prod.get("reference_pack")
        if scene["roll"]=="A" and not ref_rel:
            raise ValueError(scene["id"]+": A-roll character must supply a real character reference pack")
        if ref_rel:
            ref=inside(root,ref_rel)
            if not ref.is_file():
                raise FileNotFoundError("Required reference pack missing: "+str(ref))
            errors=validate_refs(root,load(ref))
            if errors:
                raise ValueError("Reference pack invalid: "+"; ".join(errors))
        speech="".join(words[seg] for seg in scene["audio_segment_ids"])
        for variant in prod["candidates"]:
            if not isinstance(variant,dict):
                raise ValueError("candidate must be an object")
            take=safe(variant.get("candidate_id"))
            key=shot+"/"+take
            if key in keys:
                raise ValueError("Duplicate candidate across visual shots: "+key)
            keys.add(key)
            prompt=text_prompt(scene,variant,style,speech,ref_rel)
            name="prompts/v3/"+shot+"/"+take+".txt"
            jobs.append({"shot_id":shot,"candidate_id":take,"prompt":name,
                         "reference_pack":ref_rel,
                         "notes":str(variant.get("notes") or ("Visual "+scene["id"]+": "+variant["framing"])),
                         "_text":prompt,"visual_scene_id":scene["id"]})
    if not jobs:
        raise ValueError("Visual plan contains no GPT GIF production requests; use explicit video_cut.py for external media")
    provenance={
      "version":1,"visual_plan_sha256":sha256_json(visual),
      "audio_timeline_sha256":sha256_json(timeline),
      "audio_sha256":sha256(audio),
      "style_sha256":sha256_json(style),
      "storyboard_sha256":sha256_json(storyboard),
      "requested_count":len(jobs),"external_media":unsupported,
    }
    return jobs,provenance

def prepare(project,script_path=None,timeline_path=None,visual_path=None,audio_path=None,
            style_path=None,storyboard_path=None):
    root=Path(project).resolve()
    script_path=script_path or root/"script.json"
    timeline_path=timeline_path or root/"audio-timeline.json"
    visual_path=visual_path or root/"visual-plan.json"
    audio_path=audio_path or root/"audio"/"voiceover.wav"
    style_path=style_path or root/"style-lock.json"
    storyboard_path=storyboard_path or root/"storyboard.json"
    jobs,proof=plan(root,load(script_path),load(timeline_path),load(visual_path),
                    audio_path,load(style_path),load(storyboard_path))
    manifest=root/"production"/"visual-asset-plan.json"
    tasks={"version":1,"tasks":[{k:v for k,v in item.items()
           if k in ("shot_id","candidate_id","prompt","reference_pack","notes")}
           for item in jobs]}
    proof["tasks_sha256"]=sha256_json(tasks)
    existing=None
    if manifest.is_file():
        existing=load(manifest)
        if existing.get("provenance")!=proof or existing.get("batch")!=tasks:
            raise ValueError("Existing visual asset production plan is stale. Archive it and create new candidate IDs; never overwrite old prompts")
    for job in jobs:
        path=inside(root,job["prompt"])
        if path.is_file() and path.read_text(encoding="utf-8")!=job["_text"]:
            raise ValueError("Previously prepared prompt changed: "+job["shot_id"]+"/"+job["candidate_id"])
    for job in jobs:
        path=inside(root,job["prompt"])
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.is_file():
            path.write_text(job["_text"],encoding="utf-8")
    manifest.parent.mkdir(parents=True,exist_ok=True)
    if existing is None:
        manifest.write_text(json.dumps({"version":1,"provenance":proof,"batch":tasks},
                        ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"status":"prepared_not_generated","task_count":len(jobs),
            "external_media":proof["external_media"],"manifest":str(manifest),
            "production_approved":False}

def check(project):
    root=Path(project).resolve()
    path=root/"production"/"visual-asset-plan.json"
    if not path.is_file():
        return {"status":"missing","issues":["No production visual asset plan"]}
    saved=load(path)
    if saved.get("version")!=1 or "batch" not in saved or "provenance" not in saved:
        return {"status":"blocked","issues":["Invalid production plan"]}
    try:
        jobs,proof=plan(root,load(root/"script.json"),load(root/"audio-timeline.json"),
           load(root/"visual-plan.json"),root/"audio"/"voiceover.wav",
           load(root/"style-lock.json"),load(root/"storyboard.json"))
    except (ValueError,OSError,KeyError,TypeError) as exc:
        return {"status":"blocked","issues":[str(exc)]}
    tasks={"version":1,"tasks":[{k:v for k,v in j.items()
           if k in ("shot_id","candidate_id","prompt","reference_pack","notes")}
           for j in jobs]}
    proof["tasks_sha256"]=sha256_json(tasks)
    problems=[]
    if saved["provenance"]!=proof or saved["batch"]!=tasks:
        problems.append("Visual plan, script/audio, style or storyboard changed after task preparation")
    catalog=read_catalog(root)
    ready=0
    pending=[]
    seen_bytes={}
    for job in jobs:
        path=inside(root,job["prompt"])
        key=job["shot_id"]+"/"+job["candidate_id"]
        if not path.is_file() or path.read_text(encoding="utf-8")!=job["_text"]:
            problems.append(key+": generated prompt changed or is missing")
            continue
        rec=catalog["candidates"].get(key)
        if not rec:
            pending.append(key)
            continue
        gif=inside(root,rec["file"])
        src_prompt=inside(root,rec["prompt"])
        if (not gif.is_file() or not src_prompt.is_file()
            or sha256(gif)!=rec["sha256"] or sha256(src_prompt)!=rec["prompt_sha256"]
            or rec["prompt_sha256"]!=sha256(path)):
            problems.append(key+": candidate file or exact prompt differs from production job")
        else:
            if rec["sha256"] in seen_bytes:
                problems.append(key+": byte-identical GIF reused from "+seen_bytes[rec["sha256"]])
            seen_bytes[rec["sha256"]]=key
            ready+=1
    return {"status":"blocked" if problems else ("produced_unreviewed" if not pending else "awaiting_generation"),
            "issues":problems,"produced_count":ready,
            "pending":pending,"total":len(jobs),
            "visual_approval":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    cmd=p.add_mutually_exclusive_group(required=True)
    cmd.add_argument("--prepare",action="store_true")
    cmd.add_argument("--status",action="store_true")
    cmd.add_argument("--run",action="store_true")
    p.add_argument("--backend-file",help="Trusted backend command JSON; needed for --run")
    p.add_argument("--workers",type=int,default=2)
    p.add_argument("--timeout",type=int,default=120)
    p.add_argument("--max-attempts",type=int,default=2)
    args=p.parse_args()
    if args.status:
        result=check(args.project)
    else:
        result=prepare(args.project)
        if args.run:
            if not args.backend_file:
                p.error("--run requires --backend-file (actual supported GIF generator)")
            from gif_batch import run
            backend=load(args.backend_file)
            plan_file=Path(args.project)/"production"/"visual-asset-plan.json"
            batch=load(plan_file)["batch"]
            result=run(args.project,batch,backend,args.workers,args.timeout,args.max_attempts)
            result["production_status"]=check(args.project)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if (args.status and result["status"]=="blocked") or (
        args.run and result.get("ingested")!=result.get("total")):
        raise SystemExit(1)

if __name__=="__main__":
    main()
