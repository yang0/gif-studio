"""Trace GIFs to approved shot, director plan and style.

Provenance is an operator declaration, NOT verified proof of an external model call.
"""
import hashlib
import json
from pathlib import Path
from director_plan import validate_director
from inspect_gif import digest

ALLOWED_KINDS = {"gpt_gif", "programmatic", "intentional_reuse"}
POLICY_BY_KIND = {
    "gpt_gif": "new_gpt_gif",
    "programmatic": "programmatic",
    "intentional_reuse": "intentional_reuse",
}

def fingerprint(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def load_contract(project, storyboard):
    project = Path(project)
    director_path, style_path = project/"director-plan.json", project/"style-lock.json"
    if not director_path.is_file():
        raise FileNotFoundError("Missing director-plan.json")
    if not style_path.is_file():
        raise FileNotFoundError("Missing style-lock.json")
    plan = json.loads(director_path.read_text(encoding="utf-8"))
    problems, _ = validate_director(plan, storyboard)
    if problems:
        raise ValueError("Invalid director plan: " + "; ".join(problems))
    style = json.loads(style_path.read_text(encoding="utf-8"))
    if not isinstance(style, dict) or not style.get("style_id"):
        raise ValueError("Invalid style lock")
    return plan, style, digest(style_path)

def manifest_path(project):
    return Path(project)/"production"/"assets.json"

def load_manifest(project):
    path = manifest_path(project)
    if not path.is_file():
        return {"version":1,"assets":{}}
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("version") != 1 or not isinstance(result.get("assets"), dict):
        raise ValueError("Invalid production assets manifest")
    return result

def register(project, storyboard, shot_id, kind, tool_identity, reference, prompt_path=None):
    project = Path(project)
    if kind not in ALLOWED_KINDS:
        raise ValueError("Unknown asset kind")
    board_shot = next((s for s in storyboard["shots"] if s["id"] == shot_id), None)
    if board_shot is None:
        raise ValueError("Shot not in storyboard")
    plan, _, style_hash = load_contract(project, storyboard)
    director_shot = next(s for s in plan["shots"] if s["id"] == shot_id)
    if director_shot["asset_policy"] != POLICY_BY_KIND[kind]:
        raise ValueError("Asset kind does not match director policy")
    if not tool_identity.strip() or not reference.strip():
        raise ValueError("Actual tool identity and production reference required")
    source = project/"gifs"/(shot_id+".gif")
    if not source.is_file():
        raise FileNotFoundError(source)
    if kind == "intentional_reuse":
        origin = director_shot["reuse_source_id"]
        original = project/"gifs"/(origin+".gif")
        if not original.is_file() or digest(original) != digest(source):
            raise ValueError("Reused GIF must byte-match declared source")
    prompt_hash = None
    if prompt_path:
        prompt_path = Path(prompt_path).resolve()
        if not prompt_path.is_file():
            raise FileNotFoundError(prompt_path)
        prompt_hash = digest(prompt_path)
    if kind == "gpt_gif" and not prompt_hash:
        raise ValueError("GPT GIF requires saved exact generation prompt")
    record = {"kind":kind,"source_sha256":digest(source),
              "tool_identity":tool_identity,"production_reference":reference,
              "prompt_sha256":prompt_hash,
              "prompt_path":str(prompt_path) if prompt_path else None,
              "shot_fingerprint":fingerprint(board_shot),
              "director_fingerprint":fingerprint(director_shot),
              "style_sha256":style_hash}
    manifest = load_manifest(project)
    manifest["assets"][shot_id] = record
    path = manifest_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return record

def asset_status(project, storyboard, shot_id):
    project = Path(project)
    source = project/"gifs"/(shot_id+".gif")
    if not source.is_file():
        return "missing", "GIF missing"
    try:
        plan, _, style_hash = load_contract(project, storyboard)
        record = load_manifest(project)["assets"].get(shot_id)
        if record is None:
            return "unregistered", "Missing provenance record"
        board_shot = next(s for s in storyboard["shots"] if s["id"] == shot_id)
        director_shot = next(s for s in plan["shots"] if s["id"] == shot_id)
        if record.get("kind") not in ALLOWED_KINDS:
            return "stale", "Unknown asset kind"
        if director_shot["asset_policy"] != POLICY_BY_KIND[record["kind"]]:
            return "stale", "Asset kind conflicts with director plan"
        for field, expected in (
            ("source_sha256", digest(source)),
            ("shot_fingerprint", fingerprint(board_shot)),
            ("director_fingerprint", fingerprint(director_shot)),
            ("style_sha256", style_hash),
        ):
            if record.get(field) != expected:
                return "stale", field+" changed after production"
        if not record.get("tool_identity") or not record.get("production_reference"):
            return "stale", "Missing production tool or reference"
        if record["kind"] == "gpt_gif" and not record.get("prompt_sha256"):
            return "stale", "Generation prompt missing"
        if record.get("prompt_sha256"):
            prompt = record.get("prompt_path")
            if not prompt or not Path(prompt).is_file() or digest(prompt) != record["prompt_sha256"]:
                return "stale", "Generation prompt missing or changed"
        if record["kind"] == "intentional_reuse":
            origin = director_shot.get("reuse_source_id")
            original = project/"gifs"/(str(origin)+".gif")
            if not original.is_file() or digest(original) != digest(source):
                return "stale", "Reused asset no longer matches source"
        return "registered", "Provenance matches GIF, shot, director and style"
    except (FileNotFoundError, ValueError, KeyError, StopIteration, TypeError) as exc:
        return "stale", str(exc)

def production_preflight(project, storyboard, gpt_only=True):
    issues, hashes = [], {}
    if gpt_only:
        try:
            plan, _, _ = load_contract(project, storyboard)
            manifest = load_manifest(project)
            directors = {x["id"]: x for x in plan["shots"]}
        except (FileNotFoundError, ValueError, KeyError) as exc:
            return ["Missing GPT-only production contract: " + str(exc)]
    for shot in storyboard["shots"]:
        sid = shot["id"]
        if gpt_only:
            kind = manifest["assets"].get(sid, {}).get("kind")
            policy = directors[sid].get("asset_policy")
            if kind == "programmatic" or policy == "programmatic":
                issues.append(f"{sid}: GPT-only mode forbids programmatic/vector substitutes")
            elif kind == "intentional_reuse":
                origin = directors[sid].get("reuse_source_id")
                if manifest["assets"].get(origin, {}).get("kind") != "gpt_gif":
                    issues.append(f"{sid}: reused source is not GPT GIF")
            elif kind != "gpt_gif":
                issues.append(f"{sid}: GPT-only mode requires GPT GIF source")
        status, reason = asset_status(project, storyboard, sid)
        if status != "registered":
            issues.append(f"{sid}: {status}: {reason}")
        src = Path(project)/"gifs"/(sid+".gif")
        if src.is_file():
            hashes.setdefault(digest(src), []).append(sid)
    if any(len(ids) > 1 for ids in hashes.values()):
        try:
            plan, _, _ = load_contract(project, storyboard)
            by_id = {s["id"]: s for s in plan["shots"]}
            for ids in hashes.values():
                for idx, sid in enumerate(ids[1:], 1):
                    shot = by_id[sid]
                    if (shot.get("asset_policy") != "intentional_reuse" or
                        shot.get("reuse_source_id") not in ids[:idx]):
                        issues.append("Duplicate GIF bytes without justified reuse: "+", ".join(ids))
        except (FileNotFoundError, ValueError, KeyError) as exc:
            issues.append(str(exc))
    return issues
