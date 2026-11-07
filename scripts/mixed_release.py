#!/usr/bin/env python3
"""Formal gate for mixed-media narrated videos.

A completed preview is *not* approved. Every real shot needs a distinct,
hash-bound director review; the full MP4 needs a separate final listen/watch.
"""
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from audio_timeline import sha256
from visual_plan import sha256_json
from video_cut import validate_compiled, video_has_stream, video_duration
from audio_subtitles import build as build_srt
from release_sequence import subtitle_issues
from final_review import probe as probe_movie

CHECKS=("semantic","continuity","readability","source_legitimacy")

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def record_path(root,shot_id):
    return Path(root)/"qa"/"mixed-shots"/(shot_id+".json")

def source_review(project,clip,plan,reviewer,notes,checks):
    root=Path(project).resolve()
    if not reviewer.strip() or len(notes.strip())<24:
        raise ValueError("Real reviewer and substantial visual notes required")
    if any(checks.get(c) is not True for c in CHECKS):
        raise ValueError("All four shot reviews must explicitly pass")
    if any(clip.get(x) is None for x in ("visual_plan_id","source_sha256","cut_reason")):
        raise ValueError("Shot missing source/edit fields")
    record={"version":1,"shot_id":clip["visual_plan_id"],
            "media_type":clip["media_type"],
            "source_sha256":clip["source_sha256"],
            "visual_plan_sha256":plan["visual_plan_sha256"],
            "camera_preset":clip.get("camera_preset","native"),
            "reviewer":reviewer.strip(),"notes":notes.strip(),
            "checks":{c:True for c in CHECKS},
            "reviewed_at":datetime.now(timezone.utc).isoformat()}
    path=record_path(root,clip["visual_plan_id"])
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_file():
        raise FileExistsError("Existing shot approval cannot be overwritten")
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return record

def gate(project,plan,script,timeline,visual,audio,storyboard,subtitles,preview):
    root=Path(project).resolve()
    validate_compiled(root,plan,audio,script,timeline,visual,storyboard,True)
    if not Path(preview).is_file():
        raise ValueError("Actual mixed-media preview missing")
    report_path=root/"build"/"video-preview"/"preview-report.json"
    if not report_path.is_file():
        raise ValueError("Preview technical report missing")
    report=load(report_path)
    if (report.get("output")!=str(Path(preview).resolve()) or
        report.get("video_sha256")!=sha256(preview) or
        report.get("status")!="UNREVIEWED_MIXED_PREVIEW" or
        report.get("audio_sha256")!=sha256(audio) or
        report.get("visual_plan_sha256")!=plan["visual_plan_sha256"] or
        not report.get("subtitles_burned")):
        raise ValueError("Mixed preview does not match current audio, edit or subtitle render")
    duration,tracks=probe_movie(preview)
    if "video" not in tracks or "audio" not in tracks:
        raise ValueError("Formal video must have real video and audio tracks")
    if abs(duration-plan["total_frames"]/plan["fps"])>.2:
        raise ValueError("Rendered movie duration drift")
    srt=Path(subtitles)
    if not srt.is_file() or srt.read_text(encoding="utf-8")!=build_srt(timeline,script,audio):
        raise ValueError("Aligned subtitle source differs from narration")
    proof=Path(str(srt)+".provenance.json")
    if not proof.is_file():
        raise ValueError("Aligned subtitle provenance missing")
    metadata=load(proof)
    if (metadata.get("audio_sha256")!=sha256(audio) or
        metadata.get("audio_timeline_sha256")!=sha256_json(timeline) or
        metadata.get("srt_sha256")!=sha256(srt)):
        raise ValueError("Subtitle provenance stale")
    issues=subtitle_issues(srt,plan["total_frames"]/plan["fps"])
    if issues:
        raise ValueError("Subtitles invalid: "+"; ".join(issues))
    evidence=[]
    for clip in plan["clips"]:
        path=record_path(root,clip["visual_plan_id"])
        if not path.is_file():
            raise ValueError("Unreviewed mixed shot "+clip["visual_plan_id"])
        rec=load(path)
        if (rec.get("source_sha256")!=clip["source_sha256"] or
            rec.get("visual_plan_sha256")!=plan["visual_plan_sha256"] or
            rec.get("media_type")!=clip["media_type"] or
            rec.get("camera_preset")!=clip.get("camera_preset","native") or
            any(rec.get("checks",{}).get(c) is not True for c in CHECKS) or
            not rec.get("reviewer") or len(rec.get("notes",""))<24):
            raise ValueError("Mixed shot approval stale/incomplete: "+clip["visual_plan_id"])
        evidence.append({"shot_id":clip["visual_plan_id"],
                         "review_sha256":sha256(path),
                         "source_sha256":clip["source_sha256"]})
    return evidence

def release(project,plan,script,timeline,visual,audio,storyboard,subtitles,preview,out=None):
    evidence=gate(project,plan,script,timeline,visual,audio,storyboard,subtitles,preview)
    root=Path(project).resolve()
    destination=Path(out).resolve() if out else root/"build"/"formal-mixed"/"final.mp4"
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        raise FileExistsError("Formal mixed video exists; save a new version")
    if destination==Path(preview).resolve():
        raise ValueError("Formal delivery file must differ from its unreviewed preview")
    shutil.copyfile(preview,destination)
    source_files={
        "video":destination,
        "preview":Path(preview).resolve(),
        "audio":Path(audio).resolve(),
        "subtitles":Path(subtitles).resolve(),
        "script":root/"script.json",
        "timeline":root/"audio-timeline.json",
        "visual_plan":root/"visual-plan.json",
        "storyboard":root/"storyboard.json",
        "video_plan":root/"video-plan.json"
    }
    if any(not x.is_file() for x in source_files.values()):
        raise ValueError("All exact source files must exist in project")
    output={"status":"PENDING_FINAL_VIDEO_REVIEW","kind":"mixed_media",
            "sources":{key:{"path":str(path),"sha256":sha256(path)}
                       for key,path in source_files.items()},
            "shots":evidence,
            "required_review":"Watch entire video, listen to narration and approve with final_review.py"}
    dest=root/"build"/"mixed-release"/"release-provenance.json"
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():
        raise FileExistsError("Formal release exists; archive old revision")
    dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return output

def verify_release(project,video):
    root=Path(project).resolve()
    src=root/"build"/"mixed-release"/"release-provenance.json"
    if not src.is_file():
        raise ValueError("Missing formal mixed-release manifest")
    record=load(src)
    if record.get("kind")!="mixed_media" or record.get("status")!="PENDING_FINAL_VIDEO_REVIEW":
        raise ValueError("Not an awaiting mixed-media release")
    source_files=record.get("sources",{})
    for name,entry in source_files.items():
        path=Path(entry["path"])
        if not path.is_file() or sha256(path)!=entry["sha256"]:
            raise ValueError("Mixed release source changed: "+name)
    if Path(source_files["video"]["path"]).resolve()!=Path(video).resolve():
        raise ValueError("Reviewed video differs from mixed release")
    # A signed EDL is insufficient if the actual recording, screenshots or
    # motion graphic files have changed since preview was rendered.
    validate_compiled(root,load(source_files["video_plan"]["path"]),
                      Path(source_files["audio"]["path"]),
                      load(source_files["script"]["path"]),
                      load(source_files["timeline"]["path"]),
                      load(source_files["visual_plan"]["path"]),
                      load(source_files["storyboard"]["path"]),True)
    for row in record.get("shots",[]):
        path=record_path(root,row["shot_id"])
        if not path.is_file() or sha256(path)!=row["review_sha256"]:
            raise ValueError("Mixed shot review changed: "+row["shot_id"])
    return record

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--approve-shot",action="store_true")
    mode.add_argument("--release",action="store_true")
    mode.add_argument("--verify",action="store_true")
    p.add_argument("--shot");p.add_argument("--reviewer");p.add_argument("--notes")
    p.add_argument("--preview")
    p.add_argument("--out",help="Formal MP4 destination; default project/build/formal-mixed/final.mp4")
    for key in CHECKS:
        p.add_argument("--"+key+"-pass",action="store_true")
    a=p.parse_args()
    root=Path(a.project)
    if a.verify:
        result=verify_release(root,a.out or root/"build"/"formal-mixed"/"final.mp4")
    else:
        plan=load(root/"video-plan.json")
        if a.approve_shot:
            clip=next((x for x in plan["clips"] if x["visual_plan_id"]==a.shot),None)
            if clip is None:
                raise ValueError("Shot ID missing from mixed video plan")
            result=source_review(root,clip,plan,a.reviewer or "",a.notes or "",
                                 {k:getattr(a,k+"_pass") for k in CHECKS})
        else:
            result=release(root,plan,load(root/"script.json"),
                           load(root/"audio-timeline.json"),load(root/"visual-plan.json"),
                           root/"audio"/"voiceover.wav",load(root/"storyboard.json"),
                           root/"subtitles"/"captions.srt",
                           a.preview or root/"build"/"mixed-preview.mp4",a.out)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
