#!/usr/bin/env python3
"""Execute real GIF generator backends concurrently, then safely ingest results.

Backend is an explicitly configured LOCAL executable. It MUST implement:
  <command...> --capabilities   => JSON {"version":1,"gif":true,
                                    "explicit_prompt":true,"reference_images":true/false}
  <command...> --generate       => accepts one JSON object on stdin and emits
                                    one JSON object to stdout (no prose).
The backend is responsible for invoking an actual available GIF generator,
sending the *literal prompt* and reference image bytes, and writing its output.
Its declaration is operator provenance, not cryptographic remote attestation.

No image/video is synthesized by this orchestration layer.
"""
import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

from audio_timeline import sha256
from candidate_pool import read as read_catalog, safe
from generator_adapter import request as prepare_request, ingest
from reference_pack import validate as validate_references, file_in_project, ROLES

INGEST_LOCK=threading.Lock()
RETRYABLE={"timeout","backend_failure"}
MAX_WORKERS=4
MAX_ATTEMPTS=3

def atomic_json(path, value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+".writing-"+str(os.getpid())+"-"+str(threading.get_ident()))
    try:
        tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        os.replace(tmp,path)
    finally:
        if tmp.exists():
            tmp.unlink()

def checked_command(command):
    if not isinstance(command,list) or not command or any(not isinstance(x,str) or not x for x in command):
        raise ValueError("Backend command must be a nonempty JSON array of executable and arguments")
    if any(x in ("-c","-m") for x in command):
        # No dynamic Python snippets as backend definitions.
        raise ValueError("Use a real executable backend script; no python -c or -m")
    return command

def call_backend(command, mode, payload=None, timeout=120):
    try:
        result=subprocess.run(checked_command(command)+[mode],
                              input=json.dumps(payload,ensure_ascii=False) if payload is not None else None,
                              capture_output=True,text=True,timeout=timeout,check=False)
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"Backend {mode} timed out after {timeout}s") from exc
    if result.returncode:
        raise RuntimeError(f"Backend exited {result.returncode}: {result.stderr[-1200:]}")
    try:
        value=json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("Backend must return exactly one JSON object on stdout") from exc
    if not isinstance(value,dict):
        raise ValueError("Backend output must be JSON object")
    return value

def backend_capabilities(command, timeout):
    caps=call_backend(command,"--capabilities",timeout=timeout)
    if caps.get("version")!=1 or caps.get("gif") is not True or caps.get("explicit_prompt") is not True:
        raise ValueError("Backend cannot explicitly generate actual GIF from a complete prompt")
    return caps

def validate_tasks(tasks):
    if not isinstance(tasks,dict) or tasks.get("version")!=1 or not isinstance(tasks.get("tasks"),list) or not tasks["tasks"]:
        raise ValueError("Batch manifest requires nonempty version 1 tasks")
    seen=set()
    for entry in tasks["tasks"]:
        if not isinstance(entry,dict):
            raise ValueError("Each batch task must be an object")
        shot=safe(entry.get("shot_id"))
        take=safe(entry.get("candidate_id"))
        key=shot+"/"+take
        if key in seen:
            raise ValueError("Duplicate task "+key)
        seen.add(key)
        if not isinstance(entry.get("prompt"),str) or not entry["prompt"].strip():
            raise ValueError(key+": prompt path required")
        if not isinstance(entry.get("notes"),str) or not entry["notes"].strip():
            raise ValueError(key+": notes required")
    return tasks["tasks"]

def prepare(project, entry, supports_references):
    root=Path(project).resolve()
    prompt=(root/entry["prompt"]).resolve()
    if root not in prompt.parents or not prompt.is_file():
        raise ValueError("Prompt must be a real file inside project")
    if not prompt.read_text(encoding="utf-8").strip():
        raise ValueError("Prompt cannot be blank")
    ref=None
    refs={}
    if entry.get("reference_pack"):
        ref=(root/entry["reference_pack"]).resolve()
        if root not in ref.parents or not ref.is_file():
            raise ValueError("Reference pack must be inside project")
        manifest=json.loads(ref.read_text(encoding="utf-8"))
        errors=validate_references(root,manifest)
        if errors:
            raise ValueError("Reference pack invalid: "+"; ".join(errors))
        if not supports_references:
            raise ValueError("Backend does not support reference image attachments; refusing to silently omit character bible")
        for role in ROLES:
            info=manifest["references"][role]
            image=file_in_project(root,info["file"])
            refs[role]={"path":str(image),"sha256":sha256(image)}
    pending=prepare_request(root,entry["shot_id"],entry["candidate_id"],prompt,ref)
    payload={
        "version":1,"shot_id":entry["shot_id"],"candidate_id":entry["candidate_id"],
        "prompt":prompt.read_text(encoding="utf-8"),
        "prompt_sha256":pending["prompt_sha256"],
        "reference_pack_sha256":pending["reference_pack_sha256"],
        "references":refs,
        "format":"gif",
    }
    return payload

def execute_one(project, entry, command, caps, timeout, max_attempts):
    root=Path(project).resolve()
    shot=entry["shot_id"];take=entry["candidate_id"]
    key=shot+"/"+take
    status=root/"production"/"batch"/shot/(take+".json")
    saved=json.loads(status.read_text(encoding="utf-8")) if status.is_file() else {}
    existing=read_catalog(root)["candidates"].get(key)
    if existing:
        gif=root/existing["file"];prompt=root/existing["prompt"]
        if gif.is_file() and prompt.is_file() and sha256(gif)==existing["sha256"] and sha256(prompt)==existing["prompt_sha256"]:
            result={"key":key,"status":"already_ingested","gif_sha256":existing["sha256"]}
            atomic_json(status,result)
            return result
        return {"key":key,"status":"blocked","error":"Registered candidate bytes changed; refusing overwrite"}
    try:
        payload=prepare(root,entry,caps["reference_images"] is True if "reference_images" in caps else False)
    except Exception as exc:
        result={"key":key,"status":"blocked","error":str(exc)}
        atomic_json(status,result)
        return result
    input_hash=sha256_json(payload)
    if saved.get("input_sha256") and saved["input_sha256"]!=input_hash:
        result={"key":key,"status":"blocked","error":"Input changed since prior run; use a new candidate ID"}
        atomic_json(status,result)
        return result
    attempt=saved.get("attempts",0) if saved.get("status") in ("failed","interrupted") else 0
    if saved.get("status") in ("failed","interrupted") and attempt>=max_attempts:
        result={"key":key,"status":"attempts_exhausted","attempts":attempt,"input_sha256":input_hash}
        atomic_json(status,result)
        return result
    while attempt<max_attempts:
        attempt+=1
        work=root/"production"/"batch"/shot/(take+"-attempt-"+str(attempt))
        work.mkdir(parents=True,exist_ok=True)
        outgoing=dict(payload)
        outgoing["output_directory"]=str(work)
        atomic_json(status,{"key":key,"status":"running","input_sha256":input_hash,"attempts":attempt})
        try:
            result=call_backend(command,"--generate",outgoing,timeout=timeout)
            if result.get("version")!=1 or result.get("tool") is None or not result.get("output_reference"):
                raise ValueError("Backend must declare actual tool and output reference")
            if result.get("prompt_sha256")!=payload["prompt_sha256"]:
                raise ValueError("Backend did not confirm exact prompt SHA")
            if result.get("reference_pack_sha256")!=payload["reference_pack_sha256"]:
                raise ValueError("Backend did not confirm reference pack SHA")
            sent=result.get("attached_reference_sha256",{})
            if payload["references"] and (not isinstance(sent,dict) or sent!={k:v["sha256"] for k,v in payload["references"].items()}):
                raise ValueError("Backend did not confirm every actual reference image attachment")
            file=Path(result.get("gif_path","")).resolve()
            if work not in file.parents or not file.is_file():
                raise ValueError("Backend output GIF must be saved inside the designated attempt directory")
            from verify_gif_asset import validate as gif_check
            check=gif_check(file)
            if not check.get("pass"):
                raise ValueError("Actual generated GIF failed technical intake: "+"; ".join(check.get("issues",[])))
            receipt={"version":1,"tool":result["tool"],
                     "output_reference":result["output_reference"],
                     "prompt_sha256":payload["prompt_sha256"],
                     "reference_pack_sha256":payload["reference_pack_sha256"],
                     "prompt_delivery":"explicit_tool_argument"}
            receipt_path=work/"receipt.json"
            atomic_json(receipt_path,receipt)
            with INGEST_LOCK:
                registered=ingest(root,shot,take,file,receipt_path,entry["notes"])
            outcome={"key":key,"status":"ingested_unreviewed",
                     "attempts":attempt,"input_sha256":input_hash,
                     "gif_sha256":registered["candidate"]["sha256"],
                     "tool":result["tool"],"output_reference":result["output_reference"],
                     "reference_sha256":payload["reference_pack_sha256"],
                     "backend_receipt_is_operator_declaration":True}
            atomic_json(status,outcome)
            return outcome
        except (TimeoutError,RuntimeError) as exc:
            # Only transient runtime/backend failures retry. Invalid GIFs,
            # mismatched claims and missing reference attachment need correction.
            error=str(exc)
            atomic_json(status,{"key":key,"status":"failed","attempts":attempt,
                               "input_sha256":input_hash,"error":error})
            if attempt==max_attempts:
                return {"key":key,"status":"failed","attempts":attempt,"error":error}
        except Exception as exc:
            outcome={"key":key,"status":"blocked","attempts":attempt,
                     "input_sha256":input_hash,"error":str(exc)}
            atomic_json(status,outcome)
            return outcome
    return {"key":key,"status":"failed","attempts":attempt}

def sha256_json(obj):
    import hashlib
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,
             separators=(",",":")).encode("utf-8")).hexdigest()

def run(project,manifest,command,workers=2,timeout=120,max_attempts=2):
    if not 1<=workers<=MAX_WORKERS:
        raise ValueError("workers must be 1..4")
    if not 1<=max_attempts<=MAX_ATTEMPTS:
        raise ValueError("max_attempts must be 1..3")
    if timeout<1 or timeout>3600:
        raise ValueError("timeout must be between 1 and 3600 seconds")
    entries=validate_tasks(manifest)
    caps=backend_capabilities(command,min(timeout,30))
    outcomes=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(execute_one,project,task,command,caps,timeout,max_attempts) for task in entries]
        for f in concurrent.futures.as_completed(futures):
            outcomes.append(f.result())
    outcomes.sort(key=lambda r:r["key"])
    output={"status":"batch_finished","total":len(outcomes),
            "ingested":sum(x["status"] in ("ingested_unreviewed","already_ingested") for x in outcomes),
            "results":outcomes,
            "visual_approval":False}
    atomic_json(Path(project)/"production"/"batch"/"batch-summary.json",output)
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--tasks",required=True)
    p.add_argument("--backend",required=True,help="JSON array of executable and arguments; no shell execution")
    p.add_argument("--workers",type=int,default=2)
    p.add_argument("--timeout",type=int,default=120)
    p.add_argument("--max-attempts",type=int,default=2)
    args=p.parse_args()
    result=run(args.project,json.loads(Path(args.tasks).read_text(encoding="utf-8")),
               json.loads(args.backend),args.workers,args.timeout,args.max_attempts)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result["ingested"]!=result["total"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()
