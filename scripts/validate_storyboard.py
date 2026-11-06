#!/usr/bin/env python3
"""Validate storyboard before consuming GIF assets. No external JSON-schema dependency."""
import argparse
import json
import re
from pathlib import Path

MODES = {"visual_metaphor", "structure_relation", "mechanism_breakdown",
         "compare_contrast", "data_motion"}


def validate(data):
    issues = []
    if not isinstance(data, dict):
        return ["Root must be a JSON object"]
    for key in ("project_title", "width", "height", "fps", "shots"):
        if key not in data:
            issues.append(f"Missing {key}")
    for key in ("width", "height", "fps"):
        value = data.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            issues.append(f"{key} must be a positive integer")
    shots = data.get("shots")
    if not isinstance(shots, list) or not shots:
        return issues + ["shots must be a non-empty list"]
    seen = set()
    for idx, shot in enumerate(shots, 1):
        if not isinstance(shot, dict):
            issues.append(f"shot {idx} must be object")
            continue
        name = shot.get("id")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            issues.append(f"shot {idx}: id must use only letters, digits, - and _")
        elif name in seen:
            issues.append(f"shot {idx}: duplicate id {name}")
        else:
            seen.add(name)
        duration = shot.get("duration_sec")
        if isinstance(duration, bool) or not isinstance(duration, (float, int)) or duration <= 0:
            issues.append(f"shot {idx}: duration_sec must be > 0")
        if not isinstance(shot.get("narration", ""), str):
            issues.append(f"shot {idx}: narration must be string")
        if not isinstance(shot.get("visual_goal"), str) or not shot["visual_goal"].strip():
            issues.append(f"shot {idx}: visual_goal missing")
        if shot.get("visual_mode") not in MODES:
            issues.append(f"shot {idx}: unsupported visual_mode")
        cues = shot.get("subtitle_cues")
        if cues is not None:
            if not isinstance(cues, list):
                issues.append(f"shot {idx}: subtitle_cues must be list")
            else:
                for j, cue in enumerate(cues, 1):
                    if not isinstance(cue, dict):
                        issues.append(f"shot {idx} cue {j}: must be object")
                        continue
                    a, b = cue.get("start_sec"), cue.get("end_sec")
                    if any(isinstance(x, bool) or not isinstance(x, (int, float)) for x in (a,b)):
                        issues.append(f"shot {idx} cue {j}: timestamps must be numeric")
                    elif isinstance(duration, (int, float)) and not (0 <= a < b <= duration):
                        issues.append(f"shot {idx} cue {j}: timestamps out of bounds")
                    if not isinstance(cue.get("text"), str):
                        issues.append(f"shot {idx} cue {j}: text must be string")
        if not isinstance(shot.get("motion_plan"), list) or not shot["motion_plan"]:
            issues.append(f"shot {idx}: motion_plan must be nonempty list")
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--storyboard", required=True)
    ap.add_argument("--report")
    args = ap.parse_args()
    data = json.loads(Path(args.storyboard).read_text(encoding="utf-8"))
    issues = validate(data)
    result = {"pass": not issues, "issues": issues, "shots": len(data.get("shots", []))}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.report:
        dest = Path(args.report)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(1 if issues else 0)


if __name__ == "__main__":
    main()
