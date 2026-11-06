#!/usr/bin/env python3
"""Strict technical gate for a generated animated portrait GIF."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageSequence, ImageChops, ImageStat

def file_sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def validate(path, target_width=720, target_height=1280, min_frames=5,
             aspect_tolerance=.035, min_short_edge=240):
    path=Path(path)
    faults=[]
    result={"file":str(path),"pass":False,"issues":faults}
    if not path.is_file():
        faults.append("GIF file does not exist")
        return result
    try:
        with Image.open(path) as im:
            if im.format!="GIF":
                faults.append(f"Actual file format is {im.format}, not GIF")
            w,h=im.size
            if min(w,h)<min_short_edge:
                faults.append(f"Short edge {min(w,h)} below minimum {min_short_edge}")
            if h==0 or abs(w/h-target_width/target_height)>aspect_tolerance:
                faults.append(f"Aspect mismatch: {w}x{h} vs required {target_width}:{target_height} portrait composition")
            frames=[f.copy() for f in ImageSequence.Iterator(im)]
            durations=[int(f.info.get("duration",im.info.get("duration",100))) for f in frames]
            if len(frames)<min_frames:
                faults.append(f"Only {len(frames)} frames; minimum {min_frames}")
            if not any(d>0 for d in durations):
                faults.append("No meaningful frame timing")
            if len(frames)>1:
                samples=[f.convert("RGB").resize((48,48)) for f in frames]
                diffs=[sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)
                       for a,b in zip(samples,samples[1:])]
                if max(diffs,default=0)<1.0:
                    faults.append("No detectable animation")
            result.update({"width":w,"height":h,"frames":len(frames),
                           "duration_sec":round(sum(durations)/1000,3),
                           "sha256":file_sha(path),"pass":not faults})
    except Exception as exc:
        faults.append(f"GIF cannot be decoded: {exc}")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--gif",required=True)
    p.add_argument("--report",required=True)
    p.add_argument("--width",type=int,default=720)
    p.add_argument("--height",type=int,default=1280)
    p.add_argument("--min-frames",type=int,default=5)
    p.add_argument("--min-short-edge",type=int,default=240)
    a=p.parse_args()
    result=validate(a.gif,a.width,a.height,a.min_frames,min_short_edge=a.min_short_edge)
    target=Path(a.report)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result["pass"] else 1)

if __name__=="__main__":
    main()
