#!/usr/bin/env python3
"""Verify actual visual reference files for a stable A-roll character.

The reference pack is a content-addressed manifest, NOT a claim that any
particular image generator consumed these images.
"""
import argparse
import json
from pathlib import Path
from PIL import Image
from audio_timeline import sha256

ROLES=("front","side","back","stroke_detail","scene")
MIN_EDGE=128

def file_in_project(project,rel):
    root=Path(project).resolve()
    if not isinstance(rel,str) or not rel or Path(rel).is_absolute():
        raise ValueError("Reference path must be relative")
    path=(root/rel).resolve()
    if root not in path.parents:
        raise ValueError("Reference path escapes project directory")
    return path

def validate(project,manifest):
    faults=[]
    if not isinstance(manifest,dict) or manifest.get("version")!=1:
        return ["Reference pack must be version 1"]
    if not str(manifest.get("character_id","")).strip():
        faults.append("Missing stable character_id")
    if not str(manifest.get("character_description","")).strip():
        faults.append("Missing character description")
    refs=manifest.get("references",{})
    if not isinstance(refs,dict):
        return faults+["references must be an object"]
    for role in ROLES:
        rec=refs.get(role)
        if not isinstance(rec,dict):
            faults.append(f"{role}: missing reference record")
            continue
        try:
            path=file_in_project(project,rec.get("file"))
            if not path.is_file():
                faults.append(f"{role}: reference image missing")
                continue
            if rec.get("sha256")!=sha256(path):
                faults.append(f"{role}: image hash no longer matches manifest")
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                if min(image.size)<MIN_EDGE:
                    faults.append(f"{role}: reference resolution too small")
        except (ValueError,TypeError,OSError) as exc:
            faults.append(f"{role}: invalid reference: {exc}")
    return faults

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--manifest",required=True)
    a=p.parse_args()
    data=json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    issues=validate(a.project,data)
    print(json.dumps({"pass":not issues,"issues":issues},ensure_ascii=False,indent=2))
    raise SystemExit(bool(issues))

if __name__=="__main__":
    main()
