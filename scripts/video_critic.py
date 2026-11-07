#!/usr/bin/env python3
"""Video Critic v3.1: reproducible audiovisual risk evidence, not aesthetic judgment.

FFprobe/decoded video frames supply measurable observations; human/vision-agent
review is a separate signed *declaration* with explicit evidence. Never claim
CI fixture recordings have been genuinely watched, liked, or approved.
"""
import argparse
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from audio_timeline import sha256
from visual_plan import sha256_json

WEIGHTS={"content":25,"visual":25,"pacing":20,"audio":15,"continuity":15}
CHECKS={"knowledge_error","provenance_misrepresentation","severe_av_desync"}
AUDIT_VERSION=1

def probe(file):
    obj=json.loads(subprocess.check_output([
        "ffprobe","-v","error","-show_format","-show_streams",
        "-of","json",str(file)],text=True))
    types={x.get("codec_type") for x in obj.get("streams",[])}
    return {"duration_s":float(obj.get("format",{}).get("duration") or 0),
            "video":("video" in types),"audio":("audio" in types),
            "width":next((x.get("width") for x in obj.get("streams",[]) if x.get("codec_type")=="video"),None),
            "height":next((x.get("height") for x in obj.get("streams",[]) if x.get("codec_type")=="video"),None)}

def frame(video,at_seconds):
    raw=subprocess.run(["ffmpeg","-v","error","-ss",f"{at_seconds:.3f}",
        "-i",str(video),"-map","0:v:0","-frames:v","1",
        "-vf","scale=96:96:flags=area","-f","image2pipe","-vcodec","mjpeg","-"],
        capture_output=True,check=True).stdout
    if not raw:
        raise ValueError("Cannot decode requested video frame")
    import io
    with Image.open(io.BytesIO(raw)) as img:
        return img.convert("RGB").copy()

def difference(a,b):
    delta=ImageChops.difference(a,b)
    return sum(ImageStat.Stat(delta).mean)/(3*255)

def audio_levels(video):
    """Loudness evidence only: an AAC track can be silence or machine speech."""
    proc=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(video),
        "-vn","-af","volumedetect","-f","null","-"],
        capture_output=True,text=True,check=False)
    if proc.returncode:
        return {"available":False,"error":proc.stderr[-300:]}
    match=re.search(r"mean_volume:\s*(-?inf|-?[\d.]+)\s*dB",proc.stderr)
    peak=re.search(r"max_volume:\s*(-?inf|-?[\d.]+)\s*dB",proc.stderr)
    def value(found):
        if not found or found.group(1)=="-inf":
            return None
        return float(found.group(1))
    return {"available":True,"mean_db":value(match),"peak_db":value(peak),
            "speech_intelligibility_verified":False,
            "natural_narration_verified":False}

def composition_risk(picture):
    """Estimate large uniform empty borders; never claim actual subject size."""
    grayscale=picture.convert("L")
    w,h=grayscale.size
    border=Image.new("L",(w,h))
    top=grayscale.crop((0,0,w,int(h*.16)))
    bottom=grayscale.crop((0,int(h*.84),w,h))
    # If both edge bands have very low variance while the central field
    # has detail, this might be a card-with-small-center composition.
    center=grayscale.crop((int(w*.2),int(h*.2),int(w*.8),int(h*.8)))
    var_center=ImageStat.Stat(center).stddev[0]
    var_top=ImageStat.Stat(top).stddev[0]
    var_bottom=ImageStat.Stat(bottom).stddev[0]
    return var_top<5 and var_bottom<5 and var_center>20

def inspect(video,plan=None,subtitles=None):
    video=Path(video).resolve()
    if not video.is_file():
        raise FileNotFoundError("Real rendered movie required")
    info=probe(video)
    if not info["video"] or info["duration_s"]<=0:
        raise ValueError("Cannot audit a file without playable video")
    risks=[]
    if not info["audio"]:
        risks.append({"kind":"missing_audio","severity":"high","shot_id":None,
                      "evidence":"ffprobe: no audio stream"})
    loudness=audio_levels(video) if info["audio"] else {"available":False}
    if loudness.get("available") and loudness.get("peak_db") is None:
        risks.append({"kind":"silent_audio_track","severity":"high","shot_id":None,
                      "evidence":"ffmpeg volumedetect found no meaningful audio peak; an AAC track alone is not narration"})
    elif loudness.get("available") and loudness.get("mean_db") is not None and loudness["mean_db"]<-48:
        risks.append({"kind":"very_low_audio","severity":"medium","shot_id":None,
                      "evidence":f"Mean audio level {loudness['mean_db']} dB; listen and inspect real narration"})
    if subtitles is None and info["audio"]:
        risks.append({"kind":"subtitles_not_provided","severity":"medium","shot_id":None,
                      "evidence":"No aligned SRT was supplied to this technical inspection; cannot attest caption quality"})
    elif subtitles is not None and Path(subtitles).is_file():
        from release_sequence import subtitle_issues
        for problem in subtitle_issues(subtitles,info["duration_s"]):
            risks.append({"kind":"subtitle_timing_risk","severity":"high","shot_id":None,
                          "evidence":problem})

    if subtitles is not None and not Path(subtitles).is_file():
        risks.append({"kind":"missing_subtitles","severity":"high","shot_id":None,
                      "evidence":"Subtitle file path is absent"})
    if info["width"] and info["height"] and info["width"]<400:
        risks.append({"kind":"low_resolution","severity":"medium","shot_id":None,
                      "evidence":f"ffprobe width={info['width']} px"})
    clips=plan.get("clips",[]) if isinstance(plan,dict) else []
    fps=plan.get("fps") if isinstance(plan,dict) else None
    if clips and (not isinstance(fps,int) or fps<=0):
        raise ValueError("A clip plan must contain integer positive fps")
    observations=[]
    samples=[]
    for i,clip in enumerate(clips):
        start=clip.get("start_frame")
        count=clip.get("duration_frames")
        if type(start)!=int or type(count)!=int or count<1:
            raise ValueError("Invalid clip frame bounds")
        duration=count/fps
        a=(start+.2*count)/fps
        b=(start+.8*count)/fps
        if b>=info["duration_s"]:
            b=max(a,info["duration_s"]-.02)
        first=frame(video,a)
        last=frame(video,b)
        delta=difference(first,last)
        observations.append({"shot_id":clip.get("visual_plan_id",clip.get("id",f"shot-{i+1}")),
                             "duration_s":round(duration,3),
                             "within_shot_frame_change":round(delta,5),
                             "media_type":clip.get("media_type"),
                             "camera_preset":clip.get("camera_preset","native"),
                             "static_source":clip.get("static_source",False)})
        samples.append(first)
        if composition_risk(first):
            risks.append({"kind":"uniform_margin_composition_risk","severity":"medium",
                          "shot_id":observations[-1]["shot_id"],
                          "evidence":"Top and bottom 16% have little visible detail vs center; check actual subject prominence and intentional negative space"})
        if duration>=2.5 and delta<.013:
            risks.append({"kind":"low_motion_risk","severity":"medium",
                          "shot_id":observations[-1]["shot_id"],
                          "evidence":f"Decoded-frame normalized difference {delta:.4f} at 20% vs 80% of {duration:.2f}s; deliberate stills may be valid"})
        if i:
            neighbor=difference(samples[-2],first)
            if neighbor<.045:
                risks.append({"kind":"adjacent_visual_similarity","severity":"medium",
                              "shot_id":observations[-1]["shot_id"],
                              "evidence":f"Decoded shot-start difference {neighbor:.4f}; this is a visual repetition risk, not semantic proof"})
    if len(observations)>=4:
        lengths=[r["duration_s"] for r in observations]
        if max(lengths)-min(lengths)<.15:
            risks.append({"kind":"mechanical_equal_duration","severity":"medium","shot_id":None,
                          "evidence":f"{len(lengths)} clips have near-equal durations {lengths}"})
    if clips:
        expected=max(x["start_frame"]+x["duration_frames"] for x in clips)/fps
        if abs(info["duration_s"]-expected)>.25:
            risks.append({"kind":"duration_mismatch","severity":"high","shot_id":None,
                          "evidence":f"actual {info['duration_s']:.3f}s, EDL {expected:.3f}s"})
    return {"version":AUDIT_VERSION,"status":"TECHNICAL_RISK_REPORT_UNREVIEWED",
            "video_sha256":sha256(video),"video":str(video),"technical":info,
            "loudness_evidence":loudness,
            "source_plan_sha256":sha256_json(plan) if plan is not None else None,
            "observations":observations,"risks":risks,
            "cannot_assess":["subject prominence","knowledge truth","actual character identity",
                             "text legibility","quality of narration","cinematic appeal",
                             "viewer comprehension"],
            "approved":False}

def check_report(report,video,plan=None):
    if report.get("version")!=AUDIT_VERSION or report.get("video_sha256")!=sha256(video):
        raise ValueError("Critic evidence stale: rendered video changed")
    if plan is not None and report.get("source_plan_sha256")!=sha256_json(plan):
        raise ValueError("Critic evidence stale: source edit plan changed")

def review(report,video,reviewer,notes,scores,blocking_findings,watched_entire_video=False):
    check_report(report,video)
    if not watched_entire_video:
        raise ValueError("Actual full-video watch/listen attestation required")
    if not isinstance(reviewer,str) or not reviewer.strip() or not isinstance(notes,str) or len(notes.strip())<40:
        raise ValueError("Real named reviewer and concrete notes (>=40 chars) required")
    if set(scores)!=set(WEIGHTS) or any(type(v) not in (int,float) or not 0<=v<=10 for v in scores.values()):
        raise ValueError("All five human review scores must be in 0..10")
    if not isinstance(blocking_findings,dict) or set(blocking_findings)!=CHECKS or any(type(v)!=bool for v in blocking_findings.values()):
        raise ValueError("Three explicit non-fabricated blocking-findings flags required")
    weighted=round(sum(scores[k]*w for k,w in WEIGHTS.items())/10,2)
    eligible=(weighted>=80 and all(v>=6 for v in scores.values()) and
              not any(blocking_findings.values()))
    return {"version":1,"status":"HUMAN_REVIEW_DECLARED" if eligible else "HUMAN_REWORK_REQUIRED",
            "video_sha256":report["video_sha256"],
            "technical_report_sha256":sha256_json(report),
            "reviewer":reviewer.strip(),"review_notes":notes.strip(),
            "watched_entire_video":True,
            "scores":scores,"weighted_score":weighted,
            "blocking_findings":blocking_findings,
            "eligible_for_independent_final_review":eligible,
            "note":"Human declaration, not independently verified observation or a replacement for final_review.py"}


def validate_human_review(human,report):
    """Check internal score consistency; a declaration is not a trusted signature."""
    if not isinstance(human,dict):
        return ["Human quality review must be an object"]
    issues=[]
    scores=human.get("scores",{})
    findings=human.get("blocking_findings",{})
    if not isinstance(scores,dict) or set(scores)!=set(WEIGHTS) or any(
        type(v) not in (int,float) or not 0<=v<=10 for v in scores.values()):
        return ["Human quality scores missing or invalid"]
    if not isinstance(findings,dict) or set(findings)!=CHECKS or any(
        type(v)!=bool for v in findings.values()):
        return ["Human blocking findings invalid"]
    weighted=round(sum(scores[k]*w for k,w in WEIGHTS.items())/10,2)
    eligible=weighted>=80 and all(x>=6 for x in scores.values()) and not any(findings.values())
    if human.get("video_sha256")!=report.get("video_sha256"):
        issues.append("Human review applies to a different movie")
    if human.get("technical_report_sha256")!=sha256_json(report):
        issues.append("Human review applies to a different technical evidence report")
    if human.get("weighted_score")!=weighted:
        issues.append("Human weighted score was altered")
    if human.get("eligible_for_independent_final_review") is not eligible:
        issues.append("Human review eligibility is inconsistent")
    if human.get("status")!=("HUMAN_REVIEW_DECLARED" if eligible else "HUMAN_REWORK_REQUIRED"):
        issues.append("Human review status inconsistent with actual scores/findings")
    if human.get("watched_entire_video") is not True:
        issues.append("Actual full-video watch attestation missing")
    if not isinstance(human.get("reviewer"),str) or not human["reviewer"].strip():
        issues.append("Reviewer identity missing")
    if not isinstance(human.get("review_notes"),str) or len(human["review_notes"].strip())<40:
        issues.append("Real full-video observation notes missing")
    return issues

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--video",required=True)
    p.add_argument("--plan")
    p.add_argument("--subtitles")
    p.add_argument("--report",required=True)
    p.add_argument("--review-input",help="JSON containing reviewer, notes, scores, blocking_findings and watched_entire_video")
    p.add_argument("--review-out")
    a=p.parse_args()
    plan=json.loads(Path(a.plan).read_text(encoding="utf-8")) if a.plan else None
    if a.review_input:
        report=json.loads(Path(a.report).read_text(encoding="utf-8"))
        check_report(report,a.video,plan)
        content=json.loads(Path(a.review_input).read_text(encoding="utf-8"))
        result=review(report,a.video,content["reviewer"],content["notes"],
                      content["scores"],content["blocking_findings"],
                      content.get("watched_entire_video",False))
        if not a.review_out:
            p.error("--review-out required for review")
        dest=Path(a.review_out)
    else:
        result=inspect(a.video,plan,a.subtitles)
        dest=Path(a.report)
    if dest.exists():
        raise FileExistsError("Existing critic record; use an explicit new revision")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
