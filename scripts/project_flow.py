#!/usr/bin/env python3
"""Single inspection entrypoint for a v3 audio-first GIF video project.

init creates ONLY a manifest; plan/status never fabricate narration, alignment,
art, approvals or videos. Existing v2 asset/release scripts remain the executors.
"""
import argparse
import json
import re
from pathlib import Path

from audio_timeline import sha256 as file_hash, validate as validate_audio
from visual_plan import validate as validate_visual
from candidate_pool import read as read_candidates

STAGES=("script","audio_alignment","visual_plan","aligned_subtitles","asset_production","asset_library","edit_sequence","release")
CONFIG={"version":3,"script":"script.json","audio":"audio/voiceover.wav",
        "audio_timeline":"audio-timeline.json","visual_plan":"visual-plan.json",
        "storyboard":"storyboard.json","sequence":"sequence.json",
        "release":"build/formal-sequence/release-provenance.json"}

def resolve(root,rel):
    if not isinstance(rel,str) or not rel or rel.startswith(("/", "\\")):
        raise ValueError("Project paths must be nonempty relative paths")
    root=Path(root).resolve()
    dest=(root/rel).resolve()
    if root not in dest.parents:
        raise ValueError("Project input path escapes project directory")
    return dest

def config(root):
    p=Path(root)/"project.json"
    if not p.is_file():
        raise FileNotFoundError("project.json missing; run project_flow.py init")
    value=json.loads(p.read_text(encoding="utf-8"))
    if value.get("version")!=3:
        raise ValueError("Expected v3 project.json")
    for key in CONFIG:
        if key=="version":
            continue
        resolve(root,value.get(key))
    return value

def state(root):
    root=Path(root).resolve()
    cfg=config(root)
    loc={key:resolve(root,value) for key,value in cfg.items() if key!="version"}
    stages=[]
    blockers=[]
    def entry(name,status,issues):
        stages.append({"stage":name,"status":status,"issues":issues})
        if status!="ready":
            blockers.extend(f"{name}: {x}" for x in issues)
    script=None
    if not loc["script"].is_file():
        entry("script","missing",["No locked script.json"])
    else:
        try:
            from audit_script import audit
            script=json.loads(loc["script"].read_text(encoding="utf-8"))
            report=audit(script)
            entry("script","ready" if report["pass"] else "blocked",report["issues"])
        except (ValueError,KeyError,TypeError) as exc:
            entry("script","blocked",[str(exc)])
    aligned=None
    if not loc["audio"].is_file() or not loc["audio_timeline"].is_file():
        entry("audio_alignment","missing",["Real full-track audio and verified audio-timeline.json required"])
    elif script is None:
        entry("audio_alignment","blocked",["Locked script unavailable"])
    else:
        try:
            aligned=json.loads(loc["audio_timeline"].read_text(encoding="utf-8"))
            issues=validate_audio(aligned,script,loc["audio"])
            entry("audio_alignment","ready" if not issues else "blocked",issues)
        except (ValueError,OSError,KeyError,TypeError) as exc:
            entry("audio_alignment","blocked",[str(exc)])
    if not loc["visual_plan"].is_file():
        entry("visual_plan","missing",["Visual A/B-roll plan missing"])
    elif script is None or aligned is None:
        entry("visual_plan","blocked",["Verified script/audio timeline unavailable"])
    else:
        try:
            visual=json.loads(loc["visual_plan"].read_text(encoding="utf-8"))
            issues=validate_visual(visual,aligned,script,loc["audio"])
            entry("visual_plan","ready" if not issues else "blocked",issues)
        except (ValueError,OSError,KeyError,TypeError) as exc:
            entry("visual_plan","blocked",[str(exc)])
    subtitles=root/"subtitles"/"captions.srt"
    proof=Path(str(subtitles)+".provenance.json")
    if not subtitles.is_file() or not proof.is_file():
        entry("aligned_subtitles","missing",["SRT and its verified audio provenance are required"])
    elif not loc["audio"].is_file() or not loc["audio_timeline"].is_file() or not loc["script"].is_file():
        entry("aligned_subtitles","blocked",["Original sound timeline/script missing"])
    else:
        try:
            from visual_plan import sha256_json
            p=json.loads(proof.read_text(encoding="utf-8"))
            a=json.loads(loc["audio_timeline"].read_text(encoding="utf-8"))
            issues=[]
            expected={"script_sha256":file_hash(loc["script"]),
                      "audio_sha256":file_hash(loc["audio"]),
                      "audio_timeline_sha256":sha256_json(a),
                      "srt_sha256":file_hash(subtitles)}
            for key,value in expected.items():
                if p.get(key)!=value:
                    issues.append("Aligned captions stale: "+key)
            entry("aligned_subtitles","ready" if not issues else "blocked",issues)
        except (ValueError,OSError,TypeError,KeyError) as exc:
            entry("aligned_subtitles","blocked",[str(exc)])
    production_manifest=root/"production"/"visual-asset-plan.json"
    if not production_manifest.is_file():
        entry("asset_production","missing",[
            "A/B-roll candidate batch not prepared; run visual_assets.py --prepare"])
    else:
        try:
            from visual_assets import check as check_production
            production=check_production(root)
            if production["status"]=="blocked":
                entry("asset_production","blocked",production.get("issues",[]))
            elif production["status"]=="awaiting_generation":
                entry("asset_production","missing",[
                    "Waiting for actual GPT GIF generation: "+", ".join(production["pending"])])
            else:
                entry("asset_production","ready",[])
        except (ValueError,OSError,KeyError,TypeError) as exc:
            entry("asset_production","blocked",[str(exc)])
    catalog_path=root/"library"/"catalog.json"
    if not catalog_path.is_file():
        entry("asset_library","missing",["No candidate library; produce real GPT GIF candidates"])
    else:
        try:
            c=read_candidates(root)
            if not c["candidates"]:
                entry("asset_library","blocked",["Candidate library is empty"])
            else:
                missing=[]
                for key,rec in c["candidates"].items():
                    source=resolve(root,rec["file"])
                    prompt=resolve(root,rec["prompt"])
                    if not source.is_file() or not prompt.is_file() or file_hash(source)!=rec["sha256"] or file_hash(prompt)!=rec["prompt_sha256"]:
                        missing.append(f"{key}: missing/changed GIF or prompt")
                entry("asset_library","ready" if not missing else "blocked",missing)
        except (ValueError,OSError,KeyError,TypeError) as exc:
            entry("asset_library","blocked",[str(exc)])
    if not loc["sequence"].is_file():
        entry("edit_sequence","missing",["No multi-clip sequence.json"])
    else:
        try:
            from sequence_cut import verify
            seq=json.loads(loc["sequence"].read_text(encoding="utf-8"))
            issues=verify(root,seq,loc["audio"] if loc["audio"].exists() else None,
                          storyboard=loc["storyboard"])
            entry("edit_sequence","ready" if not issues else "blocked",issues)
        except (ValueError,OSError,KeyError,TypeError) as exc:
            entry("edit_sequence","blocked",[str(exc)])
    if not loc["release"].is_file():
        entry("release","missing",["No formal release provenance"])
    else:
        try:
            record=json.loads(loc["release"].read_text(encoding="utf-8"))
            video=resolve(root,record.get("video","")) if not Path(record.get("video","/")).is_absolute() else Path(record["video"]).resolve()
            # Historical formal reports may contain absolute paths, checked directly.
            issues=[]
            if record.get("status")!="PENDING_FINAL_VIDEO_REVIEW":
                issues.append("Formal output does not have pending-review state")
            if not video.is_file() or file_hash(video)!=record.get("video_sha256"):
                issues.append("Rendered video missing or differs from release report")
            entry("release","ready" if not issues else "blocked",issues)
        except (ValueError,OSError,KeyError,TypeError) as exc:
            entry("release","blocked",[str(exc)])
    return {"version":3,"project":str(root),"stages":stages,
            "ready_for_publication":False,
            "note":"All stage checks are technical. A release still requires actual final human review.",
            "blockers":blockers}

def init(root):
    root=Path(root).resolve()
    root.mkdir(parents=True,exist_ok=True)
    path=root/"project.json"
    if path.exists():
        raise FileExistsError("Existing project manifest; will not overwrite")
    path.write_text(json.dumps(CONFIG,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return str(path)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("init","status","validate","plan"))
    p.add_argument("--project",required=True)
    a=p.parse_args()
    if a.command=="init":
        print(json.dumps({"created":init(a.project)},ensure_ascii=False))
        return
    report=state(a.project)
    if a.command=="plan":
        report["next_action"]=next((x for x in report["stages"] if x["status"]!="ready"),None)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if a.command=="validate" and report["blockers"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()
