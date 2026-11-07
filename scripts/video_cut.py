#!/usr/bin/env python3
"""Audio-first mixed source video *preview* from verified original media.

Supported: true GIF footage, real screen recordings, explicit still screenshots.
Still images are declared and visibly static, NEVER passed off as GPT GIF.
No arbitrary or fabricated code-generated vector animations.
"""
import argparse
import json
import re
import subprocess
import shutil
from pathlib import Path
from audio_timeline import sha256, validate as validate_audio
from visual_plan import validate as validate_visual, sha256_json
from candidate_pool import read as read_catalog
from edit_plan import stable_digest
from inspect_gif import inspect as inspect_gif

VIDEOS={".mp4",".mov",".mkv",".webm"}
STILLS={".png",".jpg",".jpeg",".webp"}
ID=re.compile(r"^[A-Za-z0-9_-]+$")

def inside(root,relative):
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute():
        raise ValueError("Source must be a project-relative path")
    root=Path(root).resolve()
    path=(root/relative).resolve()
    if root not in path.parents or not path.is_file():
        raise ValueError("Source missing or outside project: "+relative)
    return path

def video_duration(path):
    raw=subprocess.check_output(["ffprobe","-v","error","-show_entries",
          "format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],
          text=True)
    return float(raw.strip())

def video_has_stream(path):
    raw=subprocess.check_output(["ffprobe","-v","error","-select_streams",
        "v:0","-show_entries","stream=codec_type","-of","csv=p=0",str(path)],
        text=True)
    return "video" in raw

def compile_plan(project,script,timeline,visual,audio,storyboard,allow_mixed=False):
    root=Path(project).resolve()
    faults=validate_visual(visual,timeline,script,audio)
    if faults:
        raise ValueError("Visual plan invalid: "+"; ".join(faults))
    director_path=root/"director-v2.json"
    director=None
    directed={}
    if director_path.is_file():
        from visual_director import validate as director_validate
        director=json.loads(director_path.read_text(encoding="utf-8"))
        problems=[x for x in director_validate(director,timeline,visual)
                  if not x.endswith("(warning)")]
        if problems:
            raise ValueError("Semantic director plan invalid/stale: "+"; ".join(problems))
        directed={x["shot_id"]:x for x in director["shots"]}
    fps=storyboard["fps"]
    if type(fps)!=int or not 1<=fps<=60:
        raise ValueError("Invalid output fps")
    width=storyboard["width"];height=storyboard["height"]
    if any(type(x)!=int or x<2 or x%2 for x in (width,height)):
        raise ValueError("Output canvas needs even positive dimensions")
    shots=visual["shots"]
    if shots[0]["start_ms"]!=0 or abs(shots[-1]["end_ms"]-timeline["duration_ms"])>35:
        raise ValueError("Visual plan must cover entire recorded audio from 0ms")
    catalog=read_catalog(root)
    clips=[]
    for i,scene in enumerate(shots):
        typ=scene["media_type"]
        if typ not in ("gpt_gif","screen_recording","screenshot","data_motion"):
            raise ValueError(f"{scene['id']}: {typ} needs a real supported renderer")
        if director is not None:
            instruction=directed[scene["id"]]
            requested=instruction["preferred_media"]
            compatible=(requested==typ or
                        (requested=="original_animation" and typ=="data_motion"))
            if not compatible:
                raise ValueError(f"{scene['id']}: editor media {typ} differs from director decision {requested}")
        if typ!="gpt_gif" and not allow_mixed:
            raise ValueError("Mixed-media video requires explicit --allow-mixed-media")
        if typ=="gpt_gif":
            key=str(scene.get("source_shot_id",""))+"/"+str(scene.get("candidate_id",""))
            rec=catalog["candidates"].get(key)
            if not rec:
                raise ValueError("GIF candidate missing: "+key)
            path=inside(root,rec["file"])
            expected=rec["sha256"]
            if sha256(inside(root,rec["prompt"]))!=rec["prompt_sha256"]:
                raise ValueError("GIF prompt changed: "+key)
        else:
            path=inside(root,scene.get("source_file"))
            expected=scene.get("source_sha256")
            if typ in ("screen_recording","data_motion") and path.suffix.lower() not in VIDEOS:
                raise ValueError("Recording must be a real video file")
            if typ=="data_motion":
                proof=Path(str(path)+".motion.json")
                if not proof.is_file():
                    raise ValueError("Information motion must include generated provenance report")
                meta=json.loads(proof.read_text(encoding="utf-8"))
                if (meta.get("media_type")!="data_motion" or
                    meta.get("source_sha256")!=expected or
                    meta.get("source_kind")!="programmatic_informational_graphic_not_gpt_gif"):
                    raise ValueError("Information motion provenance invalid or outdated")
            if typ=="screenshot" and path.suffix.lower() not in STILLS:
                raise ValueError("Screenshot must be a supported still image")
        if sha256(path)!=expected:
            raise ValueError(f"{scene['id']}: source changed or source_sha256 absent")
        source_in=scene.get("source_in_ms",0)
        if type(source_in)!=int or source_in<0:
            raise ValueError("source_in_ms must be nonnegative integer")
        if typ=="screenshot" and source_in:
            raise ValueError("A still screenshot cannot have a source in-point")
        first=round(scene["start_ms"]*fps/1000)
        last=round(scene["end_ms"]*fps/1000)
        count=last-first
        if count<1:
            raise ValueError("Clip shorter than one output frame")
        if typ=="gpt_gif":
            info=inspect_gif(path,0,999999)
            if not info.get("pass"):
                raise ValueError("GIF cannot decode: "+"; ".join(info.get("issues",[])))
            duration=info["duration_sec"]
        elif typ in ("screen_recording","data_motion"):
            if not video_has_stream(path):
                raise ValueError("Recording has no video stream")
            duration=video_duration(path)
        else:
            from PIL import Image
            with Image.open(path) as picture:
                picture.verify()
            duration=None
        if duration is not None and (source_in/1000+count/fps)>duration+1/fps+.001:
            raise ValueError(f"{scene['id']}: source footage too short, cannot freeze to fill")
        camera=scene.get("camera_preset","native")
        allowed={"native","presenter","wide","medium","closeup","reaction"}
        if camera not in allowed:
            raise ValueError(f"{scene['id']}: unknown camera preset")
        if camera!="native" and scene["roll"]!="A":
            raise ValueError("A-roll camera presets cannot be attached to B-roll")
        if typ=="screenshot" and camera!="native":
            raise ValueError("Still screenshot cannot become fake A-roll camera animation")
        if camera!="native" and not str(scene.get("character_id","")).strip():
            raise ValueError("A-roll camera requires stable character_id")
        viewpoint=scene.get("viewpoint","main_character" if scene["roll"]=="A" else "content")
        if viewpoint not in ("main_character","supporting_character","presenter","first_person","content"):
            raise ValueError(f"{scene['id']}: unknown viewpoint")
        if scene["roll"]=="B" and viewpoint!="content":
            raise ValueError("B-roll must not claim a character viewpoint")
        if scene["roll"]=="A" and viewpoint=="first_person":
            if (scene.get("role")!="point_of_view" or
                scene.get("source_perspective")!="verified_first_person" or
                camera!="native"):
                raise ValueError("First-person A-roll requires verified actual POV source; crop is not POV")
        if scene["roll"]=="A" and viewpoint=="supporting_character" and not scene.get("character_id"):
            raise ValueError("Supporting-character A-roll requires character_id")
        clips.append({
            "id":"cut-"+str(i+1).zfill(3),
            "viewpoint":viewpoint,
            "camera_preset":camera,
            "character_id":scene.get("character_id"),
            "role":scene["roll"],"media_type":typ,
            "source_file":str(path.relative_to(root)),
            "source_sha256":expected,
            "source_in_ms":source_in,"start_frame":first,
            "duration_frames":count,"visual_plan_id":scene["id"],
            "cut_reason":scene["cut_reason"],
            "static_source":typ=="screenshot"
        })
    # Preserve real voice timeline positions: do not move later cuts to hide gaps.
    cursor=0
    for c in clips:
        if c["start_frame"]!=cursor:
            raise ValueError("Visual cuts have a frame gap/overlap")
        cursor+=c["duration_frames"]
    if abs(cursor/fps-timeline["duration_ms"]/1000)>.035:
        raise ValueError("Visual frame total differs from real narration")
    result={"version":1,"kind":"audio_first_video_preview",
            "fps":fps,"width":width,"height":height,"clips":clips,
            "total_frames":cursor,
            "audio_sha256":sha256(audio),
            "audio_timeline_sha256":sha256_json(timeline),
            "visual_plan_sha256":sha256_json(visual),
            "storyboard_sha256":stable_digest(storyboard),
            "status":"UNREVIEWED_MIXED_PREVIEW"}
    if director is not None:
        result["director_plan_sha256"]=sha256_json(director)
    return result

def validate_compiled(root,plan,audio,script,timeline,visual,storyboard,allow_mixed):
    expected=compile_plan(root,script,timeline,visual,audio,storyboard,allow_mixed)
    if plan!=expected:
        raise ValueError("Compiled video plan differs from current audio/visual/assets; recompile")
    return expected

def render(project,plan,script,timeline,visual,audio,storyboard,
           output,subtitles=None,allow_mixed=False):
    root=Path(project).resolve()
    validate_compiled(root,plan,audio,script,timeline,visual,storyboard,allow_mixed)
    output=Path(output).resolve()
    if output.exists():
        raise FileExistsError("Preview exists; save a new revision instead of overwriting")
    output.parent.mkdir(parents=True,exist_ok=True)
    work=root/"build"/"video-preview"/"clips"
    work.mkdir(parents=True,exist_ok=True)
    fps=plan["fps"];w=plan["width"];h=plan["height"]
    clips=[]
    for clip in plan["clips"]:
        source=inside(root,clip["source_file"])
        duration=clip["duration_frames"]/fps
        start=clip["source_in_ms"]/1000
        # Clip cache is content-addressed by all actual render parameters:
        # an untouched shot can be reused after a different shot is reworked.
        key=sha256_json({"clip":clip,"fps":fps,"width":w,"height":h,
                         "pipeline":"mixed-v31-cache-v1"})
        target=work/(key+".mp4")
        receipt=work/(key+".json")
        reusable=False
        if target.is_file() and receipt.is_file():
            try:
                proof=json.loads(receipt.read_text(encoding="utf-8"))
                reusable=(proof.get("render_key")==key and
                          proof.get("video_sha256")==sha256(target) and
                          proof.get("duration_frames")==clip["duration_frames"])
            except (ValueError,OSError):
                reusable=False
        if reusable:
            clips.append(target)
            continue
        if target.exists():
            target.unlink()
        if receipt.exists():
            receipt.unlink()
        typ=clip["media_type"]
        cmd=["ffmpeg","-hide_banner","-loglevel","error","-y"]
        if typ=="screenshot":
            cmd+=["-loop","1","-framerate",str(fps),"-i",str(source)]
        elif typ=="gpt_gif":
            cmd+=["-ignore_loop","1","-i",str(source)]
        else:
            cmd+=["-i",str(source)]
        # Source timestamp trim BEFORE fps and rescale. Screenshots are explicit
        # held stills, not AI motion; no GIF/recording loops.
        vf=[]
        if typ!="screenshot":
            vf.append(f"trim=start={start:.6f}:duration={duration:.6f}")
            vf.append("setpts=PTS-STARTPTS")
        camera=clip.get("camera_preset","native")
        if camera in ("medium","presenter","closeup","reaction"):
            # New framing of a real source, NOT a newly generated camera angle.
            scale={"medium":1.14,"presenter":1.07,"closeup":1.42,
                   "reaction":1.32}[camera]
            vf.append(f"crop=iw/{scale}:ih/{scale}:(iw-ow)/2:(ih-oh)/2")
        vf.extend([f"fps={fps}",f"scale={w}:{h}:force_original_aspect_ratio=decrease",
                   f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black","setsar=1","format=yuv420p"])
        cmd+=["-vf",",".join(vf),"-frames:v",str(clip["duration_frames"]),
              "-an","-c:v","libx264","-pix_fmt","yuv420p",str(target)]
        subprocess.run(cmd,check=True)
        counted=subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
            "-count_frames","-show_entries","stream=nb_read_frames",
            "-of","default=noprint_wrappers=1:nokey=1",str(target)],text=True).strip()
        if int(counted)!=clip["duration_frames"]:
            raise ValueError(f"{clip['id']}: rendered {counted} frames, expected {clip['duration_frames']}; no filler permitted")
        receipt.write_text(json.dumps({"render_key":key,"video_sha256":sha256(target),
                                       "duration_frames":clip["duration_frames"]},
                                       indent=2)+"\n",encoding="utf-8")
        clips.append(target)
    concat=root/"build"/"video-preview"/"concat.txt"
    concat.write_text("".join("file '"+str(x.resolve()).replace("'","'\\''")+"'\n" for x in clips),encoding="utf-8")
    joined=root/"build"/"video-preview"/"joined.mp4"
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
          "-f","concat","-safe","0","-i",str(concat),
          "-an","-c:v","libx264","-pix_fmt","yuv420p",str(joined)],check=True)
    command=["ffmpeg","-hide_banner","-loglevel","error","-y",
            "-i",str(joined),"-i",str(Path(audio).resolve()),
            "-map","0:v:0","-map","1:a:0"]
    if subtitles is not None:
        from release_sequence import subtitle_issues
        from audio_subtitles import build as expected_subtitles
        issues=subtitle_issues(subtitles,plan["total_frames"]/fps)
        # Do not accept visually plausible but stale/mismatched subtitle files.
        # The exact captions must be produced from the same real aligned voice.
        content=Path(subtitles).read_text(encoding="utf-8")
        expected=expected_subtitles(timeline,script,audio)
        if content!=expected:
            issues.append("SRT text/timestamps differ from current real audio alignment")
        proof=Path(str(subtitles)+".provenance.json")
        if not proof.is_file():
            issues.append("Aligned subtitle provenance report is missing")
        else:
            meta=json.loads(proof.read_text(encoding="utf-8"))
            if (meta.get("audio_sha256")!=sha256(audio) or
                meta.get("audio_timeline_sha256")!=sha256_json(timeline) or
                meta.get("srt_sha256")!=sha256(subtitles)):
                issues.append("Subtitle provenance no longer matches audio/timeline/SRT")
        if issues:
            raise ValueError("Invalid SRT: "+"; ".join(issues))
        arg="subtitles="+str(Path(subtitles).resolve()).replace("\\","\\\\").replace(":","\\:").replace("'","\\'")
        command+=["-vf",arg,"-c:v","libx264","-crf","19"]
    else:
        command+=["-c:v","copy"]
    command+=["-c:a","aac","-t",str(plan["total_frames"]/fps),
              "-movflags","+faststart",str(output)]
    subprocess.run(command,check=True)
    report={"status":"UNREVIEWED_MIXED_PREVIEW","output":str(output),
            "video_sha256":sha256(output),
            "audio_sha256":sha256(audio),
            "visual_plan_sha256":plan["visual_plan_sha256"],
            "clip_count":len(clips),
            "media_types":sorted(set(x["media_type"] for x in plan["clips"])),
            "contains_explicit_stills":any(x["static_source"] for x in plan["clips"]),
            "subtitles_burned":subtitles is not None,
            "formal_approval":False,
            "note":"This video must be watched and listened to before release; no auto semantic approval"}
    out=root/"build"/"video-preview"/"preview-report.json"
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--audio")
    p.add_argument("--script")
    p.add_argument("--timeline")
    p.add_argument("--visual-plan")
    p.add_argument("--storyboard")
    p.add_argument("--subtitles")
    p.add_argument("--out")
    p.add_argument("--plan")
    p.add_argument("--allow-mixed-media",action="store_true")
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument("--compile",action="store_true")
    group.add_argument("--preview",action="store_true")
    a=p.parse_args()
    root=Path(a.project).resolve()
    read=lambda path:json.loads(Path(path).read_text(encoding="utf-8"))
    script=read(a.script or root/"script.json")
    timeline=read(a.timeline or root/"audio-timeline.json")
    visual=read(a.visual_plan or root/"visual-plan.json")
    storyboard=read(a.storyboard or root/"storyboard.json")
    audio=a.audio or root/"audio"/"voiceover.wav"
    dest=Path(a.plan or root/"video-plan.json")
    if a.compile:
        if dest.exists():
            raise FileExistsError("Video plan exists; save a new revision")
        result=compile_plan(root,script,timeline,visual,audio,storyboard,a.allow_mixed_media)
        dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"plan":str(dest),"clips":len(result["clips"])},ensure_ascii=False))
    else:
        result=render(root,read(dest),script,timeline,visual,audio,storyboard,
                a.out or root/"build"/"mixed-preview.mp4",
                subtitles=a.subtitles,allow_mixed=a.allow_mixed_media)
        print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
