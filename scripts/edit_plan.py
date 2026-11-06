#!/usr/bin/env python3
"""Frame-accurate editorial decision list for GPT GIF footage.

No generated vectors or fake media. Uses actual GIF durations and optional
real narration audio. A plan is a *draft* until visually reviewed.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageSequence

MAX_FREEZE_RATIO=0.25
MAX_AUDIO_DRIFT=0.35

def stable_digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
        separators=(",",":")).encode("utf-8")).hexdigest()

def probe_audio(path):
    path=Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    raw=subprocess.check_output(
        ["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],
        text=True)
    data=json.loads(raw)
    streams=[s for s in data.get("streams",[]) if s.get("codec_type")=="audio"]
    if not streams:
        raise ValueError("Narration file has no audio stream")
    duration=float(data.get("format",{}).get("duration",0))
    if duration<=0:
        raise ValueError("Cannot determine narration duration")
    return duration

def gif_duration(path):
    with Image.open(path) as im:
        if im.format!="GIF":
            raise ValueError(f"{path} is not a GIF")
        return sum(int(f.info.get("duration", im.info.get("duration",100)))
                   for f in ImageSequence.Iterator(im))/1000

def create_plan(project, board, audio=None, max_freeze_ratio=MAX_FREEZE_RATIO):
    project=Path(project)
    fps=int(board["fps"])
    frame=0
    entries=[]
    for shot in board["shots"]:
        length=float(shot["duration_sec"])
        frames=round(length*fps)
        if frames<1:
            raise ValueError("Shot shorter than one frame")
        real=frames/fps
        gif=project/"gifs"/(shot["id"]+".gif")
        if not gif.is_file():
            raise FileNotFoundError(gif)
        native=gif_duration(gif)
        freeze=max(0,real-native)
        entries.append({
            "shot_id":shot["id"],
            "start_frame":frame,
            "duration_frames":frames,
            "narration_anchor":str(shot.get("narration",""))[:28],
            "cut_reason":"REVIEW_REQUIRED",
            "gif_native_sec":round(native,3),
            "freeze_sec":round(freeze,3),
            "freeze_ratio":round(freeze/real,4),
            "source":f"gifs/{shot['id']}.gif",
        })
        frame+=frames
    return {
        "version":1,
        "fps":fps,
        "storyboard_sha256":stable_digest(board),
        "audio_file":str(Path(audio).resolve()) if audio else None,
        "audio_duration_sec":round(probe_audio(audio),3) if audio else None,
        "max_freeze_ratio":float(max_freeze_ratio),
        "total_frames":frame,
        "duration_sec":round(frame/fps,3),
        "shots":entries,
        "review_status":"draft",
        "review_notes":"",
    }

def validate_plan(project, board, plan, audio=None, require_review=True, require_audio=True):
    issues=[]
    if plan.get("version")!=1 or plan.get("fps")!=board.get("fps"):
        issues.append("Edit plan version/fps mismatch")
    if plan.get("storyboard_sha256")!=stable_digest(board):
        issues.append("Storyboard changed after edit plan")
    shots=plan.get("shots",[])
    if len(shots)!=len(board["shots"]):
        issues.append("Edit plan shot count mismatch")
    expected_start=0
    fps=int(board["fps"])
    for i,(shot,source) in enumerate(zip(shots,board["shots"])):
        sid=source["id"]
        if shot.get("shot_id")!=sid:
            issues.append(f"{sid}: editorial order mismatch")
        frames=round(source["duration_sec"]*fps)
        if shot.get("duration_frames")!=frames or shot.get("start_frame")!=expected_start:
            issues.append(f"{sid}: gaps, overlaps or stale timing")
        expected_start+=frames
        path=Path(project)/"gifs"/(sid+".gif")
        if not path.is_file():
            issues.append(f"{sid}: GIF missing")
            continue
        native=gif_duration(path)
        freeze=max(0,frames/fps-native)
        ratio=freeze/(frames/fps)
        if ratio>float(plan.get("max_freeze_ratio",MAX_FREEZE_RATIO))+1e-6:
            issues.append(f"{sid}: {ratio:.1%} frozen end-frame exceeds editorial threshold")
        if abs(float(shot.get("gif_native_sec",-1))-native)>.005:
            issues.append(f"{sid}: GIF duration changed after edit plan")
        if require_review and (not shot.get("cut_reason") or
                               shot.get("cut_reason")=="REVIEW_REQUIRED"):
            issues.append(f"{sid}: cut has not been directed and explained")
        if require_review and not shot.get("narration_anchor"):
            issues.append(f"{sid}: missing narration anchor")
    if plan.get("total_frames")!=expected_start:
        issues.append("Total frame count mismatch")
    if require_review and plan.get("review_status")!="approved":
        issues.append("Edit plan has not been reviewed and approved")
    if audio:
        actual=probe_audio(audio)
        if abs(actual-expected_start/fps)>MAX_AUDIO_DRIFT:
            issues.append(f"Voiceover duration {actual:.2f}s differs from edit {expected_start/fps:.2f}s")
        if not plan.get("audio_file") or Path(plan["audio_file"]).resolve()!=Path(audio).resolve():
            issues.append("Edit plan bound to different narration audio file")
    elif require_review and require_audio:
        issues.append("Narrated final video requires actual voiceover audio")
    return issues

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--storyboard",required=True)
    p.add_argument("--audio")
    p.add_argument("--out")
    p.add_argument("--verify",action="store_true")
    p.add_argument("--preview",action="store_true",
                   help="Check technical timeline only; not a formal approval")
    a=p.parse_args()
    project=Path(a.project)
    board=json.loads(Path(a.storyboard).read_text(encoding="utf-8"))
    path=Path(a.out) if a.out else project/"edit-plan.json"
    if a.verify:
        plan=json.loads(path.read_text(encoding="utf-8"))
        issues=validate_plan(project,board,plan,a.audio,require_review=not a.preview)
        print(json.dumps({"pass":not issues,"issues":issues},ensure_ascii=False,indent=2))
        raise SystemExit(1 if issues else 0)
    plan=create_plan(project,board,a.audio)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"file":str(path),"review_status":"draft","shots":len(plan["shots"])},
                     ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
