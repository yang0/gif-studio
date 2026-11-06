# Changelog

## [2.0.0-editorial-alpha] - 2026-11-06
- Added frame-accurate edit decision list using actual GPT GIF duration and optional narration audio.
- Formal composition requires an approved edit plan; cut reasons and visual sequence review are mandatory.
- Formal narrative output requires actual speech within 0.35 seconds of the video; silent output is explicitly a preview.
- Reject long static end-frame filler (>25% by default) instead of using hold/loop to fake coverage.
- No vector fallback; GPT GIF remains the core visual source.

## [1.7.0] - 2026-11-06
- Added strict portrait 9:16 GIF format/motion verification.
- Blocked formal visual approval and QA on landscape GIFs even when decodable.
- Added explicit runtime prompt-delivery contract; context-inferred generation cannot be claimed as reliable per-shot prompt execution.
- Documented current runtime generation failure, without treating it as a successful film.

## [1.6.0] - 2026-11-06
- Added shot-specific must_show and must_not_show constraints.
- Added independent GPT GIF prompt compiler using approved narration, director plan and style lock.
- Added concrete failed-generation log, one focused retry prompt, and blocked_replan after two failures.
- Added CI regression coverage for off-topic generation and refusal to auto-approve failures.
- GPT GIF remains the only default visual source; no vector fallback.

## [1.5.0] - 2026-11-06

- Added director-plan validation before animation production (v1.4).
- Added content-state transitions, shot composition, entrance/exit continuity and explicit reuse decisions.
- Added asset provenance with real tool declaration, prompt SHA, shot fingerprint, director fingerprint and style SHA (v1.5).
- Formal composition now blocks missing/stale provenance and undisclosed duplicate GIF assets.
- Formal visual approval now requires contact sheet and four explicit review criteria.
- Added synthetic regression tests for stale files, repeated shots, missing director and semantic QA gates.
- No claim of full GPT GIF model integration: tool execution still depends on available Codex capability.

## [1.3.0] - 2026-11-06
- Narrative-first script drafting and review precede all storyboards.
- Added separate spoken-voice profiles, complete script structure and narration export.
- Added structural audit and verbatim script-to-storyboard consistency verification.
- Removed the assumption that a 3–6 second shot should dictate prose structure.

## [1.2.0] - 2026-11-06

### Changed
- Renamed public product and Codex skill to **gif-studio**; removed Vox/halftone collage default.
- Added seven independent visual styles, user style-lock and style-independent prompt grammar.
- Changed default short-GIF behavior from repeating to holding the final frame.
- Composition now requires technical QA and SHA-bound explicit visual review by default.

### Added
- Contact sheet extraction with loop seam metric and source SHA256.
- Per-shot approval recorder and resumable status inspection.
- Relative timed subtitle cues, in addition to legacy per-shot SRT.
- Better environment diagnostics and extended tests.

## [1.1.0] - 2026-11-06

- End-to-end synthetic GIF tests and GitHub Actions CI.
- Examples, visual specs, storyboard validation and troubleshooting.

## [1.0.0] - 2026-11-06

- Initial Codex skill and ffmpeg composition pipeline.
