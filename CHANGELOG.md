# Changelog

## [3.0.0-dev.1] - 2026-11-07
- Started Issue #1 Audio-first Visual Director; introduced validated whole-track acoustic timeline and A/B-roll visual decision schema.
- Added project_flow.py for project manifest, stage diagnostics and missing/stale resource reporting (not a full automated producer).
- Added reference-pack fingerprint validation (character front/side/back/stroke/scene) and actual GIF-generator handoff/ingest adapter; no fabricated model calls.
- Added regression tests for invalid alignment, narration mismatch, visual gaps, reference mutation and generation receipts.
- Added audio-timed `visual_to_sequence.py` compiler from verified real GIF candidates into legacy frame-accurate EDL, with stale revision checks.
- Full TTS, actual forced aligner, mixed-media renderer and release-quality sample remain open.

## [2.3.0-candidate-release-alpha] - 2026-11-07
- Added independent per-candidate GIF technical/visual approval records, including contact-sheet and source provenance.
- Added formal multi-cut release requiring every used candidate approved, natural narration, timed SRT and director-approved EDL.
- Formal output remains PENDING_FINAL_VIDEO_REVIEW until actual full-film review.
- Final review binds candidate approval hashes and rendered MP4 provenance; candidate gallery displays independent QA state.

## [2.2.0-variable-sequence-alpha] - 2026-11-07
- Added version 2 frame-accurate EDL with arbitrarily many real candidate clips per narration shot.
- Each cut carries source/candidate IDs, immutable GIF hash, source in-frame, timeline in-frame, duration and editorial reason.
- Added actual FFmpeg clip trimming and UNREVIEWED_SEQUENCE_PREVIEW rendering without placeholder graphics.
- Added version 2 seekable timeline in the local candidate HTML gallery.
- Regression tests validate multiple cuts per shot, overlap/gap checks, stale source hashes and rendered MP4 preview.
- Explicitly kept formal release gating separate from multi-clip draft functionality.

## [2.1.0-review-workspace-alpha] - 2026-11-06
- Added a read-only, offline HTML library showing each actual candidate GIF, metadata, origins, and selected alternatives.
- Added explicit unreviewed edit-preview MP4 render from selected GIF bytes, without any generated substitute visual.
- Added clickable editorial timeline linked to the draft preview player.
- Tests cover HTML escaping, missing candidate selection, tampered GIFs and actual ffmpeg preview output.

## [2.0.0-library-alpha] - 2026-11-06
- Separated multiple genuine GPT GIF candidates from final shot selection.
- New candidate_pool.py stores source bytes, prompt snapshots, actual generation origin and selection rationale.
- Selecting another candidate invalidates previous visual approvals; candidate catalog links to the production manifest during formal preflight.
- Updated SKILL.md and README to use coverage-first production and edit-later selection.
- Added library regression tests; no generated vector fallback.

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
