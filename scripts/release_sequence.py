#!/usr/bin/env python3
"""Formal multi-cut release *candidate* from reviewed GPT GIF library assets.

A successful render is PENDING_FINAL_VIDEO_REVIEW, never automatically approved.
The separate final_review.py step requires someone to actually watch/listen.
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

from candidate_pool import read as read_catalog
from candidate_review import status as candidate_status, paths as candidate_review_paths
from edit_plan import stable_digest
from inspect_gif import digest
from sequence_cut import verify as verify_sequence, render as render_sequence

def probe_video(path):
    raw=subprocess.check_output(["ffprobe","-v","error","-show_streams",
                                 "-show_format","-of","json",str(path)],text=True)
    data=json.loads(raw)
    return data

def subtitle_issues(path,total_seconds):
    p=Path(path)
    if not p.is_file():
        return ["Subtitle SRT missing"]
    content=p.read_text(encoding="utf-8-sig")
    pattern=re.compile(r"(?m)(\d\d):(\d\d):(\d\d),(\d\d\d)\s*-->\s*(\d\d):(\d\d):(\d\d),(\d\d\d)")
    matches=list(pattern.finditer(content))
    if not matches:
        return ["Subtitle SRT has no valid timed cues"]
    issues=[]
    last_end=0.
    for m in matches:
        a=list(map(int,m.groups()))
        start=a[0]*3600+a[1]*60+a[2]+a[3]/1000
        end=a[4]*3600+a[5]*60+a[6]+a[7]/1000
        if end<=start or start<last_end-.001:
            issues.append("Subtitle cues overlap, regress or have nonpositive time")
        if end>total_seconds+.15:
            issues.append("Subtitle cue exceeds video duration")
        last_end=end
    return issues

def v3_subtitle_provenance_issues(project, sequence, audio, subtitles):
    """V3 release must use subtitles bound to the SAME aligned voice track."""
    if not sequence.get("audio_timeline_sha256"):
        return []  # Legacy v2 projects use their existing subtitle contract.
    root=Path(project).resolve()
    timeline=root/"audio-timeline.json"
    script=root/"script.json"
    proof=Path(str(subtitles)+".provenance.json")
    missing=[str(p) for p in (timeline,script,proof) if not p.is_file()]
    if missing:
        return ["V3 aligned subtitle provenance missing: "+", ".join(missing)]
    try:
        from visual_plan import sha256_json
        aligned=json.loads(timeline.read_text(encoding="utf-8"))
        record=json.loads(proof.read_text(encoding="utf-8"))
        expected={
            "audio_timeline_sha256":sha256_json(aligned),
            "audio_sha256":digest(audio),
            "script_sha256":digest(script),
            "srt_sha256":digest(subtitles),
        }
        errors=[]
        for key,actual in expected.items():
            if record.get(key)!=actual:
                errors.append("V3 subtitle provenance mismatch: "+key)
        if sequence.get("audio_timeline_sha256")!=expected["audio_timeline_sha256"]:
            errors.append("V3 sequence aligned against a different audio timeline")
        return errors
    except (ValueError,OSError,KeyError,TypeError) as exc:
        return ["Invalid V3 subtitle provenance: "+str(exc)]

def preflight(project, storyboard, sequence, audio, subtitles):
    root=Path(project).resolve()
    issues=verify_sequence(root,sequence,audio,require_audio=True,storyboard=storyboard)
    if sequence.get("status")!="approved":
        issues.append("Sequence must be director-reviewed and approved")
    if len(str(sequence.get("review_notes","")).strip())<24:
        issues.append("Sequence approval requires substantive full-edit review notes")
    if not audio or not Path(audio).is_file():
        issues.append("Real narration audio file is mandatory")
    issues.extend(subtitle_issues(subtitles,sequence["total_frames"]/sequence["fps"]))
    if audio and Path(audio).is_file() and subtitles and Path(subtitles).is_file():
        issues.extend(v3_subtitle_provenance_issues(root,sequence,audio,subtitles))
    catalog=read_catalog(root)
    used=set()
    for clip in sequence["clips"]:
        key=(clip["shot_id"],clip["candidate_id"])
        if key in used:
            continue
        used.add(key)
        state,reason=candidate_status(root,storyboard,*key)
        if state!="ready":
            issues.append(f"{key[0]}/{key[1]}: {state}: {reason}")
    return issues

def release(project,storyboard,sequence_file,audio,subtitles,out):
    root=Path(project).resolve()
    sequence_path=Path(sequence_file).resolve()
    seq=json.loads(sequence_path.read_text(encoding="utf-8"))
    faults=preflight(root,storyboard,seq,audio,subtitles)
    if faults:
        raise ValueError("Formal sequence release blocked: "+"; ".join(faults))
    build=root/"build"/"formal-sequence"
    build.mkdir(parents=True,exist_ok=True)
    # Re-use exactly the same GIF selection and render logic as preview.
    intermediate=build/"reviewed-footage-with-audio.mp4"
    draft=render_sequence(root,seq,intermediate,audio)
    if draft["warnings"] or not draft["audio_included"]:
        raise ValueError("Source timeline did not synchronize with real narration")
    target=Path(out).resolve()
    target.parent.mkdir(parents=True,exist_ok=True)
    # The subtitles are a deterministic overlay on the real GIF footage.
    arg="subtitles="+str(Path(subtitles).resolve()).replace("\\","\\\\").replace(":","\\:").replace("'","\\'")
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                    "-i",str(intermediate),"-vf",arg,"-map","0:v:0",
                    "-map","0:a:0","-c:v","libx264","-crf","18","-preset","medium",
                    "-pix_fmt","yuv420p","-c:a","copy","-movflags","+faststart",
                    str(target)],check=True)
    media=probe_video(target)
    kinds=[s.get("codec_type") for s in media.get("streams",[])]
    videos=[s for s in media.get("streams",[]) if s.get("codec_type")=="video"]
    if not videos or "audio" not in kinds:
        raise ValueError("Rendered output lost a required video or audio track")
    video=videos[0]
    if int(video.get("width",0))!=seq["width"] or int(video.get("height",0))!=seq["height"]:
        raise ValueError("Rendered dimensions do not match approved sequence")
    duration=float(media.get("format",{}).get("duration",0))
    if abs(duration-seq["total_frames"]/seq["fps"])>.20:
        raise ValueError("Final video duration inconsistent with approved sequence")
    from final_review import sha256
    catalog=read_catalog(root)
    used=set((c["shot_id"],c["candidate_id"]) for c in seq["clips"])
    artifacts=[]
    for sid,take in sorted(used):
        rec=catalog["candidates"][sid+"/"+take]
        _,review_path=candidate_review_paths(root,sid,take)
        artifacts.append({
            "shot":sid,"candidate":take,
            "gif_sha256":rec["sha256"],
            "prompt_sha256":rec["prompt_sha256"],
            "candidate_approval_sha256":digest(review_path)})
    output={"status":"PENDING_FINAL_VIDEO_REVIEW",
            "video":str(target),
            "video_sha256":sha256(target),
            "sequence_sha256":stable_digest(seq),
            "sequence_source":str(sequence_path),
            "storyboard_sha256":digest(storyboard),
            "storyboard_source":str(Path(storyboard).resolve()),
            "audio_sha256":digest(audio),
            "audio_source":str(Path(audio).resolve()),
            "subtitles_sha256":digest(subtitles),
            "subtitles_source":str(Path(subtitles).resolve()),
            "sources":artifacts,
            "duration_sec":duration,
            "has_audio":True,
            "burned_subtitles":True,
            "approval_required":"final_review.py --inspect and --approve"}
    report=build/"release-provenance.json"
    report.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--storyboard",required=True)
    p.add_argument("--sequence",required=True)
    p.add_argument("--audio",required=True)
    p.add_argument("--subtitles",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    result=release(a.project,a.storyboard,a.sequence,a.audio,a.subtitles,a.out)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
