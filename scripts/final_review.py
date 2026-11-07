#!/usr/bin/env python3
"""Post-render approval: inspect actual MP4 and bind review to SHA256.

Technical preview contact sheet is automatic. The 'approve' step is an
operator statement, NOT machine proof of subjective quality.
"""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def probe(path):
    obj=json.loads(subprocess.check_output(
        ["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],
        text=True))
    duration=float(obj["format"]["duration"])
    tracks={s["codec_type"] for s in obj["streams"]}
    return duration,tracks

def sheet(project,video,frames=8):
    duration,tracks=probe(video)
    if duration<=0:
        raise ValueError("Invalid video duration")
    frames=max(3,min(16,frames))
    outdir=Path(project)/"qa"/"final"
    outdir.mkdir(parents=True,exist_ok=True)
    thumbs=[]
    for n in range(frames):
        at=duration*(n+0.5)/frames
        still=outdir/(f"f{n:02d}.jpg")
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                        "-ss",str(at),"-i",str(video),"-frames:v","1",str(still)],
                       check=True)
        with Image.open(still) as im:
            thumbs.append(ImageOps.contain(im.convert("RGB"),(240,360)))
    canvas=Image.new("RGB",(4*256,((len(thumbs)+3)//4)*390),"white")
    draw=ImageDraw.Draw(canvas)
    for i,im in enumerate(thumbs):
        x=(i%4)*256
        y=(i//4)*390
        canvas.paste(im,(x+(240-im.width)//2,y))
        draw.text((x+8,y+365),f"{duration*(i+0.5)/frames:.1f}s",fill="black")
    dest=outdir/"contact-sheet.jpg"
    canvas.save(dest,quality=90)
    status={"video":str(Path(video).resolve()),"sha256":sha256(video),
            "duration_sec":duration,"audio_track_present":"audio" in tracks,
            "contact_sheet":str(dest.resolve()),
            "contact_sheet_sha256":sha256(dest),
            "status":"awaiting_actual_full_video_review"}
    (outdir/"inspection.json").write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return status

def approve(project, video, reviewer, notes, checks):
    root=Path(project)
    report=root/"qa"/"final"/"inspection.json"
    if not report.is_file():
        raise ValueError("Run final_review.py --inspect first")
    info=json.loads(report.read_text(encoding="utf-8"))
    if sha256(video)!=info.get("sha256"):
        raise ValueError("Rendered MP4 changed since preview")
    if not Path(info["contact_sheet"]).is_file() or sha256(info["contact_sheet"])!=info["contact_sheet_sha256"]:
        raise ValueError("Contact sheet changed after review")
    if not all(checks.values()):
        raise ValueError("Full-video review must explicitly pass every category")
    if not reviewer.strip() or len(notes.strip())<16:
        raise ValueError("Identify actual reviewer and provide substantive observations")
    if not info["audio_track_present"]:
        raise ValueError("No audio track; this is only a silent preview, not a finished narrated video")
    formal=root/"build"/"formal-sequence"/"release-provenance.json"
    if (root/"sequence.json").is_file() and not formal.is_file():
        raise ValueError("Variable sequence final approval requires formal release provenance")
    if formal.is_file():
        provenance=json.loads(formal.read_text(encoding="utf-8"))
        if (provenance.get("status")!="PENDING_FINAL_VIDEO_REVIEW" or
            provenance.get("video_sha256")!=info["sha256"] or
            Path(provenance.get("video","")).resolve()!=Path(video).resolve()):
            raise ValueError("Formal release provenance differs from reviewed video")
        from candidate_review import paths as candidate_review_paths
        from edit_plan import stable_digest
        for source_field,hash_field in (
            ("storyboard_source","storyboard_sha256"),
            ("audio_source","audio_sha256"),
            ("subtitles_source","subtitles_sha256"),
        ):
            source_file=provenance.get(source_field)
            if not source_file or not Path(source_file).is_file() or sha256(source_file)!=provenance.get(hash_field):
                raise ValueError(source_field+" changed or missing since formal render")
        sequence_file=provenance.get("sequence_source")
        if not sequence_file or not Path(sequence_file).is_file():
            raise ValueError("Formal sequence source missing since render")
        if stable_digest(json.loads(Path(sequence_file).read_text(encoding="utf-8")))!=provenance.get("sequence_sha256"):
            raise ValueError("Formal sequence changed since render")
        for source in provenance.get("sources",[]):
            approved=candidate_review_paths(root,source["shot"],source["candidate"])[1]
            if not approved.is_file() or sha256(approved)!=source["candidate_approval_sha256"]:
                raise ValueError("Selected candidate review changed after render")
        seq=root/"sequence.json"
        if seq.is_file() and stable_digest(json.loads(seq.read_text(encoding="utf-8")))!=provenance.get("sequence_sha256"):
            raise ValueError("Approved sequence changed since formal render")
    record={"status":"release_approved","video":info["video"],
            "sha256":info["sha256"],"reviewer":reviewer,
            "review_notes":notes,"checks":checks,
            "reviewed_at":datetime.now(timezone.utc).isoformat()}
    dest=root/"qa"/"final"/"approval.json"
    dest.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return record

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--video",required=True)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--inspect",action="store_true")
    g.add_argument("--approve",action="store_true")
    p.add_argument("--reviewer")
    p.add_argument("--notes")
    for key in ("semantic","pacing","continuity","subtitles","audio"):
        p.add_argument("--"+key+"-pass",action="store_true")
    args=p.parse_args()
    if args.inspect:
        record=sheet(args.project,args.video)
    else:
        checks={key:getattr(args,key+"_pass") for key in
                ("semantic","pacing","continuity","subtitles","audio")}
        record=approve(args.project,args.video,args.reviewer or "",args.notes or "",checks)
    print(json.dumps(record,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
