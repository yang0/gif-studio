#!/usr/bin/env python3
"""Codex GIF generation handoff. Prepare inputs, ingest a genuine external result.

This module intentionally does not invent an image-generation API. Each run
records the exact prompt SHA and (optionally) actual character reference pack.
Tool use must occur through an actually available Codex runtime tool.
"""
import argparse
import json
import shutil
from pathlib import Path

from audio_timeline import sha256
from reference_pack import validate as validate_references
from candidate_pool import add as add_candidate
from verify_gif_asset import validate as validate_gif

def request(project,shot,candidate,prompt,reference_pack=None):
    root=Path(project).resolve()
    path=Path(prompt).resolve()
    if not path.is_file() or not path.read_text(encoding="utf-8").strip():
        raise ValueError("Exact nonempty generation prompt required")
    pack_digest=None
    if reference_pack:
        ref=Path(reference_pack).resolve()
        pack=json.loads(ref.read_text(encoding="utf-8"))
        issues=validate_references(root,pack)
        if issues:
            raise ValueError("Reference pack invalid: "+"; ".join(issues))
        pack_digest=sha256(ref)
    manifest={"version":1,"shot_id":shot,"candidate_id":candidate,
              "prompt_path":str(path),"prompt_sha256":sha256(path),
              "reference_pack_path":str(Path(reference_pack).resolve()) if reference_pack else None,
              "reference_pack_sha256":pack_digest,
              "status":"awaiting_actual_generator_call",
              "instructions":"Send exact prompt to real GIF tool. Attach each reference file only if supported. Record actual tool response; never fabricate tool calls."}
    out=root/"production"/"requests"/shot/(candidate+".json")
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():
        previous=json.loads(out.read_text(encoding="utf-8"))
        if previous!=manifest:
            raise ValueError("Request exists and is different; create a new candidate ID")
    else:
        out.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return manifest

def ingest(project,shot,candidate,gif,receipt,notes):
    root=Path(project).resolve()
    request_path=root/"production"/"requests"/shot/(candidate+".json")
    if not request_path.is_file():
        raise FileNotFoundError("No prepared generation request")
    saved=json.loads(request_path.read_text(encoding="utf-8"))
    if saved.get("shot_id")!=shot or saved.get("candidate_id")!=candidate:
        raise ValueError("Candidate differs from generation request")
    prompt=Path(saved["prompt_path"])
    if not prompt.is_file() or sha256(prompt)!=saved["prompt_sha256"]:
        raise ValueError("Prompt changed after generation request")
    if saved.get("reference_pack_path"):
        refs=Path(saved["reference_pack_path"])
        if not refs.is_file() or sha256(refs)!=saved["reference_pack_sha256"]:
            raise ValueError("Reference pack manifest changed after request")
        issues=validate_references(root,json.loads(refs.read_text(encoding="utf-8")))
        if issues:
            raise ValueError("Reference images changed after request: "+"; ".join(issues))
    evidence=json.loads(Path(receipt).read_text(encoding="utf-8"))
    if not isinstance(evidence,dict):
        raise ValueError("Tool receipt must be object")
    if evidence.get("version")!=1 or not evidence.get("tool") or not evidence.get("output_reference"):
        raise ValueError("Actual generating tool and output reference required")
    if evidence.get("prompt_sha256")!=saved["prompt_sha256"]:
        raise ValueError("Tool receipt prompt hash does not match requested prompt")
    delivery=evidence.get("prompt_delivery","context_only_unverified")
    if delivery not in ("explicit_tool_argument","context_only_unverified"):
        raise ValueError("Unknown prompt delivery")
    if saved.get("reference_pack_sha256") and evidence.get("reference_pack_sha256")!=saved["reference_pack_sha256"]:
        raise ValueError("Tool receipt does not bind requested character references")
    check=validate_gif(gif)
    if not check["pass"]:
        raise ValueError("Actual GIF failed technical intake: "+"; ".join(check["issues"]))
    record=add_candidate(root,shot,candidate,gif,prompt,
        str(evidence["tool"]),str(evidence["output_reference"]),notes,
        prompt_delivery=delivery)
    # External receipt is operator-supplied provenance, not remote attestation.
    return {"status":"candidate_recorded_unreviewed",
            "candidate":record,
            "gif_technical_check":check,
            "tool_receipt_is_unverified_external_declaration":True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--prepare",action="store_true")
    g.add_argument("--ingest",action="store_true")
    p.add_argument("--shot",required=True)
    p.add_argument("--candidate",required=True)
    p.add_argument("--prompt")
    p.add_argument("--references")
    p.add_argument("--gif")
    p.add_argument("--receipt")
    p.add_argument("--notes")
    a=p.parse_args()
    if a.prepare:
        if not a.prompt:
            p.error("--prepare requires --prompt")
        result=request(a.project,a.shot,a.candidate,a.prompt,a.references)
    else:
        if not all((a.gif,a.receipt,a.notes)):
            p.error("--ingest requires --gif --receipt --notes")
        result=ingest(a.project,a.shot,a.candidate,a.gif,a.receipt,a.notes)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
