#!/usr/bin/env python3
"""Validate visual storytelling decisions before expensive GIF generation."""
import argparse
import json
from pathlib import Path

POLICIES = {"new_gpt_gif", "intentional_reuse", "programmatic"}
REQUIRED = ("id", "spoken_point", "visual_proof", "start_state", "change_event",
            "end_state", "composition", "entry_transition", "exit_transition",
            "source_anchor", "asset_policy")

def validate_director(plan, storyboard):
    issues, warnings = [], []
    shots = plan.get("shots") if isinstance(plan, dict) else None
    expected = storyboard.get("shots", [])
    if not isinstance(shots, list) or not shots:
        return ["Director plan needs a nonempty shots array"], []
    if plan.get("version") != 1:
        issues.append("Director plan version must be 1")
    if not isinstance(plan.get("creative_thesis"), str) or not plan["creative_thesis"].strip():
        issues.append("creative_thesis must describe the overarching visual story")
    board_ids = [s["id"] for s in expected]
    actual_ids = [s.get("id") for s in shots if isinstance(s, dict)]
    if board_ids != actual_ids:
        issues.append("Director shot order/IDs must exactly match storyboard")
    for i, shot in enumerate(shots):
        if not isinstance(shot, dict):
            issues.append(f"Shot {i+1}: must be object")
            continue
        sid = str(shot.get("id", i+1))
        for key in REQUIRED:
            if not isinstance(shot.get(key), str) or not shot[key].strip():
                issues.append(f"{sid}: missing {key}")
        policy = shot.get("asset_policy")
        if policy not in POLICIES:
            issues.append(f"{sid}: unknown asset_policy {policy}")
        if policy == "new_gpt_gif":
            must = shot.get("must_show")
            avoid = shot.get("must_not_show")
            if not isinstance(must, list) or len(must) < 2 or any(
                    not isinstance(v, str) or not v.strip() for v in must):
                issues.append(f"{sid}: new_gpt_gif needs >=2 concrete must_show elements/events")
            if not isinstance(avoid, list) or any(not isinstance(v,str) for v in avoid):
                issues.append(f"{sid}: must_not_show must be explicit list")
        if policy == "intentional_reuse":
            if not shot.get("reuse_source_id") or not shot.get("reuse_justification"):
                issues.append(f"{sid}: intentional reuse requires source ID and justification")
            if shot.get("reuse_source_id") == sid:
                issues.append(f"{sid}: cannot reuse itself")
        if policy == "programmatic" and not shot.get("programmatic_reason"):
            issues.append(f"{sid}: programmatic footage requires an explicit reason")
        if i < len(expected):
            narration = expected[i].get("narration", "")
            anchor = shot.get("source_anchor", "")
            if anchor and anchor not in narration:
                issues.append(f"{sid}: source_anchor not found verbatim in shot narration")
        if len(str(shot.get("change_event", ""))) < 12:
            warnings.append(f"{sid}: change_event may be too vague to animate")
        if shot.get("composition", "").strip().lower() in ("fixed card layout", "template"):
            issues.append(f"{sid}: generic fixed template is not an acceptable composition")
    if len(shots) >= 3:
        if len(set(s.get("composition", "") for s in shots)) == 1:
            warnings.append("Every shot uses exactly the same composition")
        if len(set(s.get("change_event", "") for s in shots)) == 1:
            warnings.append("Every shot has identical motion choreography")
    return issues, warnings

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--director", required=True)
    parser.add_argument("--storyboard", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()
    plan = json.loads(Path(args.director).read_text(encoding="utf-8"))
    board = json.loads(Path(args.storyboard).read_text(encoding="utf-8"))
    issues, warnings = validate_director(plan, board)
    report = {"pass": not issues, "issues": issues, "warnings": warnings}
    if args.report:
        output = Path(args.report)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not issues else 1)

if __name__ == "__main__":
    main()
