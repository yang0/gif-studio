#!/usr/bin/env python3
"""Compile approved sound-first A/B-roll coverage into the existing GIF EDL.

No fake visual assets, audio timestamps or approvals are generated. Requires
explicit candidate IDs and actual GIF library entries for every shot.
"""
import argparse
import json
from pathlib import Path

from audio_timeline import sha256 as file_sha
from visual_plan import validate as validate_visual, sha256_json
from edit_plan import stable_digest, gif_duration
from candidate_pool import read as read_candidates
from sequence_cut import verify as verify_sequence

def compile_sequence(project,script,audio,timeline,visual,storyboard):
    project=Path(project).resolve()
    errors=validate_visual(visual,timeline,script,audio)
    if errors:
        raise ValueError("Invalid audio/visual plan: "+"; ".join(errors))
    board=storyboard
    if visual["shots"][0]["start_ms"]!=0:
        raise ValueError("Visual plan must begin at 0ms to avoid dropping opening audio")
    if abs(visual["shots"][-1]["end_ms"]-timeline["duration_ms"])>35:
        raise ValueError("Visual plan must end with full audio duration")
    fps=int(board["fps"])
    catalog=read_candidates(project)
    segments={s["id"]:s for s in timeline["segments"]}
    clips=[]
    cursor=0
    for i,scene in enumerate(visual["shots"]):
        if scene["media_type"]!="gpt_gif":
            raise ValueError(f"Visual {scene['id']} uses {scene['media_type']}; requires explicit mixed-media renderer and review; do not substitute fake GIF")
        shot=scene.get("source_shot_id")
        take=scene.get("candidate_id")
        if not shot or not take:
            raise ValueError(f"{scene['id']} requires real source_shot_id and candidate_id")
        record=catalog["candidates"].get(shot+"/"+take)
        if not record:
            raise ValueError(f"{scene['id']}: missing actual GIF candidate {shot}/{take}")
        gif=project/record["file"]
        if not gif.is_file() or file_sha(gif)!=record["sha256"]:
            raise ValueError(f"{scene['id']}: candidate GIF changed or missing")
        start_in_ms=scene.get("source_in_ms",0)
        if type(start_in_ms)!=int or start_in_ms<0:
            raise ValueError(f"{scene['id']}: source_in_ms must be nonnegative integer")
        first=round(scene["start_ms"]*fps/1000)
        last=round(scene["end_ms"]*fps/1000)
        frames=last-first
        in_frames=round(start_in_ms*fps/1000)
        if frames<1 or (in_frames+frames)/fps>gif_duration(gif)+1/fps+.001:
            raise ValueError(f"{scene['id']}: GIF cannot cover narration time; generate additional footage instead of freezing")
        text="".join(segments[s]["text"] for s in scene["audio_segment_ids"])
        clips.append({
            "id":"cut-"+str(i+1).zfill(3),
            "shot_id":shot,"candidate_id":take,
            "source_sha256":record["sha256"],
            "start_frame":cursor,"in_frame":in_frames,
            "duration_frames":frames,
            "narration_anchor":text[:80],
            "cut_reason":scene["cut_reason"],
            "visual_plan_id":scene["id"]})
        cursor+=frames
    result={"version":2,"fps":fps,"width":board["width"],"height":board["height"],
            "storyboard_sha256":stable_digest(board),
            "audio_sha256":file_sha(audio),
            "audio_timeline_sha256":sha256_json(timeline),
            "visual_plan_sha256":sha256_json(visual),
            "clips":clips,"total_frames":cursor,"status":"draft","review_notes":""}
    errors=verify_sequence(project,result,audio)
    if errors:
        raise ValueError("Compiled sequence invalid: "+"; ".join(errors))
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--script",required=True)
    p.add_argument("--audio",required=True)
    p.add_argument("--timeline",required=True)
    p.add_argument("--visual-plan",required=True)
    p.add_argument("--storyboard",required=True)
    p.add_argument("--out")
    a=p.parse_args()
    read=lambda p:json.loads(Path(p).read_text(encoding="utf-8"))
    result=compile_sequence(a.project,read(a.script),a.audio,
            read(a.timeline),read(a.visual_plan),read(a.storyboard))
    destination=Path(a.out) if a.out else Path(a.project)/"sequence.json"
    if destination.exists():
        raise FileExistsError("Existing sequence will not be overwritten; edit a new revision")
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"sequence":str(destination),"clips":len(result["clips"]),
                      "status":"draft"},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
