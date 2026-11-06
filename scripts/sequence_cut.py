#!/usr/bin/env python3
"""Variable-length editorial sequence assembled from REAL GIF candidate footage.

A sequence clip can use any registered candidate, in any order, and can trim
an interval within it. Nothing in this module generates replacement imagery.
Preview output is ALWAYS UNREVIEWED; release still needs separate approvals.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from candidate_pool import read as read_catalog
from edit_plan import gif_duration, probe_audio, stable_digest
from inspect_gif import digest

ID = re.compile(r"^[A-Za-z0-9_-]+$")
DRIFT_LIMIT = 0.35

def verify(project, sequence, audio=None, require_audio=False):
    root = Path(project).resolve()
    faults = []
    if sequence.get("version") != 2:
        faults.append("Sequence schema must be version 2")
    fps = sequence.get("fps")
    width = sequence.get("width")
    height = sequence.get("height")
    if not isinstance(fps, int) or not 1 <= fps <= 60:
        faults.append("fps must be integer 1..60")
    if not isinstance(width, int) or not isinstance(height, int) or width < 2 or height < 2 or width % 2 or height % 2:
        faults.append("Canvas must use positive even width/height")
    if faults:
        return faults
    catalog = read_catalog(root)
    clips = sequence.get("clips", [])
    if not isinstance(clips, list) or not clips:
        return ["Sequence must contain one or more clips"]
    current = 0
    used_ids = set()
    for idx, clip in enumerate(clips):
        if not isinstance(clip, dict):
            faults.append(f"Clip {idx+1}: expected object")
            continue
        cid = clip.get("id")
        sid = clip.get("shot_id")
        take = clip.get("candidate_id")
        if any(not isinstance(x, str) or not ID.fullmatch(x) for x in (cid, sid, take)):
            faults.append(f"Clip {idx+1}: invalid id/shot_id/candidate_id")
            continue
        if cid in used_ids:
            faults.append(f"{cid}: duplicate clip id")
        used_ids.add(cid)
        rec = catalog["candidates"].get(sid+"/"+take)
        if rec is None:
            faults.append(f"{cid}: candidate not found in library")
            continue
        source = root / rec["file"]
        prompt = root / rec["prompt"]
        if not source.is_file() or digest(source) != rec["sha256"]:
            faults.append(f"{cid}: source GIF absent or differs from catalog hash")
            continue
        if not prompt.is_file() or digest(prompt) != rec["prompt_sha256"]:
            faults.append(f"{cid}: candidate prompt absent or modified")
        if clip.get("source_sha256") != rec["sha256"]:
            faults.append(f"{cid}: sequence source hash is stale")
        start = clip.get("start_frame")
        native_in = clip.get("in_frame")
        length = clip.get("duration_frames")
        if any(type(x) is not int for x in (start, native_in, length)):
            faults.append(f"{cid}: frame offsets/durations must be integer")
            continue
        if start != current:
            faults.append(f"{cid}: gap, overlap, or incorrect start_frame (expected {current})")
        if native_in < 0 or length < 1:
            faults.append(f"{cid}: invalid source in-point or duration")
        else:
            native = gif_duration(source)
            if (native_in + length) / fps > native + 1 / fps + 0.001:
                faults.append(f"{cid}: requested footage exceeds real GIF duration ({native:.3f}s); no freeze filler permitted")
        if not clip.get("cut_reason") or clip.get("cut_reason") == "REVIEW_REQUIRED":
            faults.append(f"{cid}: editorial cut_reason missing")
        if not clip.get("narration_anchor"):
            faults.append(f"{cid}: narration anchor missing")
        current += max(length, 0)
    if sequence.get("total_frames") != current:
        faults.append(f"Sequence total_frames is stale: expected {current}")
    if sequence.get("status") == "approved":
        # Editing approval is not visual release approval; only a declared intent.
        if len(str(sequence.get("review_notes", "")).strip()) < 16:
            faults.append("Approved sequence needs substantive review_notes")
    if audio:
        actual = probe_audio(audio)
        if abs(actual - current / fps) > DRIFT_LIMIT:
            faults.append(f"Voiceover duration {actual:.2f}s differs from sequence {current/fps:.2f}s")
    elif require_audio:
        faults.append("Narrated deliverable requires real audio")
    return faults

def initialize(project, storyboard):
    root = Path(project).resolve()
    board = json.loads(Path(storyboard).read_text(encoding="utf-8"))
    catalog = read_catalog(root)
    fps = int(board["fps"])
    cursor = 0
    clips = []
    for shot in board["shots"]:
        sid = shot["id"]
        selected = catalog["selections"].get(sid)
        if not selected:
            raise ValueError(f"{sid}: select one initial candidate in candidate_pool first")
        take = selected["candidate_id"]
        rec = catalog["candidates"][sid+"/"+take]
        if digest(root/rec["file"]) != rec["sha256"]:
            raise ValueError(f"{sid}: candidate modified")
        limit = int(gif_duration(root/rec["file"]) * fps + 0.00001)
        frames = min(round(float(shot["duration_sec"]) * fps), limit)
        if frames < 1:
            raise ValueError(f"{sid}: selected candidate too short")
        clips.append({
            "id":f"cut-{len(clips)+1:03d}",
            "shot_id":sid, "candidate_id":take,
            "source_sha256":rec["sha256"],
            "start_frame":cursor,"in_frame":0,"duration_frames":frames,
            "narration_anchor":shot.get("narration", "")[:80],
            "cut_reason":"REVIEW_REQUIRED"})
        cursor += frames
    return {
        "version":2, "fps":fps, "width":int(board["width"]),
        "height":int(board["height"]),
        "storyboard_sha256":stable_digest(board),
        "clips":clips, "total_frames":cursor, "status":"draft",
        "review_notes":"",
    }

def render(project, sequence, output, audio=None):
    root = Path(project).resolve()
    faults = verify(root, sequence, audio)
    # For an editorial preview, duration mismatch is returned as a warning,
    # and the preview is rendered without audio to avoid silently truncating speech.
    audio_mismatch = any(f.startswith("Voiceover duration") for f in faults)
    hard_faults = [f for f in faults if not f.startswith("Voiceover duration")]
    if hard_faults:
        raise ValueError("Invalid sequence: " + "; ".join(hard_faults))
    fps=sequence["fps"]
    target=Path(output).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    work=root/"build"/"sequence"/"clips"
    work.mkdir(parents=True,exist_ok=True)
    cat=read_catalog(root)
    clip_paths=[]
    for clip in sequence["clips"]:
        rec=cat["candidates"][clip["shot_id"]+"/"+clip["candidate_id"]]
        source=root/rec["file"]
        out=work/(clip["id"]+".mp4")
        start=clip["in_frame"]
        count=clip["duration_frames"]
        vf=(f"fps={fps},trim=start_frame={start}:end_frame={start+count},"
            f"setpts=PTS-STARTPTS,scale={sequence['width']}:{sequence['height']}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={sequence['width']}:{sequence['height']}:(ow-iw)/2:(oh-ih)/2:black,"
            "setsar=1,format=yuv420p")
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
             "-ignore_loop","1","-i",str(source),"-vf",vf,
             "-frames:v",str(count),"-r",str(fps),"-an",
             "-c:v","libx264","-pix_fmt","yuv420p",str(out)],check=True)
        clip_paths.append(out)
    concat=root/"build"/"sequence"/"concat.txt"
    def safe_quote(p):
        return str(p.resolve()).replace("'", "'\\''")
    concat.write_text("".join("file '"+safe_quote(p)+"'\n" for p in clip_paths),encoding="utf-8")
    silent=root/"build"/"sequence"/"preview-noaudio.mp4"
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
        "-f","concat","-safe","0","-i",str(concat),"-an","-c:v","libx264",
        "-pix_fmt","yuv420p","-movflags","+faststart",str(silent)],check=True)
    if audio and not audio_mismatch:
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
            "-i",str(silent),"-i",str(Path(audio).resolve()),
            "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac",
            "-t",str(sequence["total_frames"]/fps),"-movflags","+faststart",str(target)],check=True)
    else:
        import shutil
        shutil.copyfile(silent,target)
    result={
        "status":"UNREVIEWED_SEQUENCE_PREVIEW",
        "video":str(target),
        "source":"candidate GIF files only; no synthetic replacement",
        "clips":len(sequence["clips"]),
        "duration_sec":sequence["total_frames"]/fps,
        "audio_included":bool(audio and not audio_mismatch),
        "warnings":faults,
        "sequence_sha256":stable_digest(sequence),
        "formal_approval":False,
    }
    report=root/"build"/"sequence"/"report.json"
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--storyboard")
    p.add_argument("--sequence")
    p.add_argument("--audio")
    p.add_argument("--out")
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--init",action="store_true")
    mode.add_argument("--verify",action="store_true")
    mode.add_argument("--preview",action="store_true")
    a=p.parse_args()
    root=Path(a.project).resolve()
    dest=Path(a.sequence) if a.sequence else root/"sequence.json"
    if a.init:
        if not a.storyboard:
            raise ValueError("--init requires --storyboard")
        plan=initialize(root,a.storyboard)
        if dest.exists():
            raise FileExistsError("Sequence exists; edit it instead of overwriting")
        dest.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        result={"sequence":str(dest),"status":"draft","clips":len(plan["clips"])}
    else:
        plan=json.loads(dest.read_text(encoding="utf-8"))
        if a.verify:
            issues=verify(root,plan,a.audio)
            result={"pass":not issues,"issues":issues}
        else:
            output=Path(a.out) if a.out else root/"build"/"sequence-preview.mp4"
            result=render(root,plan,output,a.audio)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if a.verify and not result["pass"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()
