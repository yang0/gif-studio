# v3.0 · Real GPT GIF batch generation runtime contract

`gif_batch.py` is a queue/runner, **not an image generator**. It can execute an explicitly configured **real local backend executable** using subprocess (without shell interpolation), send the literal prompt text and each reference-image path + SHA, and ingest genuine rendered GIFs into the existing candidate pool. If the current Codex/tool environment cannot execute GIF generation or cannot accept explicit prompts and image inputs, the backend must reject the request. Do not generate fallback SVG/PNG spritesheets pretending to be native GIF output.

## Prepare the assets

- Create `project/prompts/shot-01-wide.txt` and other full shot-specific prompts.
- For character A-roll, create actual front/side/back/stroke_detail/scene images in the project, and a valid `project/reference-pack.json`. The backend must explicitly attach every reference image; simply describing references in prose does not suffice.
- Author `project/gif-batch.json` using `templates/gif-batch.json`. Use two or more **distinct action/coverage** candidate prompts instead of regenerating the same prompt over and over.

## Backend protocol

An executable (path must be trusted; DO NOT run untrusted third-party scripts) must support two calls:

1. `backend --capabilities` returns exactly one JSON object to stdout: `{"version":1,"gif":true,"explicit_prompt":true,"reference_images":true}`. Set `reference_images:false` only for backends that cannot attach images; the runner then **refuses** A-roll jobs requiring character references.
2. `backend --generate` consumes one JSON object from stdin with `prompt` (complete exact text), `prompt_sha256`, `reference_pack_sha256`, `references` (role => absolute real file path and expected image SHA), `shot_id`, `candidate_id`, `format:"gif"`, and `output_directory`. It must generate a **real animated GIF inside that exact output directory**.
3. Return exactly one JSON object to stdout: `{"version":1,"tool":"ACTUAL_TOOL","output_reference":"ACTUAL_OUTPUT_ID","prompt_sha256":"...","reference_pack_sha256":"...","attached_reference_sha256":{"front":"...","side":"...","back":"...","stroke_detail":"...","scene":"..."},"gif_path":"ABSOLUTE_PATH_TO_RENDERED_GIF"}`.
4. If a real generation call fails, return nonzero and write useful details to stderr; do not fabricate an output image or claim a different tool was used.

The runner validates the returned claims against source files and *real GIF bytes*, checks aspect ratio/frames/animation, and registers the candidate with its original prompt snapshot. **This is operator-supplied provenance, not cryptographic proof that remote GPT accepted the references**. Genuine visual quality/character identity still requires independent review.

## Windows-friendly invocation

Create a local **trusted** `backend-command.json` containing a JSON array, for example:

```json
["C:\\Python312\\python.exe", "E:\\my-tools\\actual-gif-provider.py"]
```

That second path must point to a *real working implementation* of the protocol above, connected to a generator you can genuinely use. It is **not bundled** with the Skill and will not be invented.

```powershell
python scripts/gif_batch.py --project project --tasks project/gif-batch.json --backend-file backend-command.json --workers 2 --max-attempts 2 --timeout 180
```

No Docker, shell pipeline or separate server is needed for the scheduler itself. The backend may need its own network/runtime.

## Recovery and quality guardrails

- Each attempt has a distinct output directory; task state is under `production/batch/<shot>/<candidate>.json`.
- A valid already-ingested candidate is reused on rerun. Changed request prompts/references or changed GIF bytes cause a **block**, not silent reuse.
- Only nonzero backend exits or timeouts are retried, maximum three attempts. Invalid GIF files and mismatched metadata fail immediately.
- Task rows are concurrent; the catalog write is serialized **within the running process**. Do not launch multiple batch runner processes in the same project simultaneously; cross-process catalog serialization is not provided.
- There is no cost/credit accounting; confirm the actual external generator's quota rules independently. The runner itself does not buy API credits.
- `batch_finished` and `ingested_unreviewed` mean files were ingested, **not** semantic correctness, style consistency, or final movie approval. Review in the candidate gallery before moving to the EDL/release workflow.
