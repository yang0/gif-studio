#!/usr/bin/env python3
"""Synchronous, resumable orchestration of real sound-first stages.

This is intentionally NOT a scheduler and does not claim to render a finished
video: visual direction and candidate selection remain explicit human/agent
decisions. Existing validated artifacts are resumed, never overwritten.
"""
import argparse
import json
from pathlib import Path
from audio_timeline import sha256, validate as validate_alignment
from visual_plan import validate as validate_visual
from project_flow import config, resolve
from sequence_cut import verify as verify_sequence

STEPS=("voice","alignment","sequence")

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def paths(project):
    root=Path(project).resolve()
    cfg=config(root)
    return root,{key:resolve(root,val) for key,val in cfg.items() if key!="version"}

def run_stage(project,stage,allow_network=False,allow_models=False,
              tts_voice="zh-CN-XiaoxiaoNeural",align_model="base",
              align_language="zh"):
    root,p=paths(project)
    if not p["script"].is_file():
        raise FileNotFoundError("Cannot proceed without locked script.json")
    script=read(p["script"])
    from audio_timeline import script_text
    script_text(script)
    if stage=="voice":
        if p["audio"].exists():
            # Existing voice may be imported rather than synthesized.
            # Never claim it is TTS-produced merely because it exists.
            from audio_timeline import probe_ms
            ms=probe_ms(p["audio"])
            if p["audio_timeline"].exists():
                errs=validate_alignment(read(p["audio_timeline"]),script,p["audio"])
                if errs:
                    raise ValueError("Existing voice/alignment changed: "+"; ".join(errs))
            return {"stage":"voice","status":"resumed_existing_audio",
                    "audio_sha256":sha256(p["audio"]),"duration_ms":ms}
        if not allow_network:
            raise RuntimeError("Voice is absent; explicit --allow-network-tts is required to call online TTS")
        from voice_production import make_audio
        result=make_audio(script,p["audio"],voice=tts_voice)
        return {"stage":"voice","status":"synthesized","result":result}
    if stage=="alignment":
        if not p["audio"].is_file():
            raise FileNotFoundError("Narration audio missing; run voice stage first")
        if p["audio_timeline"].is_file():
            errs=validate_alignment(read(p["audio_timeline"]),script,p["audio"])
            if errs:
                raise ValueError("Existing alignment invalid: "+"; ".join(errs))
            return {"stage":"alignment","status":"resumed_verified_alignment"}
        if not allow_models:
            raise RuntimeError("No alignment; explicit --allow-alignment-model is required to run local model/download")
        from forced_align import align
        result=align(script,p["audio"],model_name=align_model,language=align_language)
        p["audio_timeline"].parent.mkdir(parents=True,exist_ok=True)
        # Only write after actual align succeeds and the validator passes.
        p["audio_timeline"].write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        return {"stage":"alignment","status":"aligned","segments":len(result["segments"])}
    if stage=="director":
        from visual_director import validate as validate_director
        from character_performance import validate as validate_actor
        from broll_strategy import review as validate_broll
        from editorial_engine import recommend
        director=root/"director-v2.json"
        if not director.is_file():
            raise FileNotFoundError("Missing actual Codex-authored director-v2.json; prepare briefs with director_brief_agent.py")
        if not p["audio_timeline"].is_file() or not p["visual_plan"].is_file():
            raise FileNotFoundError("Real audio/visual plan needed before director review")
        audio=read(p["audio_timeline"])
        visual=read(p["visual_plan"])
        direction=read(director)
        errors=[x for x in validate_director(direction,audio,visual)
                if not x.endswith("(warning)")]
        errors+=validate_actor(direction,visual)["errors"]
        errors+=validate_broll(direction,visual)["errors"]
        if errors:
            raise ValueError("Director semantic/acting strategy invalid: "+"; ".join(errors))
        decisions=recommend(direction,audio,visual)
        out=root/"build"/"director"/"semantic-cut-draft.json"
        if out.is_file():
            existing=read(out)
            if existing!=decisions:
                raise ValueError("Old director cut decisions stale; archive before creating a new revision")
            return {"stage":"director","status":"resumed_verified_director",
                    "cut_risks":decisions["risks"]}
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(decisions,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        return {"stage":"director","status":"semantic_cuts_prepared_unreviewed",
                "cut_risks":decisions["risks"]}
    if stage=="mixed_preview":
        from video_cut import compile_plan,render,validate_compiled
        from audio_subtitles import build as expected_srt
        if not p["visual_plan"].is_file() or not p["storyboard"].is_file():
            raise FileNotFoundError("Real visual plan and storyboard missing")
        timeline=read(p["audio_timeline"]); visual=read(p["visual_plan"])
        storyboard=read(p["storyboard"])
        plan_path=root/"video-plan.json"
        if plan_path.is_file():
            plan=read(plan_path)
            validate_compiled(root,plan,p["audio"],script,timeline,visual,storyboard,True)
        else:
            plan=compile_plan(root,script,timeline,visual,p["audio"],storyboard,True)
            plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        subtitles=root/"subtitles"/"captions.srt"
        if not subtitles.is_file():
            raise FileNotFoundError("Actual aligned SRT required before narrated preview; run audio_subtitles.py")
        output=root/"build"/"mixed-preview.mp4"
        if output.is_file():
            report_file=root/"build"/"video-preview"/"preview-report.json"
            report=read(report_file) if report_file.is_file() else {}
            if (report.get("video_sha256")!=sha256(output) or
                report.get("visual_plan_sha256")!=plan["visual_plan_sha256"] or
                report.get("audio_sha256")!=sha256(p["audio"])):
                raise ValueError("Existing preview stale; save a new project revision")
            return {"stage":"mixed_preview","status":"resumed_unchanged_preview"}
        report=render(root,plan,script,timeline,visual,p["audio"],storyboard,
                      output,subtitles=subtitles,allow_mixed=True)
        return {"stage":"mixed_preview","status":"rendered_unreviewed",
                "video_sha256":report["video_sha256"]}
    if stage=="sequence":
        if not p["audio_timeline"].is_file() or not p["audio"].is_file():
            raise FileNotFoundError("Actual audio and audio-timeline.json required")
        timeline=read(p["audio_timeline"])
        errs=validate_alignment(timeline,script,p["audio"])
        if errs:
            raise ValueError("Audio alignment invalid: "+"; ".join(errs))
        if not p["visual_plan"].is_file() or not p["storyboard"].is_file():
            raise FileNotFoundError("Reviewed A/B-roll visual plan and storyboard required")
        visual=read(p["visual_plan"])
        errs=validate_visual(visual,timeline,script,p["audio"])
        if errs:
            raise ValueError("Visual plan invalid: "+"; ".join(errs))
        if p["sequence"].is_file():
            errs=verify_sequence(root,read(p["sequence"]),p["audio"],storyboard=p["storyboard"])
            if errs:
                raise ValueError("Old sequence is stale: "+"; ".join(errs))
            return {"stage":"sequence","status":"resumed_verified_edl"}
        from visual_to_sequence import compile_sequence
        result=compile_sequence(root,script,p["audio"],timeline,visual,read(p["storyboard"]))
        p["sequence"].parent.mkdir(parents=True,exist_ok=True)
        p["sequence"].write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        return {"stage":"sequence","status":"compiled_unreviewed","clips":len(result["clips"])}
    raise ValueError("Unknown workflow stage")

def run(project,until,**kwargs):
    if until not in STEPS and until not in ("director","mixed_preview"):
        raise ValueError("Unknown workflow target")
    if until in ("director","mixed_preview"):
        stages=["voice","alignment","director"]
        if until=="mixed_preview":stages.append("mixed_preview")
    else:
        stages=list(STEPS[:STEPS.index(until)+1])
        if until=="sequence" and (Path(project)/"director-v2.json").is_file():
            stages.insert(-1,"director")
    outcomes=[]
    for stage in stages:
        try:
            record=run_stage(project,stage,**kwargs)
            outcomes.append(record)
        except Exception as exc:
            # Persist only honest progress. Never skip a stage after a failure.
            result={"workflow":"audio_first_v3","completed":outcomes,
                    "status":"blocked","blocked_at":stage,
                    "error":str(exc)}
            write_status(project,result)
            return result
        write_status(project,{"workflow":"audio_first_v3","completed":outcomes,
                    "status":"in_progress"})
    result={"workflow":"audio_first_v3","completed":outcomes,
            "status":"inputs_ready_for_next_stage",
            "note":"This runner never awards visual QA or final video approval."}
    write_status(project,result)
    return result

def write_status(project,data):
    target=Path(project).resolve()/"build"/"workflow-status.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--until",choices=STEPS+("director","mixed_preview"),default="sequence")
    p.add_argument("--allow-network-tts",action="store_true")
    p.add_argument("--allow-alignment-model",action="store_true")
    p.add_argument("--voice",default="zh-CN-XiaoxiaoNeural")
    p.add_argument("--align-model",default="base")
    p.add_argument("--align-language",default="zh")
    args=p.parse_args()
    result=run(args.project,args.until,allow_network=args.allow_network_tts,
               allow_models=args.allow_alignment_model,tts_voice=args.voice,
               align_model=args.align_model,align_language=args.align_language)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result["status"]=="blocked":
        raise SystemExit(1)

if __name__=="__main__":
    main()
