#!/usr/bin/env python3
"""Structural checks only; naturalness and causal coherence require semantic review."""
import argparse
import json
import re
from pathlib import Path

def normalize(text):
    return re.sub(r"\s+", "", text or "")

def audit(script, storyboard=None):
    issues, warnings = [], []
    paragraphs = script.get("paragraphs", [])
    if not isinstance(paragraphs, list) or not paragraphs:
        return {"pass":False,"issues":["Nonempty paragraphs required"],"warnings":[]}
    for key in ("title","central_question","thesis","structure"):
        if not isinstance(script.get(key),str) or not script[key].strip():
            issues.append(key+" is required")
    seen = set()
    for i,p in enumerate(paragraphs):
        if not isinstance(p,dict):
            issues.append(f"paragraph {i+1} must be object")
            continue
        pid=p.get("id")
        if not isinstance(pid,str) or not re.fullmatch(r"p[0-9]+",pid):
            issues.append(f"paragraph {i+1} invalid id")
        elif pid in seen:
            issues.append(f"duplicate paragraph id {pid}")
        else:
            seen.add(pid)
        if not isinstance(p.get("text"),str) or not p["text"].strip():
            issues.append(f"paragraph {i+1} empty text")
        if i and not isinstance(p.get("handoff"),str):
            warnings.append(f"paragraph {i+1} missing handoff rationale")
        if not isinstance(p.get("listener_question"),str):
            warnings.append(f"paragraph {i+1} missing listener question")
        if p.get("verified") is False:
            warnings.append(f"paragraph {i+1} contains unverified content")
    narration="".join(p.get("text","") for p in paragraphs if isinstance(p,dict))
    if storyboard is not None:
        shots=storyboard.get("shots",[])
        if not isinstance(shots,list) or not shots:
            issues.append("storyboard shots missing")
        elif normalize(narration)!=normalize("".join(x.get("narration","") for x in shots)):
            issues.append("Storyboard narration must reproduce the approved script verbatim and in order")
    return {"pass":not issues,"issues":issues,"warnings":warnings,
            "paragraph_count":len(paragraphs),"narration":narration,
            "character_count":len(normalize(narration))}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--script",required=True)
    p.add_argument("--storyboard")
    p.add_argument("--voiceover")
    p.add_argument("--report")
    a=p.parse_args()
    script=json.loads(Path(a.script).read_text(encoding="utf-8"))
    storyboard=json.loads(Path(a.storyboard).read_text(encoding="utf-8")) if a.storyboard else None
    output=audit(script,storyboard)
    if a.voiceover and output["pass"]:
        path=Path(a.voiceover)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(output["narration"]+"\n",encoding="utf-8")
    result={k:v for k,v in output.items() if k!="narration"}
    if a.report:
        path=Path(a.report)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result["pass"] else 1)

if __name__=="__main__":
    main()
