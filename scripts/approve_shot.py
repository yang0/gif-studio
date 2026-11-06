#!/usr/bin/env python3
"""Record an explicit human/agent visual review bound to the exact GIF bytes."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from inspect_gif import digest


def approve(project, shot, reviewer, notes):
    project = Path(project)
    source = project / "gifs" / (shot + ".gif")
    tech = project / "qa" / (shot + ".json")
    if not source.is_file() or not tech.is_file():
        raise FileNotFoundError("GIF and technical QA report are required")
    report = json.loads(tech.read_text(encoding="utf-8"))
    sha = digest(source)
    if not report.get("pass") or report.get("source_sha256") != sha:
        raise ValueError("Technical QA failed or is stale; rerun inspect_gif.py")
    if not reviewer.strip() or not notes.strip():
        raise ValueError("Reviewer and review notes must be nonempty")
    record = {"approved": True, "source_sha256": sha,
              "reviewer": reviewer, "notes": notes,
              "reviewed_at": datetime.now(timezone.utc).isoformat()}
    output = project / "qa" / (shot + ".visual.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2)+"\n",
                      encoding="utf-8")
    return record


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--shot", required=True)
    p.add_argument("--reviewer", required=True)
    p.add_argument("--notes", required=True)
    a = p.parse_args()
    if not a.shot.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid shot name")
    print(json.dumps(approve(a.project, a.shot, a.reviewer, a.notes),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
