#!/usr/bin/env python3
"""Run a WHOLE-script TTS provider and an acoustic alignment provider.

Providers are explicitly configured argv commands (no shell). An actual
forced aligner must output the same timestamp schema as audio_timeline.py.
A synthetic/test provider is not production evidence. Audio and alignment
are recorded independently so failed alignment can be retried without TTS.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from audit_script import audit
from audio_timeline import sha256, probe_ms, validate as validate_alignment

def load_config(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version")!=1:
        raise ValueError("Voice provider config version must be 1")
    for stage in ("tts","alignment"):
        entry=data.get(stage)
        if entry is None:
            continue
        if not isinstance(entry,dict) or not entry.get("name") or not isinstance(entry.get("argv"),list):
            raise ValueError(f"{stage}: provider name and argv array required")
        argv=entry["argv"]
        if not argv or not all(isinstance(s,str) and s.strip() for s in argv):
            raise ValueError(f"{stage}: argv entries must be nonempty strings")
        if any(("{"+key+"}") in s for s in argv for key in ("api_key","token","password")):
            raise ValueError("Keep credentials in environment variables, not argv")
    return data

def execute(provider,values,stage):
    if not provider:
        raise ValueError(f"{stage}: no provider configured")
    values={**values,"python":sys.executable,"skill_dir":str(Path(__file__).resolve().parent)}
    try:
        argv=[value.format_map(values) for value in provider["argv"]]
    except KeyError as exc:
        raise ValueError(f"{stage}: unknown command placeholder {exc}") from exc
    timeout=provider.get("timeout_seconds",600)
    if type(timeout) is not int or timeout<1 or timeout>3600:
        raise ValueError(f"{stage}: invalid timeout")
    try:
        subprocess.run(argv,check=True,timeout=timeout,stdin=subprocess.DEVNULL,
                       capture_output=True,text=True,errors="replace")
    except subprocess.CalledProcessError as exc:
        # Provider output can contain secrets. Do not echo it to caller/log.
        raise RuntimeError(f"{stage}: provider returned exit code {exc.returncode}; inspect provider's secure local logs") from None
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{stage}: provider timed out after {timeout}s") from None

def write_json_atomic(path,obj):
    dest=Path(path)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("w",encoding="utf-8",dir=dest.parent,
                                     prefix=".voice-",suffix=".json",delete=False) as tmp:
        json.dump(obj,tmp,ensure_ascii=False,indent=2)
        tmp.write("\n")
        name=tmp.name
    os.replace(name,dest)

def run(project, providers, *, reuse_audio=False):
    root=Path(project).resolve()
    script_file=root/"script.json"
    script=json.loads(script_file.read_text(encoding="utf-8"))
    reviewed=audit(script)
    if not reviewed["pass"]:
        raise ValueError("Locked narration script failed audit: "+"; ".join(reviewed["issues"]))
    text=reviewed["narration"]
    script_hash=sha256(script_file)
    audio=root/"audio"/"voiceover.wav"
    timeline=root/"audio-timeline.json"
    metadata=root/"audio"/"voice-production.json"
    fulltext=root/"audio"/"voiceover-fulltext.txt"
    audio.parent.mkdir(parents=True,exist_ok=True)
    if metadata.exists():
        prior=json.loads(metadata.read_text(encoding="utf-8"))
        if prior.get("script_sha256")!=script_hash:
            raise ValueError("Script changed after prior voice production. Archive old outputs and explicitly start a new project revision.")
    if reuse_audio:
        if not audio.exists():
            raise FileNotFoundError("Cannot reuse audio that does not exist")
        if metadata.exists() and json.loads(metadata.read_text(encoding="utf-8")).get("audio_sha256")!=sha256(audio):
            raise ValueError("Audio changed since prior generation metadata")
    else:
        if audio.exists():
            raise FileExistsError("Existing full-track narration; use --reuse-audio instead of silently overwriting")
        if not providers.get("tts"):
            raise ValueError("No actual TTS provider configured. Supply an audio file manually and use --reuse-audio.")
        with tempfile.TemporaryDirectory(prefix="gif-studio-voice-") as temp:
            tempdir=Path(temp)
            text_file=tempdir/"fulltext.txt"
            output=tempdir/"narration.wav"
            text_file.write_text(text,encoding="utf-8")
            execute(providers["tts"],{"text_file":str(text_file),"audio_out":str(output),
                                     "script_file":str(script_file),"project":str(root)},"TTS")
            if not output.is_file():
                raise ValueError("TTS provider did not create a real audio file")
            duration=probe_ms(output)
            if duration<300:
                raise ValueError("TTS provider returned implausibly short audio")
            # No destructive overwrite, even if a second process raced us.
            with audio.open("xb") as dest, output.open("rb") as src:
                import shutil
                shutil.copyfileobj(src,dest)
    duration=probe_ms(audio)
    audio_hash=sha256(audio)
    if metadata.exists():
        previous=json.loads(metadata.read_text(encoding="utf-8"))
        if previous.get("audio_sha256")!=audio_hash:
            raise ValueError("Audio no longer matches prior production record")
    else:
        write_json_atomic(metadata,{"version":1,"script_sha256":script_hash,
            "audio_sha256":audio_hash,"duration_ms":duration,
            "tts_provider":providers.get("tts",{}).get("name") if not reuse_audio else "external_existing_audio",
            "alignment_status":"pending","verified_voice_quality":False})
    # This is the single full script passed to both providers. No split-by-sentence TTS.
    if fulltext.exists() and fulltext.read_text(encoding="utf-8")!=text:
        raise ValueError("Full narration text file differs from locked script")
    fulltext.write_text(text,encoding="utf-8")
    if timeline.exists():
        current=json.loads(timeline.read_text(encoding="utf-8"))
        issues=validate_alignment(current,script,audio)
        if issues:
            raise ValueError("Existing alignment is stale: "+"; ".join(issues))
        return {"status":"already_aligned","audio_sha256":audio_hash,
                "duration_ms":duration,"segments":len(current["segments"])}
    if not providers.get("alignment"):
        return {"status":"audio_ready_alignment_required","audio_sha256":audio_hash,
                "duration_ms":duration,
                "note":"No forced aligner configured. Provide actual manual-verified timeline or an aligner; timestamps not fabricated."}
    with tempfile.TemporaryDirectory(prefix="gif-studio-align-") as temp:
        result=Path(temp)/"alignment.json"
        execute(providers["alignment"],{"text_file":str(fulltext),
                 "audio_file":str(audio),"timeline_out":str(result),
                 "script_file":str(script_file),"project":str(root)},"alignment")
        if not result.is_file():
            raise ValueError("Aligner did not return a timeline")
        alignment=json.loads(result.read_text(encoding="utf-8"))
        # Enforce provider-generated traceability and prevent claim of manual review.
        source=alignment.get("source",{})
        if not isinstance(source,dict) or source.get("method")!="forced_alignment":
            raise ValueError("Alignment provider must declare source.method=forced_alignment")
        if source.get("tool_or_reviewer")!=providers["alignment"]["name"]:
            raise ValueError("Alignment output must name the configured aligner")
        problems=validate_alignment(alignment,script,audio)
        if problems:
            raise ValueError("Forced alignment rejected: "+"; ".join(problems))
        if timeline.exists():
            raise FileExistsError("Alignment appeared during execution; refusing overwrite")
        write_json_atomic(timeline,alignment)
    record=json.loads(metadata.read_text(encoding="utf-8"))
    record["alignment_status"]="verified_timing_contract"
    record["alignment_sha256"]=sha256(timeline)
    record["alignment_provider"]=providers["alignment"]["name"]
    write_json_atomic(metadata,record)
    return {"status":"aligned","audio_sha256":audio_hash,
            "duration_ms":duration,"segments":len(alignment["segments"]),
            "verified_voice_quality":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",required=True)
    p.add_argument("--providers",required=True,help="JSON config containing trusted TTS/forced-alignment argv commands")
    p.add_argument("--reuse-audio",action="store_true",
                   help="Skip synthesis; reuse an existing locked complete recording")
    a=p.parse_args()
    print(json.dumps(run(a.project,load_config(a.providers),reuse_audio=a.reuse_audio),
                     ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
