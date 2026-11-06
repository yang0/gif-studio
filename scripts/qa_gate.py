"""Shared SHA-bound quality gate for composition and status reporting."""
import json
from pathlib import Path
from inspect_gif import digest


def shot_quality(project, shot_id):
    project = Path(project)
    gif = project / "gifs" / (shot_id + ".gif")
    tech = project / "qa" / (shot_id + ".json")
    visual = project / "qa" / (shot_id + ".visual.json")
    if not gif.is_file():
        return "missing", "GIF missing"
    sha = digest(gif)
    if not tech.is_file():
        return "generated", "Technical QA missing"
    try:
        report = json.loads(tech.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return "generated", "Technical QA corrupt"
    if not report.get("pass") or report.get("source_sha256") != sha:
        return "generated", "Technical QA failed or stale"
    if not visual.is_file():
        return "technical_passed", "Visual approval missing"
    try:
        review = json.loads(visual.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return "technical_passed", "Visual approval corrupt"
    if not review.get("approved") or review.get("source_sha256") != sha:
        return "technical_passed", "Visual approval failed or stale"
    return "ready", "Ready to compose"
