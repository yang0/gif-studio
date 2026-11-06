#!/usr/bin/env python3
"""Independent GIF candidate library. No rendering, generation or QA claims."""
import argparse
import json
import re
import shutil
from pathlib import Path
from inspect_gif import digest

PATTERN=re.compile(r"^[A-Za-z0-9_-]+$")

def safe(value):
    if not PATTERN.fullmatch(value):
        raise ValueError("Invalid shot/candidate ID")
    return value

def path(project):
    return Path(project)/"library"/"catalog.json"

def read(project):
    p=path(project)
    if not p.is_file():
        return {"version":1,"candidates":{},"selections":{}}
    c=json.loads(p.read_text(encoding="utf-8"))
    if c.get("version")!=1 or not isinstance(c.get("candidates"),dict) or not isinstance(c.get("selections"),dict):
        raise ValueError("Invalid catalog")
    return c

def save(project,c):
    p=path(project)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(c,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def add(project,shot,candidate,gif,prompt,tool,reference,notes):
    root=Path(project).resolve()
    safe(shot);safe(candidate)
    gif=Path(gif).resolve()
    prompt=Path(prompt).resolve()
    if not gif.is_file() or not prompt.is_file():
        raise FileNotFoundError("GIF and exact prompt file required")
    if not tool.strip() or not reference.strip() or not notes.strip():
        raise ValueError("Actual tool, reference and notes required")
    with gif.open("rb") as f:
        if f.read(6) not in (b"GIF87a",b"GIF89a"):
            raise ValueError("Input not a GIF")
    c=read(root)
    key=f"{shot}/{candidate}"
    sha=digest(gif)
    if key in c["candidates"]:
        r=c["candidates"][key]
        if r["sha256"]!=sha:
            raise ValueError("Candidate ID already used for different bytes")
        return r
    destination=root/"library"/"candidates"/shot/(candidate+".gif")
    prompt_snapshot=root/"library"/"prompts"/shot/(candidate+".txt")
    destination.parent.mkdir(parents=True,exist_ok=True)
    prompt_snapshot.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists() and digest(destination)!=sha:
        raise ValueError("Candidate file collision")
    if prompt_snapshot.exists() and digest(prompt_snapshot)!=digest(prompt):
        raise ValueError("Candidate prompt collision")
    if destination!=gif:
        shutil.copyfile(gif,destination)
    if prompt_snapshot!=prompt:
        shutil.copyfile(prompt,prompt_snapshot)
    record={"shot_id":shot,"candidate_id":candidate,
            "file":str(destination.relative_to(root)),"sha256":sha,
            "prompt":str(prompt_snapshot.relative_to(root)),
            "prompt_sha256":digest(prompt_snapshot),
            "tool":tool,"reference":reference,"notes":notes,
            "status":"unreviewed"}
    c["candidates"][key]=record
    save(root,c)
    return record

def select(project,shot,candidate,reason,overwrite=False):
    root=Path(project).resolve()
    safe(shot);safe(candidate)
    if len(reason.strip())<12:
        raise ValueError("Editorial choice requires substantive reason")
    c=read(root)
    key=f"{shot}/{candidate}"
    r=c["candidates"].get(key)
    if r is None:
        raise ValueError("Candidate missing")
    src=root/r["file"]
    if not src.is_file() or digest(src)!=r["sha256"]:
        raise ValueError("Candidate missing or modified")
    destination=root/"gifs"/(shot+".gif")
    if destination.exists() and not overwrite:
        raise FileExistsError("Production slot exists; explicitly select --overwrite")
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,destination)
    c["selections"][shot]={"candidate_id":candidate,"sha256":r["sha256"],
                            "reason":reason.strip()}
    save(root,c)
    for suffix in (".json",".visual.json",".intake.json"):
        old=root/"qa"/(shot+suffix)
        if old.exists():
            old.unlink()
    return c["selections"][shot]

def selection_status(project,shot):
    root=Path(project).resolve()
    c=read(root)
    selected=c["selections"].get(shot)
    if selected is None:
        return False,"No candidate selected"
    record=c["candidates"].get(f"{shot}/{selected['candidate_id']}")
    if record is None:
        return False,"Catalog entry missing"
    source=root/record["file"]
    production=root/"gifs"/(shot+".gif")
    prompt=root/record["prompt"]
    if not source.is_file() or not production.is_file() or not prompt.is_file():
        return False,"File missing"
    if digest(source)!=record["sha256"] or digest(production)!=record["sha256"]:
        return False,"Selected GIF mismatch"
    if digest(prompt)!=record["prompt_sha256"]:
        return False,"Selected prompt changed"
    return True,"Selected GIF matches catalog"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("add")
    for arg in ("shot","candidate","gif","prompt","tool","reference","notes"):
        a.add_argument("--"+arg,required=True)
    b=sub.add_parser("select")
    for arg in ("shot","candidate","reason"):
        b.add_argument("--"+arg,required=True)
    b.add_argument("--overwrite",action="store_true")
    sub.add_parser("list")
    args=p.parse_args()
    if args.command=="add":
        out=add(args.project,args.shot,args.candidate,args.gif,args.prompt,args.tool,args.reference,args.notes)
    elif args.command=="select":
        out=select(args.project,args.shot,args.candidate,args.reason,args.overwrite)
    else:
        out=read(args.project)
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
