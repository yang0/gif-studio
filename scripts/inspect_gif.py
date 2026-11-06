#!/usr/bin/env python3
"""Check GIF metadata and simple inter-frame image differences. Visual semantic QA is separate."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageStat, ImageSequence


def inspect(path, expected, tolerance):
    p = Path(path)
    issues = []
    warnings = []
    if not p.is_file():
        return {"file": str(p), "pass": False, "issues": ["File missing"]}
    try:
        with Image.open(p) as im:
            if im.format != "GIF":
                issues.append("Not GIF format")
            frames = []
            delays = []
            for frame in ImageSequence.Iterator(im):
                frames.append(frame.convert("RGB"))
                delays.append(int(frame.info.get("duration", im.info.get("duration", 100))))
            width, height = im.size
            duration = sum(delays) / 1000
            loop = im.info.get("loop")
            if len(frames) < 4:
                issues.append("Less than 4 frames")
            if not (width > 0 and height > 0):
                issues.append("Invalid dimensions")
            if abs(width / height - 9 / 16) > 0.07:
                warnings.append("Aspect ratio not close to 9:16; compositor will letterbox")
            if abs(duration - expected) > tolerance:
                warnings.append("GIF duration differs from target; compositor will loop/trim")
            if loop is None:
                warnings.append("No loop metadata")
            diffs = []
            for a, b in zip(frames, frames[1:]):
                small_a = a.resize((64, 64))
                small_b = b.resize((64, 64))
                d = ImageChops.difference(small_a, small_b)
                diffs.append(sum(ImageStat.Stat(d).mean) / (3 * 255))
            if diffs and max(diffs) > 0.7:
                warnings.append("Large frame-to-frame jump; review visually")
            if diffs and max(diffs) < 0.002:
                warnings.append("Almost no visible motion")
            report = {"file": str(p.resolve()), "pass": not issues, "issues": issues,
                      "warnings": warnings, "width": width, "height": height,
                      "frames": len(frames), "duration_sec": round(duration, 3),
                      "loop": loop, "mean_adjacent_difference": round(sum(diffs)/max(len(diffs),1),4),
                      "max_adjacent_difference": round(max(diffs,default=0),4)}
            return report
    except Exception as exc:
        return {"file": str(p), "pass": False, "issues": [str(exc)]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gif", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--duration", type=float, default=5)
    ap.add_argument("--tolerance", type=float, default=1.5)
    a = ap.parse_args()
    report = inspect(a.gif, a.duration, a.tolerance)
    dest = Path(a.report)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
