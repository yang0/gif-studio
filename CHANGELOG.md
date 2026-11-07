# Changelog

## [3.1.0-dev.1] - 2026-11-07
- Created Issue #2 and implemented semantic Visual Director v2 storyboard contracts with explicit alternative shot proposals.
- Added decoded-MP4 Video Critic risks, honest standalone human scoring, score integrity checks and stale-asset detection.
- Added hash-bound localized revision planner with keep/rebuild dependency scope.
- v3.1 quality checks are opt-in for existing projects and required before final approval when director-v2.json exists.
- Reorganized SKILL.md around content/sound, directing, footage/editing, actual review and selective rework; archived legacy procedures.
- Archived real 24s sample as a failed quality benchmark, not a release-quality video.


## [3.0.0-dev.8] - 2026-11-07
- Added original four-template B-roll information motion renderer with source provenance, actual MP4 output, and FFmpeg tests.
- Added A-roll scene viewpoint labels and honest camera reframing; real first-person requires real POV evidence.
- Added per-shot mixed video review, separate formal MP4 and source-bound final approval with stale-asset invalidation.
- Produced a 24-second, eight-shot mixed editorial sample using three genuine previous GIFs and five original B-roll scenes.
- Sample is NOT publish-approved: local Mandarin TTS remains robotic and no genuine sentence-level alignment was available.

## [3.0.0-dev.3] - 2026-11-07
- Added visual_assets.py to derive distinct candidate prompt and batch manifests directly from verified A/B-roll visual plans and narration anchors.
- Required real identity/style/scene reference pack for character A-roll and unique shot-specific motion/camera spec for every candidate.
- Connected the production manifest to existing gif_batch.py executor (real external backend only), immutable prompts and project_flow asset-production diagnostics.
- Added strict regression tests for duplicate candidate IDs, missing references, stale prompts and revised visual plans.
- Real artistic quality, actual TTS/Whisper and public-ready sample remain pending, not inferred from unit tests.


## [3.0.0-dev.7] - 2026-11-07
- Enforced exact alignment-derived subtitles plus matching provenance hashes in mixed-media video preview.
- Clarified video-first product scope: GIF is optional, account-pool integrations are not part of the Skill, and existing footage can be edited directly.
- GIF-only release flags remain legacy compatibility while mixed-media formal release approval remains pending.

## [3.0.0-dev.6] - 2026-11-07
- Added `video_cut.py`: audio-first A/B-roll preview from genuine GIF candidates, actual screen recordings and explicitly static screenshots.
- Uses original file hashes, real source in-points, frame-accurate FFmpeg cuts, narration audio and optional aligned SRT burn-in.
- Verifies actual exported clip frame counts, source duration, stale visual plans, and prevents unapproved mixed-media substitution.
- Added FFmpeg regression tests with 3 different real media containers; output is always UNREVIEWED_MIXED_PREVIEW pending full review.
- Kept video creation independent of account pools, paid model APIs and speculative GIF generators.


## [3.0.0-dev.5] - 2026-11-07
- Removed DSH account-pool integration and its documentation/tests: gif-studio is a standalone video-production skill, independent of any account pool or image provider.
- Retained optional provider-neutral candidate ingestion and video-editing tools; video delivery, voice alignment, A/B-roll direction and visual QA remain the product focus.


## [3.0.0-dev.3] - 2026-11-07
- Added `gif_batch.py` for concurrent real executable GIF backend calls with explicit literal prompts and source image attachment metadata.
- Batch jobs use bounded retry/timeout, content-addressed request checks, serialized in-process candidate ingestion and per-candidate resume state.
- Reject invalid native GIFs, altered prompts, mismatched reference-image SHA declarations, missing backend capabilities and fake response metadata.
- Added end-to-end subprocess protocol fixture tests and Windows-friendly `--backend-file` configuration; requires a *real* external GIF generation backend.
- Synthetic test GIFs only exercise protocol; never represent qualified GPT footage.

## [3.0.0-dev.2] - 2026-11-07
- Added real optional `edge-tts` whole-narration synthesis with actual WAV output, immutable audio metadata and no fabricated timestamps.
- Added optional `stable-ts` forced alignment from locked paragraph text to real audio; fails closed on drift/missing segments.
- Added resumable synchronous `production_run.py` stages (voice, alignment, sequence), explicit network/model consent flags and structured blocked-state reports.
- Added voice/align/provider-failure and workflow-resume regression tests.
- Real provider network/model integration, visual QA and publishable benchmark video remain unverified and open.

## [3.0.0-dev.2] - 2026-11-07
- Added real whole-track TTS and forced-alignment provider interfaces, resumable voice runner and portable provider configuration.
- Added audio_subtitles.py to generate sentence-level SRT directly from verified acoustic timecodes, with a provenance manifest.
- Formal v3 sequence release now rejects captions that no longer match the recorded audio/timeline/script.
- Online voice models, actual human listening and release-quality film remain subject to real validation.

## [3.0.0-dev.1] - 2026-11-07
- Started Issue #1 Audio-first Visual Director; introduced validated whole-track acoustic timeline and A/B-roll visual decision schema.
- Added project_flow.py for project manifest, stage diagnostics and missing/stale resource reporting (not a full automated producer).
- Added reference-pack fingerprint validation (character front/side/back/stroke/scene) and actual GIF-generator handoff/ingest adapter; no fabricated model calls.
- Added regression tests for invalid alignment, narration mismatch, visual gaps, reference mutation and generation receipts.
- Added audio-timed `visual_to_sequence.py` compiler from verified real GIF candidates into legacy frame-accurate EDL, with stale revision checks.
- Added command-based `voice_pipeline.py`, optional real `edge-tts` full-track synthesis and `stable-ts` forced alignment implementations plus opt-in `production_run.py` stage runner. Providers need actual runtime dependencies/authorization; CI tests use mocks.
- Mixed-media renderer and release-quality sample remain open.

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
