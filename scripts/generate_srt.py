#!/usr/bin/env python3
"""SRT: storyboard-level cues or optional relative timestamped per-shot cues."""
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
    lines, t, index = [], 0.0, 0
    for shot in data["shots"]:
        duration = float(shot["duration_sec"])
        if duration <= 0:
            raise ValueError("duration_sec must be positive")
        cues = shot.get("subtitle_cues")
        if cues is None:
            cues = [{"start_sec":0, "end_sec":duration,
                     "text":shot.get("subtitle") or shot.get("narration") or ""}]
        for cue in cues:
            start, end = float(cue["start_sec"]), float(cue["end_sec"])
            if not (0 <= start < end <= duration + 1e-7):
                raise ValueError("Cue timestamps must be within shot bounds")
            text = str(cue.get("text", "")).strip()
            if text:
                index += 1
                lines.extend([str(index), f"{stamp(t+start)} --> {stamp(t+end)}", text, ""])
        t += duration
    return "\n".join(lines)+"\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--storyboard", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    dest = Path(a.output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render(json.loads(Path(a.storyboard).read_text(encoding="utf-8"))),
                    encoding="utf-8")


if __name__ == "__main__":
    main()
