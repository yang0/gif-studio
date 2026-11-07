#!/usr/bin/env python3
"""Fail-closed golden sample acceptance: real files, hashes and explicit reviews.

This script checks documented evidence, NOT whether a film looks good or
whether a declaration is truthful. No approval is ever generated here.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

REQUIRED = ("actual_mp4", "real_voice_review", "actual_human_review")
BLOCKING = ("knowledge_error", "provenance_misrepresentation", "severe_av_desync")
WEIGHTS = {"content": 25, "visual": 25, "pacing": 20, "audio": 15, "continuity": 15}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def probe(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format",
         "-of", "json", str(path)],
        check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(result.stdout)


def check(root):
    root = Path(root)
    acceptance = json.loads((root / "acceptance.json").read_text(encoding="utf-8"))
    problems = []
    if acceptance.get("status") == "AWAITING_REAL_GOLDEN_SAMPLE":
        problems.append("acceptance status still awaiting real sample")
    if acceptance.get("release_approved") is not True:
        problems.append("independent final release not approved")
    for field in REQUIRED:
        if not acceptance.get(field):
            problems.append("missing documented evidence: " + field)
    movie = acceptance.get("actual_mp4")
    if movie:
        path = (root / movie).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            problems.append("MP4 must exist inside sample directory")
        else:
            expected = acceptance.get("actual_mp4_sha256")
            if not expected or digest(path) != expected:
                problems.append("MP4 source SHA256 absent or mismatched")
            try:
                data = probe(path)
                streams = data.get("streams", [])
                kinds = {s.get("codec_type") for s in streams}
                duration = float(data.get("format", {}).get("duration", 0))
                low, high = acceptance.get("target_seconds", [20, 30])
                if not {"audio", "video"}.issubset(kinds):
                    problems.append("real MP4 must contain audio and video")
                if not low <= duration <= high:
                    problems.append("real MP4 duration outside target range")
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                problems.append("cannot probe movie: " + str(exc))
    review = acceptance.get("actual_human_review")
    if review:
        path = (root / review).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            problems.append("missing human review evidence file")
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
            scores = data.get("scores", {})
            if not isinstance(scores, dict) or set(scores) != set(WEIGHTS) or any(
                type(x) not in (int, float) or not 0 <= x <= 10 for x in scores.values()
            ):
                problems.append("five human scores missing or invalid")
            else:
                weighted = sum(scores[k] * weight for k, weight in WEIGHTS.items()) / 10
                if weighted < 80 or min(scores.values()) < 6:
                    problems.append("human score below publishing threshold")
            findings = data.get("blocking_findings")
            if not isinstance(findings, dict) or set(findings) != set(BLOCKING) or any(
                type(x) is not bool for x in findings.values()
            ) or any(findings.values()):
                problems.append("blocking human findings missing or present")
            if data.get("watched_entire_video") is not True:
                problems.append("full movie watch/listen declaration missing")
            if movie and data.get("video_sha256") != acceptance.get("actual_mp4_sha256"):
                problems.append("review refers to different movie")
    voice = acceptance.get("real_voice_review")
    if voice:
        path = (root / voice).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            problems.append("missing real voice review evidence file")
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not (data.get("listened_entire_audio") is True and
                    data.get("natural_chinese_approved") is True):
                problems.append("natural Chinese narration not approved")
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, default=Path("examples/focus-notification-v31"))
    args = parser.parse_args()
    problems = check(args.sample)
    print(json.dumps({"eligible": not problems, "problems": problems},
                     ensure_ascii=False, indent=2))
    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
