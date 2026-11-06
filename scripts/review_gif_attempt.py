#!/usr/bin/env python3
"""Human/agent-recorded GIF generation failure. Never self-certifies quality."""
import argparse
import json
import re
from datetime import datetime,timezone
from pathlib import Path
from build_gif_prompts import build_prompt
from inspect_gif import digest
from production_contract import fingerprint

CATEGORIES=("wrong_subject","wrong_action","generic_symbols","style_drift",
            "object_morphing","text_artifacts","composition","other")

def reject(project,shot_id,category,observation,reviewer,storyboard):
    if not re.fullmatch(r"[A-Za-z0-9_-]+",shot_id):
        raise ValueError("Invalid shot")
    if category not in CATEGORIES:
        raise ValueError("Invalid category")
    if len(observation.strip())<16 or not reviewer.strip():
        raise ValueError("Concrete observation and named reviewer required")
    project=Path(project)
    board=json.loads(Path(storyboard).read_text(encoding="utf-8"))
    plan=json.loads((project/"director-plan.json").read_text(encoding="utf-8"))
    style=json.loads((project/"style-lock.json").read_text(encoding="utf-8"))
    shot=next(s for s in board["shots"] if s["id"]==shot_id)
    decision=next(s for s in plan["shots"] if s["id"]==shot_id)
    gif=project/"gifs"/(shot_id+".gif")
    if not gif.is_file():
        raise FileNotFoundError(gif)
    log_path=project/"qa"/(shot_id+".attempts.json")
    log={"shot_id":shot_id,"failures":[]}
    if log_path.exists():
        log=json.loads(log_path.read_text(encoding="utf-8"))
    current_director_fingerprint = fingerprint(decision)
    if log.get("director_fingerprint") != current_director_fingerprint:
        previous = log.get("failures", [])
        archive = log.get("archived_cycles", [])
        if previous:
            archive.append({"director_fingerprint":log.get("director_fingerprint"),
                            "failures":previous})
        log = {"shot_id":shot_id, "failures":[],
               "director_fingerprint":current_director_fingerprint,
               "archived_cycles":archive}
    failures=log["failures"]
    if len(failures)>=2:
        raise ValueError("Two failed attempts; first revise the director plan")
    sha=digest(gif)
    if failures and failures[-1]["gif_sha256"]==sha:
        raise ValueError("Cannot record same failed GIF as a new generation")
    prompt_path=(project/"prompts"/(shot_id+".txt") if not failures else
                 project/"prompts"/(shot_id+".retry-2.txt"))
    if not prompt_path.is_file():
        raise FileNotFoundError(prompt_path)
    failures.append({"attempt":len(failures)+1,"category":category,
                     "observation":observation.strip(),"reviewer":reviewer,
                     "gif_sha256":sha,"prompt_sha256":digest(prompt_path),
                     "recorded_at":datetime.now(timezone.utc).isoformat()})
    log_path.parent.mkdir(parents=True,exist_ok=True)
    log_path.write_text(json.dumps(log,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if len(failures)==1:
        retry=build_prompt(shot,decision,style,attempt=2,issue=category+": "+observation)
        path=project/"prompts"/(shot_id+".retry-2.txt")
        path.write_text(retry,encoding="utf-8")
        return {"status":"retry_ready","prompt":str(path)}
    return {"status":"blocked_replan",
            "next_step":"Revise director-plan.json after two semantic failures; do not substitute vectors"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--storyboard",required=True)
    p.add_argument("--shot",required=True)
    p.add_argument("--category",required=True,choices=CATEGORIES)
    p.add_argument("--observation",required=True)
    p.add_argument("--reviewer",required=True)
    a=p.parse_args()
    print(json.dumps(reject(a.project,a.shot,a.category,a.observation,
                            a.reviewer,a.storyboard),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
