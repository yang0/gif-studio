#!/usr/bin/env python3
"""Compile shot-specific GPT GIF prompts. Generates text, not images."""
import argparse
import json
from pathlib import Path
from director_plan import validate_director
from validate_storyboard import validate

def build_prompt(shot, director, style, attempt=1, issue=None):
    if director["asset_policy"] != "new_gpt_gif":
        raise ValueError("Only new GPT GIF shots can be compiled")
    must = director.get("must_show", [])
    avoid = director.get("must_not_show", [])
    if not isinstance(must,list) or len(must)<2 or any(not isinstance(v,str) or not v.strip() for v in must):
        raise ValueError("At least two explicit must_show elements or actions required")
    if not isinstance(avoid,list) or any(not isinstance(v,str) for v in avoid):
        raise ValueError("must_not_show must be strings")
    if attempt not in (1,2) or (attempt==2 and not issue):
        raise ValueError("At most one focused retry, requiring concrete failure observation")
    required="\n".join(f"{i}. {v}" for i,v in enumerate(must,1))
    forbidden="\n".join(f"{i}. {v}" for i,v in enumerate(avoid,1))
    prompt=f"""Create ONE animated GIF showing a specific event from an educational video.
CRITICAL VISUAL PROOF: {director["visual_proof"]}
Do not replace this scene with generic objects or topical symbols.

SHOT: {shot["id"]}
NARRATION: {shot["narration"]}
KNOWLEDGE GOAL: {shot["visual_goal"]}
SOURCE ANCHOR: {director["source_anchor"]}

THE FOLLOWING MUST BE CLEARLY VISIBLE:
{required}

THE FOLLOWING MUST NOT APPEAR:
{forbidden if forbidden else "No unrelated concepts, symbols, or objects."}

COMPLETE VISUAL EVENT:
Opening: {director["start_state"]}
Specific change: {director["change_event"]}
Final visible state: {director["end_state"]}
Composition and subject scale: {director["composition"]}
Prior-shot connection: {director["entry_transition"]}
Next-shot handoff: {director["exit_transition"]}

STYLE LOCK:
{json.dumps(style, ensure_ascii=False, indent=2)}

Duration target: {shot["duration_sec"]} seconds, only if supported by the current tool.
Use a readable opening, a clear visible event, and a final hold. Each object retains its identity.
Never replace the selected style with a default paper collage, random brain/lightbulb,
generic AI graphics, slide template, vector card montage, or stock symbolic imagery.
No narration text, watermark, fabricated numerical details, logo, or fake UI.
OUTPUT: an actual animated GIF, not an image description or alternative video source.
"""
    if attempt==2:
        prompt+="\nPRIOR ATTEMPT FAILED; CORRECT THIS EXACT PROBLEM:\n"+str(issue).strip()
        prompt+="\nAvoid the previous failed composition. Preserve the mandatory elements.\n"
    return prompt

def compile_project(project, storyboard):
    project=Path(project)
    board=json.loads(Path(storyboard).read_text(encoding="utf-8"))
    errors=validate(board)
    if errors:
        raise ValueError("; ".join(errors))
    director=json.loads((project/"director-plan.json").read_text(encoding="utf-8"))
    style=json.loads((project/"style-lock.json").read_text(encoding="utf-8"))
    errors,_=validate_director(director,board)
    if errors:
        raise ValueError("; ".join(errors))
    if not isinstance(style,dict) or not style.get("style_id"):
        raise ValueError("style-lock.json needs style_id")
    output=project/"prompts"
    output.mkdir(parents=True,exist_ok=True)
    paths={}
    for shot,decision in zip(board["shots"],director["shots"]):
        if decision["asset_policy"]!="new_gpt_gif":
            continue
        path=output/(shot["id"]+".txt")
        path.write_text(build_prompt(shot,decision,style),encoding="utf-8")
        paths[shot["id"]]=str(path)
    return paths

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--storyboard",required=True)
    a=p.parse_args()
    print(json.dumps(compile_project(a.project,a.storyboard),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
