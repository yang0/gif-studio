#!/usr/bin/env python3
"""Generate one subtitle cue per storyboard shot (not word-level alignment)."""
import argparse
import json
from pathlib import Path


def stamp(sec):
    ms = round(sec * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def render(data):
    lines, t = [], 0.0
    for idx, shot in enumerate(data["shots"], 1):
        duration = float(shot["duration_sec"])
        if duration <= 0:
            raise ValueError("duration_sec must be positive")
        subtitle = str(shot.get("subtitle") or shot.get("narration") or "").strip()
        if subtitle:
            lines.extend([str(idx), f"{stamp(t)} --> {stamp(t+duration)}", subtitle, ""])
        t += duration
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--storyboard", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    data = json.loads(Path(a.storyboard).read_text(encoding="utf-8"))
    dest = Path(a.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render(data), encoding="utf-8")


if __name__ == "__main__":
    main()
