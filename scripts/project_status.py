#!/usr/bin/env python3
"""Report what remains before genuine reviewed production can be delivered."""
import argparse
import json
from pathlib import Path
from qa_gate import shot_quality
from production_contract import production_preflight
from validate_storyboard import validate

def status(project, storyboard):
    board = json.loads(Path(storyboard).read_text(encoding="utf-8"))
    errors = validate(board)
    if errors:
        raise ValueError("Invalid storyboard: "+"; ".join(errors))
    shots = []
    for item in board["shots"]:
        state, reason = shot_quality(project,item["id"],board)
        shots.append({"id":item["id"],"status":state,"reason":reason})
    issues = production_preflight(project, board)
    return {"shots":shots,"production_issues":issues,
            "ready":not issues and all(x["status"]=="ready" for x in shots)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--storyboard",required=True)
    p.add_argument("--report")
    a=p.parse_args()
    result=status(a.project,a.storyboard)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if a.report:
        path=Path(a.report)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
