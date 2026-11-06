#!/usr/bin/env python3
"""Render ONLY the chosen real GIFs as an explicitly unapproved editorial MP4.

Unlike formal composition, this intentionally needs no visual QA approval: its
purpose is to create evidence for the human editor to review before approval.
It never uses synthetic/vector stand-in imagery or claims the video is final.
"""
import argparse
import json
import subprocess
from pathlib import Path
from candidate_pool import selection_status, read as read_candidates
from edit_plan import create_plan, validate_plan
from gif_to_mp4 import convert
from inspect_gif import digest

def run(args):
    subprocess.run(args,check=True)

def render(project,storyboard,out,audio=None):
    root=Path(project).resolve()
    board=json.loads(Path(storyboard).read_text(encoding="utf-8"))
    catalog=read_candidates(root)
    if not catalog["selections"]:
        raise ValueError("No candidate selected; review alternatives and select first")
    for shot in board["shots"]:
        sid=shot["id"]
        ok,why=selection_status(root,sid)
        if not ok:
            raise ValueError(f"{sid}: {why}")
        rec=catalog["candidates"][sid+"/"+catalog["selections"][sid]["candidate_id"]]
        source=root/"gifs"/(sid+".gif")
        if digest(source)!=rec["sha256"]:
            raise ValueError("Selected GIF was changed")
    plan=create_plan(root,board,audio)
    problems=validate_plan(root,board,plan,audio,require_review=False)
    # Warn on too-long holds, but allow producing honest review evidence.
    build=root/"build"
    build.mkdir(parents=True,exist_ok=True)
    fps=int(board["fps"])
    clips=[]
    for shot in board["shots"]:
        src=root/"gifs"/(shot["id"]+".gif")
        dst=build/"previews"/(shot["id"]+".mp4")
        convert(src,dst,shot["duration_sec"],board["width"],board["height"],fps,mode="hold")
        clips.append(dst)
    concat=build/"editorial-clips.txt"
    def escaped(f):
        return str(f.resolve()).replace("'","'\\''")
    concat.write_text("".join("file '"+escaped(f)+"'\n" for f in clips),encoding="utf-8")
    out=Path(out).resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    video=build/"editorial-silent.mp4"
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0",
         "-i",str(concat),"-c:v","libx264","-pix_fmt","yuv420p","-an",str(video)])
    if audio:
        audio=Path(audio).resolve()
        run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(video),
             "-i",str(audio),"-map","0:v:0","-map","1:a:0",
             "-c:v","copy","-c:a","aac","-t",str(plan["duration_sec"]),str(out)])
    else:
        import shutil
        shutil.copyfile(video,out)
    report={"video":str(out),"status":"UNREVIEWED_EDITORIAL_PREVIEW",
            "candidate_selection_verified":True,
            "formal_visual_qa_enforced":False,
            "audio_present":bool(audio),
            "timeline_warnings":problems,
            "review_required":True,
            "shot_candidates":[{"shot":s["id"],
              "candidate":catalog["selections"][s["id"]]["candidate_id"],
              "sha256":digest(root/"gifs"/(s["id"]+".gif"))}
              for s in board["shots"]]}
    (build/"editorial-preview-report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--storyboard",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--audio")
    a=p.parse_args()
    print(json.dumps(render(a.project,a.storyboard,a.out,a.audio),
                     ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
