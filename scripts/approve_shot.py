#!/usr/bin/env python3
"""Explicit semantic review; no silent or self-generated quality success."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from inspect_gif import digest
from production_contract import asset_status, load_manifest, fingerprint

def approve(project, shot, reviewer, notes, storyboard=None, visual_checks=None):
    project = Path(project)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", shot):
        raise ValueError("Invalid shot ID")
    source, tech = project/"gifs"/(shot+".gif"), project/"qa"/(shot+".json")
    if not source.is_file() or not tech.is_file():
        raise FileNotFoundError("GIF and technical QA report required")
    report = json.loads(tech.read_text(encoding="utf-8"))
    sha = digest(source)
    if not report.get("pass") or report.get("source_sha256") != sha:
        raise ValueError("Technical QA missing, failed or stale")
    if not reviewer.strip() or not notes.strip():
        raise ValueError("Named reviewer and substantive notes required")
    record = {"approved":True,"source_sha256":sha,
              "reviewer":reviewer,"notes":notes,
              "reviewed_at":datetime.now(timezone.utc).isoformat()}
    if storyboard is not None:
        status, reason = asset_status(project, storyboard, shot)
        if status != "registered":
            raise ValueError("Production registration invalid: "+reason)
        checks = visual_checks or {}
        if any(checks.get(k) is not True for k in
               ("semantic","motion","style","composition")):
            raise ValueError("All four visual checks must be explicitly confirmed")
        sheet = report.get("contact_sheet")
        if not sheet or not Path(sheet).is_file():
            raise ValueError("Real contact sheet required for formal review")
        record["asset_fingerprint"] = fingerprint(load_manifest(project)["assets"][shot])
        record["contact_sheet_sha256"] = digest(sheet)
        record["visual_checks"] = checks
    else:
        record["legacy_review"] = True
    output = project/"qa"/(shot+".visual.json")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return record

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--storyboard", required=True)
    p.add_argument("--shot", required=True)
    p.add_argument("--reviewer", required=True)
    p.add_argument("--notes", required=True)
    p.add_argument("--semantic-pass", action="store_true")
    p.add_argument("--motion-pass", action="store_true")
    p.add_argument("--style-pass", action="store_true")
    p.add_argument("--composition-pass", action="store_true")
    a = p.parse_args()
    storyboard = json.loads(Path(a.storyboard).read_text(encoding="utf-8"))
    flags = {"semantic":a.semantic_pass,"motion":a.motion_pass,
             "style":a.style_pass,"composition":a.composition_pass}
    print(json.dumps(approve(a.project,a.shot,a.reviewer,a.notes,storyboard,flags),
                     ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
