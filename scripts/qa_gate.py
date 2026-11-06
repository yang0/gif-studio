"""Quality gate for actual files, QA reports and production declarations."""
import json
from pathlib import Path
from inspect_gif import digest
from production_contract import asset_status, load_manifest, fingerprint, load_contract

def shot_quality(project, shot_id, storyboard=None):
    project = Path(project)
    gif = project/"gifs"/(shot_id+".gif")
    tech = project/"qa"/(shot_id+".json")
    visual = project/"qa"/(shot_id+".visual.json")
    if not gif.is_file():
        return "missing", "GIF missing"
    sha = digest(gif)
    attempts = project/"qa"/(shot_id+".attempts.json")
    if attempts.is_file():
        try:
            history=json.loads(attempts.read_text(encoding="utf-8"))
            failures=history.get("failures", [])
            if storyboard is not None:
                director, _, _ = load_contract(project, storyboard)
                active_shot = next(x for x in director["shots"] if x["id"]==shot_id)
                if history.get("director_fingerprint") != fingerprint(active_shot):
                    failures = []
            if len(failures)>=2:
                return "blocked_replan", "Two visual attempts failed; revise director plan"
            if any(x.get("gif_sha256")==sha for x in failures):
                return "rejected", "Current GIF failed visual inspection"
        except (ValueError,OSError):
            return "rejected", "Invalid failed-attempt record"
    if storyboard is not None:
        status, message = asset_status(project, storyboard, shot_id)
        if status != "registered":
            return status, message
    if not tech.is_file():
        return "generated", "Technical QA missing"
    try:
        report = json.loads(tech.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return "generated", "Technical QA corrupt"
    if not report.get("pass") or report.get("source_sha256") != sha:
        return "generated", "Technical QA failed or stale"
    if not visual.is_file():
        return "technical_passed", "Visual review missing"
    try:
        review = json.loads(visual.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return "technical_passed", "Visual review corrupt"
    if not review.get("approved") or review.get("source_sha256") != sha:
        return "technical_passed", "Visual review failed or stale"
    if storyboard is not None:
        record = load_manifest(project)["assets"].get(shot_id, {})
        if review.get("asset_fingerprint") != fingerprint(record):
            return "technical_passed", "Visual review predates production registration"
        tests = review.get("visual_checks", {})
        for key in ("semantic", "motion", "style", "composition"):
            if tests.get(key) is not True:
                return "technical_passed", "Missing explicit visual check: "+key
        sheet = report.get("contact_sheet")
        if not sheet or not Path(sheet).is_file():
            return "technical_passed", "Contact sheet missing"
        if review.get("contact_sheet_sha256") != digest(sheet):
            return "technical_passed", "Reviewed contact sheet differs from current sheet"
        if not review.get("reviewer") or not review.get("notes"):
            return "technical_passed", "Review notes missing"
    return "ready", "Asset and required reviews ready"
