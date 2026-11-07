# Authentic visual-source contract · Issue #3

> Applicable to the **default** `production_run.py --until mixed_preview`, `video_cut.py` CLI, and `mixed_release.py` CLI. Older modules remain for technical migration/tests, **not** the recommended creation workflow.

## Hard rule

The project's video **must not be fabricated** out of SVG/Pillow/Canvas, FFmpeg drawbox/drawtext card animations, data-motion charts, repetitive still frames, or vector/PPT slides. These are not substitutes for real creative footage. FFmpeg may trim, color-convert, rescale, add actual speech subtitles, mix audio, and concatenate **existing** real media.

A video can be based on a model-created GIF/video, actual camera recording, actual screen recording, licensed footage, or a clearly static source screenshot/photo used as evidence. No particular model, vendor, API, account pool, Docker stack or payment gateway is required. Do not substitute one medium for another on failure.

`media_type=data_motion` and `text_overlay` are no longer valid **primary video sources** in the default pipeline. Existing scripts/tests involving graphics remain legacy. Model-rendered video may be registered as `original_animation` only with explicit real generation details; programmatically drawn animation cannot claim that type.

## Required shot metadata

Every `visual-plan.json.shots[]` needs an actual `source_provenance` declaration. For example, after **actually** recording the screen and calculating the file's SHA256:

```json
{
  "id": "v002",
  "start_ms": 1200,
  "end_ms": 2900,
  "roll": "B",
  "role": "demo",
  "media_type": "screen_recording",
  "visual_event": "在真实应用里打开通知设置、关闭通知开关",
  "cut_reason": "直接展示实际操作，而不是插入一个标有文字的 PPT 卡片",
  "audio_segment_ids": ["s002"],
  "source_file": "media/real-screen-capture.mp4",
  "source_sha256": "<file SHA256, never invent>",
  "source_provenance": {
    "origin": "screen_capture",
    "producer": "OBS Studio / actual operator",
    "reference": "<actual recording-session identifier>",
    "source_sha256": "<same file SHA256>",
    "rights_confirmed": true
  }
}
```

Supported `media_type → origin` pairs:

| Media type | Source origin |
| --- | --- |
| `gpt_gif` (legacy name for actual generated GIFs, not tied to one model) | `model_generated_gif` |
| `original_animation` | `model_generated_video` |
| `real_video` | `camera_recording`, `licensed_real_footage` |
| `screen_recording` | `screen_capture` |
| `screenshot` | `screen_capture`, `camera_photo`, `licensed_photo`, `model_generated_image` |

Every kind needs `producer`, `reference`, `rights_confirmed: true`, and `source_sha256` bound to the bytes of the exact source file. A `gpt_gif` shot additionally needs a real `candidate_pool` registration with tool, matching reference, original prompt, and `prompt_delivery=explicit_tool_argument`. A model-generated video requires `model`, `request_id`, and original `prompt_sha256` in `source_provenance`. These values should come from actual tool output, not be made up.

Only **real** source media may be imported. The evidence schema is not a licence to label a synthetic frame as a camera shot: `ffprobe`, GIF decoding and SHA256 establish file integrity and type, **not** its actual authorship. Human/vision-agent visual inspection, tool logs, licence checks and independent release approval remain essential. The checker never issues creative approval.

## Standard flow: stop on absent assets

```bash
# 1. Write real speech, time alignment, director/visual plans.
# 2. Produce/import ACTUAL footage; register source evidence on every shot.

# Preview the per-shot blocker list without rendering anything:
python scripts/real_source_gate.py --project project --report project/quality/media-gaps.json

# Only after all source gaps are fixed:
python scripts/production_run.py --project project --until mixed_preview

# Then check technical video evidence and actually watch/listen:
python scripts/video_critic.py --video project/build/mixed-preview.mp4 \
  --plan project/video-plan.json --report project/quality/critic.json
```

The source checker prints `status: BLOCKED_REAL_MEDIA` plus a `gaps[]` array containing each `shot_id`, problem and actionable `next_action`. Missing original footage, stale bytes, path escapes, mismatched declared origin, procedural media, a static GIF, duplicate footage at the same in-point, unsupported file extension or non-decoding video **block** the preview. Do not fall back to filler or reused footage.

The default `video_cut.py` CLI and mixed formal-release CLI run the same preflight. `project_flow.py status` includes `real_visual_sources`. Tests that call low-level `video_cut.compile_plan()` directly are legacy structural fixtures, not a means of approving production; they may include synthetic art strictly to test technical mechanics.

## What successful tests do not mean

- Passing the media gate does **not** prove a video is interesting, attractive or accurate.
- A GIF with multiple frames does **not** prove a model generated it, nor that it depicts a meaningful motion.
- A model/recording reference typed in JSON is an **unverified claim** until checked independently.
- CI green means the checked code paths work on fixtures, **not** that the Golden Sample passed.
- Issue #2 P2-2 remains open until a 20–30s real film with natural narration, authentic alignment, visual continuity, and independent full watch/listen ≥80/100 exists.
