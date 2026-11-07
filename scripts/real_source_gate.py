#!/usr/bin/env python3
"""Authentic-media preflight for the DEFAULT v3.1 production entrypoints.

Provenance metadata is an accountable declaration, NOT machine proof of
authorship, video quality, or that model inference really happened. Final
creative judgment still requires watching the actual footage.
"""
import argparse
import json
import subprocess
from pathlib import Path

from audio_timeline import sha256
from candidate_pool import read as read_candidates

ALLOWED = {
    "gpt_gif": {"model_generated_gif"},
    "real_video": {"camera_recording", "licensed_real_footage"},
    "screen_recording": {"screen_capture"},
    "screenshot": {"screen_capture", "camera_photo", "licensed_photo",
                   "model_generated_image"},
    "original_animation": {"model_generated_video"},
}
FORBIDDEN = {"data_motion", "text_overlay", "svg", "vector", "pillow",
             "canvas", "programmatic", "motion_graphics"}
VIDEO = {".mp4", ".mov", ".mkv", ".webm"}
STILL = {".png", ".jpeg", ".jpg", ".webp"}
GAPS_HELP = {
    "gpt_gif": "Generate/import a real animated GIF with explicit model invocation and register it in candidate_pool.",
    "real_video": "Import actual filmed footage and record verifiable acquisition details.",
    "screen_recording": "Capture a real screen session, do not synthesize the UI as a video.",
    "screenshot": "Import a real screenshot/photo as an explicitly static evidence shot.",
    "original_animation": "Import an actual model-generated video and its generation reference.",
}


def file_in_project(root, relative):
    if not isinstance(relative, str) or not relative:
        return None
    root = Path(root).resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        return None
    return target


def probe_video(path):
    raw = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type", "-of", "json", str(path)],
        text=True, encoding="utf-8")
    obj = json.loads(raw)
    if not any(row.get("codec_type") == "video" for row in obj.get("streams", [])):
        raise ValueError("No video stream")
    duration = float(obj.get("format", {}).get("duration") or 0)
    if duration <= 0:
        raise ValueError("Missing positive video duration")
    return duration


def inspect_media(root, visual):
    """Return one actionable gap report per shot; NEVER create fake footage."""
    root = Path(root).resolve()
    shots = visual.get("shots") if isinstance(visual, dict) else None
    if not isinstance(shots, list) or not shots:
        return {"status": "BLOCKED_REAL_MEDIA", "can_render": False,
                "gaps": [{"shot_id": None, "issues": ["No director visual shots supplied"],
                          "next_action": "Create a meaningful visual plan first."}],
                "review_approved": False}
    try:
        catalog = read_candidates(root).get("candidates", {})
    except (ValueError, OSError, TypeError, KeyError):
        catalog = {}
    gaps = []
    used = {}
    for number, shot in enumerate(shots, 1):
        if not isinstance(shot, dict):
            gaps.append({"shot_id": f"shot-{number}", "issues": ["Shot must be a JSON object"],
                         "next_action": "Write a director shot with a real asset."})
            continue
        sid = shot.get("id") or f"shot-{number}"
        kind = shot.get("media_type")
        issues = []
        if kind not in ALLOWED:
            issues.append("Unsupported/procedural media_type: " + str(kind) +
                          "; no SVG/Pillow/Canvas/data_motion or card-animation fallback")
        if not str(shot.get("visual_event", "")).strip() or not str(shot.get("cut_reason", "")).strip():
            issues.append("Missing specific visual event or reason for the cut")
        metadata = shot.get("source_provenance")
        if not isinstance(metadata, dict):
            issues.append("source_provenance declaration is required for every shot")
            metadata = {}
        origin = metadata.get("origin")
        if kind in ALLOWED and origin not in ALLOWED[kind]:
            issues.append("Media origin missing/incompatible with " + str(kind))
        for field in ("producer", "reference"):
            if not isinstance(metadata.get(field), str) or len(metadata[field].strip()) < 3:
                issues.append("source_provenance." + field + " must identify a concrete source")
        if metadata.get("rights_confirmed") is not True:
            issues.append("source_provenance.rights_confirmed must be explicitly true")
        record = None
        if kind == "gpt_gif":
            key = str(shot.get("source_shot_id", "")) + "/" + str(shot.get("candidate_id", ""))
            record = catalog.get(key)
            if not isinstance(record, dict):
                issues.append("Real registered GIF candidate missing: " + key)
            else:
                if record.get("prompt_delivery") != "explicit_tool_argument":
                    issues.append("GIF prompt delivery not verifiably explicit")
                if not all(isinstance(record.get(k), str) and record[k].strip()
                           for k in ("tool", "reference", "prompt", "prompt_sha256")):
                    issues.append("GIF catalog lacks actual tool/reference/prompt evidence")
                prompt = file_in_project(root, record.get("prompt"))
                if not prompt or sha256(prompt) != record.get("prompt_sha256"):
                    issues.append("GIF original prompt missing/changed")
                rel = record.get("file")
                expected_hash = record.get("sha256")
        else:
            rel = shot.get("source_file")
            expected_hash = shot.get("source_sha256")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            issues.append("Exact 64-character source SHA256 required")
        if metadata.get("source_sha256") != expected_hash:
            issues.append("Provenance is not bound to the exact source SHA256")
        source = file_in_project(root, rel)
        if source is None:
            issues.append("Original media file missing or outside project: " + str(rel))
        else:
            if sha256(source) != expected_hash:
                issues.append("Original media bytes changed or hash is incorrect")
            suffix = source.suffix.lower()
            if kind == "gpt_gif" and suffix != ".gif":
                issues.append("gpt_gif source is not a GIF file")
            elif kind in ("real_video", "screen_recording", "original_animation") and suffix not in VIDEO:
                issues.append("Actual footage must be a video file")
            elif kind == "screenshot" and suffix not in STILL:
                issues.append("Static evidence must be a supported bitmap image, not SVG")
            elif kind in ALLOWED:
                try:
                    if kind in ("real_video", "screen_recording", "original_animation"):
                        duration = probe_video(source)
                        start = shot.get("source_in_ms", 0)
                        begin, end = shot.get("start_ms"), shot.get("end_ms")
                        if all(type(x) is int for x in (start, begin, end)) and (
                            start < 0 or end <= begin or (start + end - begin) / 1000 > duration + .04
                        ):
                            issues.append("Footage too short for scene; cannot freeze/loop to fill")
                    else:
                        from PIL import Image
                        with Image.open(source) as frame:
                            frame.verify()
                        if kind == "gpt_gif":
                            with Image.open(source) as frame:
                                if frame.n_frames < 2:
                                    issues.append("GIF is static, no actual animated frames")
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    issues.append("Cannot decode original visual media: " + str(exc))
        if kind == "original_animation" and (
            not isinstance(metadata.get("model"), str) or
            not isinstance(metadata.get("prompt_sha256"), str) or
            not isinstance(metadata.get("request_id"), str) or
            not metadata["model"].strip() or len(metadata["prompt_sha256"]) != 64 or
            not metadata["request_id"].strip()
        ):
            issues.append("Model-generated video needs real model/request_id/prompt SHA evidence")
        if kind == "gpt_gif" and record and metadata.get("reference") != record.get("reference"):
            issues.append("GIF generation reference differs from source catalog")
        if kind == "screenshot" and shot.get("roll") != "B":
            issues.append("Still screenshots/photos cannot impersonate moving A-roll performances")
        if source is not None and isinstance(expected_hash, str) and len(expected_hash) == 64:
            marker = (expected_hash, shot.get("source_in_ms", 0))
            if marker in used:
                issues.append("Same source segment reused as " + str(used[marker]) +
                              "; use a genuinely different shot instead of filler")
            else:
                used[marker] = sid
        if issues:
            gaps.append({"shot_id": sid, "issues": issues,
                         "next_action": GAPS_HELP.get(kind, "Replace with a real filmed, captured or model-generated source.")})
    return {
        "status": "BLOCKED_REAL_MEDIA" if gaps else "REAL_MEDIA_STRUCTURALLY_READY",
        "can_render": not gaps,
        "gaps": gaps, "shot_count": len(shots),
        "review_approved": False,
        "limitations": ["Metadata and hashes do not prove authentic authorship, semantic accuracy or image quality.",
                        "A human/vision reviewer must actually watch/listen and approve the real film."]
    }


def require_media(root, visual):
    result = inspect_media(root, visual)
    if result["gaps"]:
        lines = [f"{item['shot_id']}: " + "; ".join(item["issues"]) for item in result["gaps"]]
        raise ValueError("Authentic-media preflight blocked; no fallback video will be made:\n" +
                         "\n".join(lines))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--visual-plan", help="Default: <project>/visual-plan.json")
    parser.add_argument("--report", help="Optional JSON report path")
    args = parser.parse_args()
    root = Path(args.project).resolve()
    path = Path(args.visual_plan) if args.visual_plan else root / "visual-plan.json"
    visual = json.loads(path.read_text(encoding="utf-8"))
    result = inspect_media(root, visual)
    if args.report:
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(not result["can_render"])


if __name__ == "__main__":
    main()
