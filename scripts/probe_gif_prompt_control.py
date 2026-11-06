#!/usr/bin/env python3
"""Detect suspiciously similar GIF results for intentionally distinct requests.

Similarity is a heuristic only. This tool CANNOT establish prompt delivery or
semantic correctness; a human/vision reviewer must inspect the frames.
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageOps

def image_signature(path):
    with Image.open(path) as im:
        im.seek(max(0,im.n_frames//2))
        frame=im.convert("RGB")
        # Midpoint average hash provides a simple similarity warning.
        gray=ImageOps.grayscale(frame).resize((16,16))
        pix=list(gray.getdata())
        average=sum(pix)/len(pix)
        bits=[x>=average for x in pix]
        return bits, im.size

def probe(first,second):
    a,dim_a=image_signature(first)
    b,dim_b=image_signature(second)
    agreement=sum(x==y for x,y in zip(a,b))/len(a)
    suspicion=agreement>=0.88
    return {"prompt_control_suspect":suspicion,
            "midframe_ahash_agreement":round(agreement,3),
            "first_dimensions":list(dim_a),
            "second_dimensions":list(dim_b),
            "interpretation":("Two intentionally distinct prompt targets produced highly similar midframes. "
                              "Check whether the runtime actually received different prompts; "
                              "do not approve these shots automatically." if suspicion else
                              "No obvious repeated-template similarity detected; semantic review still required.")}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first",required=True)
    p.add_argument("--second",required=True)
    p.add_argument("--report",required=True)
    a=p.parse_args()
    result=probe(a.first,a.second)
    path=Path(a.report)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
