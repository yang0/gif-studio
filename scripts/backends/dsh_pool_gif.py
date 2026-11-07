#!/usr/bin/env python3
"""Real optional local ChatGPT2API-DSH GIF backend for gif_batch.py.

Uses the user's existing locally running DSH account-pool interface.
GIF mode in that plugin currently does NOT support reference images.
No paid OpenAI API or video model is used.
"""
import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MODELS={"gpt-image-2.6","gpt-image-2.6-flare","gpt-image-2.6-sunburst"}
MAX_RESPONSE=60*1024*1024

def local_endpoint():
    value=os.environ.get("GIF_STUDIO_DSH_BASE_URL","http://127.0.0.1:38650/v1").rstrip("/")
    parsed=urllib.parse.urlparse(value)
    if parsed.scheme!="http" or parsed.hostname not in ("127.0.0.1","localhost","::1") or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path!="/v1":
        raise ValueError("DSH GIF backend only supports a loopback HTTP /v1 endpoint")
    return value+"/images/generations"

def settings():
    model=os.environ.get("GIF_STUDIO_DSH_MODEL","gpt-image-2.6")
    if model not in MODELS:
        raise ValueError("Unsupported DSH GIF model")
    frames=int(os.environ.get("GIF_STUDIO_GIF_FRAMES","9"))
    duration=int(os.environ.get("GIF_STUDIO_GIF_FRAME_MS","200"))
    if not 2<=frames<=16 or not 20<=duration<=2000 or duration%10:
        raise ValueError("DSH GIF frame_count must be 2..16; frame duration 20..2000ms, step 10")
    return model,frames,duration

def generate(task):
    if task.get("version")!=1 or task.get("format")!="gif":
        raise ValueError("Only GIF version 1 generation requests are supported")
    if task.get("references") or task.get("reference_pack_sha256"):
        raise ValueError("DSH ChatGPT account-pool GIF currently does not support image references; rejecting A-roll request")
    prompt=task.get("prompt")
    if not isinstance(prompt,str) or not prompt.strip():
        raise ValueError("Missing complete literal generation prompt")
    digest=hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    if digest!=task.get("prompt_sha256"):
        raise ValueError("Supplied generation prompt SHA mismatch")
    token=os.environ.get("GIF_STUDIO_DSH_API_KEY","")
    if not token:
        raise ValueError("GIF_STUDIO_DSH_API_KEY must be set to the local plugin's API access key")
    model,frames,duration=settings()
    output=Path(task["output_directory"]).resolve()
    if not output.is_dir():
        raise FileNotFoundError("Caller-provided isolated attempt directory absent")
    body={"model":model,"prompt":prompt,"output_format":"gif",
          "frame_count":frames,"frame_duration_ms":duration,
          "size":"auto","aspect_ratio":"9:16"}
    encoded=json.dumps(body,ensure_ascii=False).encode("utf-8")
    request=urllib.request.Request(local_endpoint(),data=encoded,method="POST",
        headers={"Content-Type":"application/json","Authorization":"Bearer "+token})
    # Do not allow OS proxy environment to redirect a locally authenticated request.
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request,timeout=240) as response:
            data=response.read(MAX_RESPONSE+1)
    except urllib.error.HTTPError as exc:
        detail=exc.read(3000).decode("utf-8","replace")
        raise RuntimeError(f"Local DSH image endpoint returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Local DSH image endpoint unavailable: {exc.reason}") from exc
    if len(data)>MAX_RESPONSE:
        raise ValueError("Local DSH response exceeded 60MiB maximum")
    response=json.loads(data.decode("utf-8"))
    items=response.get("data") if isinstance(response,dict) else None
    if not isinstance(items,list) or not items or not isinstance(items[0],dict):
        raise ValueError("DSH response lacked images data[0]")
    raw=items[0].get("b64_json")
    if not isinstance(raw,str) or not raw:
        raise ValueError("DSH did not return native GIF b64_json")
    try:
        gif=base64.b64decode(raw,validate=True)
    except ValueError as exc:
        raise ValueError("Invalid base64 GIF from DSH") from exc
    if not gif.startswith((b"GIF87a",b"GIF89a")):
        raise ValueError("Upstream returned non-GIF bytes; refusing to animate a static image")
    path=output/"generated.gif"
    if path.exists():
        raise FileExistsError("Attempt GIF already exists")
    path.write_bytes(gif)
    # There may be no upstream ID. A content hash is an honest local reference.
    reference=response.get("id") if isinstance(response.get("id"),str) and response["id"] else "local-gif-sha256:"+hashlib.sha256(gif).hexdigest()
    return {"version":1,"tool":"chatgpt2api-dsh:"+model,
            "output_reference":reference,"prompt_sha256":digest,
            "reference_pack_sha256":None,"attached_reference_sha256":{},
            "gif_path":str(path),
            "note":"Local account-pool GIF response; no reference-image capability and no remote authenticity attestation"}

def main():
    if len(sys.argv)!=2 or sys.argv[1] not in ("--capabilities","--generate"):
        raise SystemExit("Usage: dsh_pool_gif.py --capabilities | --generate")
    if sys.argv[1]=="--capabilities":
        print(json.dumps({"version":1,"gif":True,"explicit_prompt":True,"reference_images":False,
                          "backend":"local-chatgpt2api-dsh-gif"}))
        return
    task=json.load(sys.stdin)
    result=generate(task)
    print(json.dumps(result,ensure_ascii=False))

if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        print(f"DSH GIF backend error: {exc}",file=sys.stderr)
        raise SystemExit(1)
