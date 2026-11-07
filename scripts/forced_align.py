#!/usr/bin/env python3
"""Real transcript-to-audio alignment via optional stable-ts.

Always feed the locked full script to the aligner. Do not infer timestamps
from character counts. If model output text/paragraph count diverges, abort.
"""
import argparse
import json
import re
from pathlib import Path
from audio_timeline import sha256,probe_ms,script_text,normalize,validate

def align(script,audio,model_name="base",language="zh",model_loader=None):
    try:
        import stable_whisper
    except ImportError as exc:
        if model_loader is None:
            raise RuntimeError("Optional dependency missing: pip install stable-ts openai-whisper") from exc
    paragraphs=script.get("paragraphs",[])
    texts=[x["text"] for x in paragraphs]
    if not texts:
        raise ValueError("No locked script paragraphs")
    model=model_loader(model_name) if model_loader is not None else stable_whisper.load_model(model_name)
    # original_split preserves one approved paragraph per segment, rather than
    # making up text boundaries after alignment.
    result=model.align(str(Path(audio).resolve()),"\n".join(texts),
                       language=language,original_split=True)
    if result is None:
        raise ValueError("Forced aligner returned no result")
    aligned=list(result.segments)
    if len(aligned)!=len(texts):
        raise ValueError(f"Aligner returned {len(aligned)} segments for {len(texts)} locked paragraphs; refusing approximate remap")
    segments=[]
    for i,(reference,real) in enumerate(zip(texts,aligned)):
        observed=str(real.text)
        if normalize(observed)!=normalize(reference):
            raise ValueError(f"Aligner text drift at paragraph {i+1}; no synthetic timecode fallback")
        start=int(round(float(real.start)*1000))
        end=int(round(float(real.end)*1000))
        segments.append({"id":f"s{i+1:03d}","start_ms":start,
                         "end_ms":end,"text":reference})
    timeline={"version":1,
              "source":{"method":"forced_alignment",
                        "tool_or_reviewer":f"stable-ts:{model_name}:{language}"},
              "audio_sha256":sha256(audio),"duration_ms":probe_ms(audio),
              "segments":segments}
    issues=validate(timeline,script,audio)
    if issues:
        raise ValueError("Actual alignment failed validation: "+"; ".join(issues))
    return timeline

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--script",required=True)
    p.add_argument("--audio",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--model",default="base")
    p.add_argument("--language",default="zh")
    a=p.parse_args()
    script=json.loads(Path(a.script).read_text(encoding="utf-8"))
    timeline=align(script,a.audio,a.model,a.language)
    dest=Path(a.out)
    if dest.exists():
        raise FileExistsError("Existing alignment will not be replaced")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(timeline,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"actual_forced_alignment","file":str(dest),
                      "segments":len(timeline["segments"])},ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
