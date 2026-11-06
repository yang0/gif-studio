#!/usr/bin/env python3
"""GIF technical QA: decode, durations, difference metrics and contact sheet."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageSequence, ImageStat


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def difference(a, b):
    a = a.resize((64, 64)).convert("RGB")
    b = b.resize((64, 64)).convert("RGB")
    return round(sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / (255 * 3), 5)


def inspect(path, expected, tolerance, contact_sheet=None):
    p = Path(path)
    issues, warnings = [], []
    if not p.is_file():
        return {"file": str(p), "pass": False, "issues": ["File missing"]}
    try:
        with Image.open(p) as im:
            if im.format != "GIF":
                issues.append("Not a GIF")
            frames = [f.convert("RGB") for f in ImageSequence.Iterator(im)]
            delays = [int(f.info.get("duration", im.info.get("duration", 100)))
                      for f in ImageSequence.Iterator(im)]
            width, height = im.size
            duration = sum(delays) / 1000
            if len(frames) < 4:
                issues.append("Less than 4 frames")
            if width < 1 or height < 1:
                issues.append("Invalid dimensions")
            if any(d <= 0 for d in delays):
                warnings.append("Zero-delay frames detected")
            if abs(width / height - 9 / 16) > .07:
                warnings.append("Not 9:16; compositor will letterbox")
            if abs(duration - expected) > tolerance:
                warnings.append("GIF duration differs from requested shot duration")
            if "loop" not in im.info:
                warnings.append("No looping metadata; looping is not assumed")
            deltas = [difference(a, b) for a, b in zip(frames, frames[1:])]
            seam = difference(frames[-1], frames[0]) if len(frames) > 1 else 0
            if max(deltas, default=0) > 0.7:
                warnings.append("Large adjacent frame jump; inspect contact sheet")
            if max(deltas, default=0) < .002:
                warnings.append("Almost no visible motion")
            if seam > .15:
                warnings.append("Large final-to-first seam; use hold instead of loop")
            if contact_sheet and frames:
                sheet_path = Path(contact_sheet)
                sheet_path.parent.mkdir(parents=True, exist_ok=True)
                count = min(8, len(frames))
                indexes = sorted(set(round(i * (len(frames)-1) / max(count-1, 1))
                                     for i in range(count)))
                thumb_w, thumb_h = 220, 220
                panel_w = thumb_w + 12
                panel_h = thumb_h + 38
                columns = min(4, len(indexes))
                rows = (len(indexes) + columns - 1) // columns
                sheet = Image.new("RGB", (columns * panel_w, rows * panel_h), "white")
                draw = ImageDraw.Draw(sheet)
                for n, idx in enumerate(indexes):
                    frame = ImageOps.contain(frames[idx], (thumb_w, thumb_h))
                    x, y = (n % columns) * panel_w, (n // columns) * panel_h
                    sheet.paste(frame, (x + (thumb_w-frame.width)//2, y))
                    draw.text((x+6, y+thumb_h+4), f"frame {idx+1}/{len(frames)}", fill="black")
                sheet.save(sheet_path, quality=88)
            return {"file": str(p.resolve()), "source_sha256": digest(p),
                    "pass": not issues, "issues": issues, "warnings": warnings,
                    "width": width, "height": height, "frames": len(frames),
                    "duration_sec": round(duration, 3),
                    "loop": im.info.get("loop"),
                    "mean_adjacent_difference": round(sum(deltas)/max(1,len(deltas)), 5),
                    "max_adjacent_difference": round(max(deltas, default=0), 5),
                    "loop_seam_difference": seam,
                    "contact_sheet": str(Path(contact_sheet).resolve()) if contact_sheet else None}
    except Exception as exc:
        return {"file": str(p), "pass": False, "issues": [str(exc)]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gif", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--duration", type=float, default=5)
    p.add_argument("--tolerance", type=float, default=1.5)
    p.add_argument("--contact-sheet")
    a = p.parse_args()
    result = inspect(a.gif, a.duration, a.tolerance, a.contact_sheet)
    dest = Path(a.report)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
