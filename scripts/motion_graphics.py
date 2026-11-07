#!/usr/bin/env python3
"""Original editable informational B-roll templates, not synthetic GPT GIFs.

Renders genuine motion-graphics footage (process/comparison/timeline/metric)
with Pillow + FFmpeg. Source data remain explicit and verifiable.
Never label the result as AI-generated character footage.
"""
import argparse
import hashlib
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

TEMPLATES={"process","comparison","timeline","metric"}
THEMES={"dark":{"bg":"#101722","surface":"#1e2b3b","fg":"#f3f7fa","muted":"#a6b9c8","accent":"#59e1ca"},
        "light":{"bg":"#f5f6f2","surface":"#e5e9e5","fg":"#172530","muted":"#556774","accent":"#137e78"}}
SAFE_FONT_PATHS=(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/msyh.ttc"
)

def fingerprint(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,
             separators=(",",":")).encode("utf-8")).hexdigest()

def font_path(path=None):
    if path:
        p=Path(path).resolve()
        if not p.is_file():
            raise FileNotFoundError("Selected font file missing")
        return p
    for item in SAFE_FONT_PATHS:
        if Path(item).is_file():
            return Path(item)
    raise FileNotFoundError("No suitable font installed; pass --font")

def font(path,size):
    return ImageFont.truetype(str(path),size)

def ease(t):
    t=max(0.0,min(1.0,t))
    return t*t*(3-2*t)

def text(draw,xy,value,ft,fill,anchor="mm"):
    draw.text(xy,str(value),font=ft,fill=fill,anchor=anchor)

def validate(spec):
    if not isinstance(spec,dict) or spec.get("version")!=1:
        raise ValueError("Motion spec must have version 1")
    kind=spec.get("template")
    if kind not in TEMPLATES:
        raise ValueError("Unsupported information motion template")
    title=spec.get("title")
    if not isinstance(title,str) or not title.strip() or len(title)>50:
        raise ValueError("A concise informative title is required (1..50 chars)")
    if spec.get("theme","dark") not in THEMES:
        raise ValueError("Unsupported theme")
    items=spec.get("items",[])
    if kind!="metric":
        if not isinstance(items,list) or not 2<=len(items)<=5:
            raise ValueError("Information graphics need 2..5 items")
        for item in items:
            if not isinstance(item,dict) or not isinstance(item.get("label"),str) or not 1<=len(item["label"].strip())<=28:
                raise ValueError("Each item needs a short accurate label")
        if kind=="comparison" and any(type(x.get("value")) not in (float,int) or x["value"]<0 for x in items):
            raise ValueError("Comparison values must be nonnegative numbers")
    else:
        if type(spec.get("value")) not in (int,float) or type(spec.get("start_value",0)) not in (int,float):
            raise ValueError("Numeric metric requires real start_value/value")
        if not isinstance(spec.get("unit",""),str) or len(spec.get("unit",""))>16:
            raise ValueError("Invalid metric unit")
    return spec

def draw_frame(spec,progress,width,height,ftpath):
    colors=THEMES[spec.get("theme","dark")]
    img=Image.new("RGB",(width,height),colors["bg"])
    d=ImageDraw.Draw(img)
    unit=min(width/1080,height/1920)
    def f(sz):return font(ftpath,max(11,int(sz*unit)))
    def tx(x,y,value,size=44,color="fg",anchor="mm"):
        text(d,(int(x),int(y)),value,f(size),colors[color],anchor)
    pad=int(width*.085)
    tx(width/2,height*.19,spec["title"],54)
    d.rounded_rectangle((pad,height*.27,width-pad,height*.78),radius=int(34*unit),
                        fill=colors["surface"])
    items=spec.get("items",[])
    t=ease(progress)
    if spec["template"]=="process":
        count=len(items)
        area=width-2*pad
        step=area/count
        for i,item in enumerate(items):
            cx=int(pad+(i+.5)*step)
            cy=int(height*.49)
            a=ease(t*count-i)
            radius=int((35+18*a)*unit)
            d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),
                      fill=colors["accent"] if a>.01 else colors["muted"])
            tx(cx,cy,str(i+1),37,"bg")
            tx(cx,cy+105*unit,item["label"],27)
            if i<count-1:
                left=cx+radius+8*unit;right=cx+step-radius-8*unit
                if right>left:
                    d.line((left,cy,right,cy),fill=colors["muted"],width=max(2,int(5*unit)))
    elif spec["template"]=="comparison":
        maximum=max(x["value"] for x in items) or 1
        count=len(items)
        for i,item in enumerate(items):
            cy=height*(.36+(i+.5)*.35/count)
            tx(pad+25*unit,cy,item["label"],27,anchor="lm")
            start=pad+width*.32
            end=start+(width-pad-start-width*.11)*item["value"]/maximum*ease(t*1.35-i*.09)
            d.rounded_rectangle((int(start),int(cy-18*unit),int(max(start+2,end)),int(cy+18*unit)),
                                radius=int(14*unit),fill=colors["accent"])
            tx(width-pad-8*unit,cy,f'{item["value"]:g}',26,anchor="rm")
    elif spec["template"]=="timeline":
        y=height*.52
        x0=pad+45*unit;x1=width-pad-45*unit
        d.line((int(x0),int(y),int(x1),int(y)),fill=colors["muted"],width=max(2,int(5*unit)))
        n=len(items)
        for i,item in enumerate(items):
            cx=x0+(x1-x0)*i/(n-1)
            a=ease(t*n-i)
            r=int((12+16*a)*unit)
            d.ellipse((int(cx-r),int(y-r),int(cx+r),int(y+r)),
                      fill=colors["accent"] if a>.01 else colors["muted"])
            tx(cx,y+(-110 if i%2 else 110)*unit,item["label"],26)
    elif spec["template"]=="metric":
        start=float(spec.get("start_value",0))
        value=start+(float(spec["value"])-start)*ease(t)
        tx(width/2,height*.49,f'{value:,.1f}'.rstrip("0").rstrip(".")+spec.get("unit",""),115)
        tx(width/2,height*.64,spec.get("caption",""),30,"muted")
    tx(width/2,height*.86,spec.get("footer",""),25,"muted")
    return img

def render(spec,out,fps=24,width=720,height=1280,duration=3,ftpath=None):
    validate(spec)
    if not 5<=fps<=60 or width%2 or height%2 or min(width,height)<200:
        raise ValueError("Invalid video format")
    if not .5<=duration<=30:
        raise ValueError("Clip duration must be 0.5..30 seconds")
    dest=Path(out).resolve()
    if dest.exists():
        raise FileExistsError("Motion video exists; do not overwrite an approved asset")
    dest.parent.mkdir(parents=True,exist_ok=True)
    ftpath=font_path(ftpath)
    n=round(duration*fps)
    with tempfile.TemporaryDirectory(prefix="gif-studio-motion-") as td:
        frames=Path(td)
        for k in range(n):
            img=draw_frame(spec,(k+.5)/n,width,height,ftpath)
            img.save(frames/f"frame-{k:05d}.png")
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                        "-framerate",str(fps),"-i",str(frames/"frame-%05d.png"),
                        "-c:v","libx264","-crf","19","-pix_fmt","yuv420p",
                        "-movflags","+faststart",str(dest)],check=True)
    from audio_timeline import sha256
    report={"version":1,"media_type":"data_motion","template":spec["template"],
            "spec_sha256":fingerprint(spec),"source_sha256":sha256(dest),
            "duration_frames":n,"fps":fps,"width":width,"height":height,
            "source_kind":"programmatic_informational_graphic_not_gpt_gif",
            "not_character_animation":True}
    dest.with_suffix(dest.suffix+".motion.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--spec",required=True);p.add_argument("--out",required=True)
    p.add_argument("--fps",type=int,default=24)
    p.add_argument("--width",type=int,default=720)
    p.add_argument("--height",type=int,default=1280)
    p.add_argument("--duration",type=float,default=3)
    p.add_argument("--font")
    a=p.parse_args()
    result=render(json.loads(Path(a.spec).read_text(encoding="utf-8")),
                  a.out,a.fps,a.width,a.height,a.duration,a.font)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
