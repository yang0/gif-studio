# v3.1：视频导演 → 语义剪辑 → 实际审片 → 局部返工

这是通用 Codex 视频制作 Skill，不是某个 GIF 生成器的客户端。

## 0. 准备真实输入

项目以 `project/script.json` 的定稿文案、真实 `project/audio/voiceover.wav`、声学对齐 `project/audio-timeline.json`、`project/visual-plan.json`、`project/storyboard.json` 为依据。
通过 `python scripts/project_flow.py init --project project` 创建项目（已有项目不可覆盖）；准备自然声音、严格确认句级时间码，然后：
- `python scripts/audio_timeline.py --script project/script.json --audio project/audio/voiceover.wav --timeline project/audio-timeline.json`
- `python scripts/visual_plan.py --script project/script.json --audio project/audio/voiceover.wav --timeline project/audio-timeline.json --plan project/visual-plan.json`

不能用 CI 的静音、机械旁白或字数估计虚构真实口播质量。

## 1. Codex 创建两套真正不同的视觉方案

`python scripts/director_brief_agent.py --script project/script.json --timeline project/audio-timeline.json --visual project/visual-plan.json --out project/director-assignment.md`

Codex 读取 `director-assignment.md`，逐镜明确 init → trigger → final、信息增量、表演、镜头理由与实际素材；将 JSON 保存到 `project/shot-briefs.json`。然后：

`python scripts/director_brief_agent.py --script project/script.json --timeline project/audio-timeline.json --visual project/visual-plan.json --briefs project/shot-briefs.json`

`python scripts/visual_director.py --visual project/visual-plan.json --timeline project/audio-timeline.json --briefs project/shot-briefs.json --variant dramatic --out project/director-v2.json`

`python scripts/character_performance.py --director project/director-v2.json --visual project/visual-plan.json`

`python scripts/broll_strategy.py --director project/director-v2.json --visual project/visual-plan.json`

所有检查都只是方向核对，真实素材画面质量仍需观看。

## 2. 用实际语音的事件点决定切镜

`python scripts/editorial_engine.py --director project/director-v2.json --visual project/visual-plan.json --timeline project/audio-timeline.json --out project/editorial-decisions.json`

它标出真实口播与动作事件的切点风险，不能用固定每三秒切一次。

若需要实际更改镜头边界，审片人准备确认过的 `boundaries.json`（从 0 到音轨尾毫秒的整数时间码，数量=镜头数+1），执行：

`python scripts/semantic_recut.py --visual project/visual-plan.json --timeline project/audio-timeline.json --script project/script.json --audio project/audio/voiceover.wav --boundaries project/boundaries.json --out project/visual-plan-r2.json`

编排必须保证实际视频源长度充足。改变视觉时间线后重新写受影响的导演方案，不允许旧导演计划静默复用。

## 3. 真正制作未审核视频

准备合格源素材后用：

`python scripts/audio_subtitles.py --project project`

`python scripts/production_run.py --project project --until mixed_preview`

已存在的原样片与 EDL 只有在哈希一致时才可恢复。静态图是明确静态证据，程序信息图必须有证明来源的 .motion.json，绝不能伪装为 GPT GIF。视频片段经哈希与所有输出参数构成的缓存键进行复用。

## 4. 实际看片、记问题和单镜返工

`python scripts/video_critic.py --video project/build/mixed-preview.mp4 --plan project/video-plan.json --report project/quality/critic.json`

审阅者完整观看并试听，检查角色、知识事实、人物大小、字幕与声音；允许用本地 A/B 工作台生成对比页面：

`python scripts/review_compare.py --project project --before project/build/mixed-preview.mp4 --after project/build/revised-preview.mp4 --critic project/quality/critic.json --plan project/video-plan.json --out project/review/compare.html`

HTML 直接浏览器打开，无联网服务；点击某个镜头可定位播放，人工记录问题并下载符合 `revision_planner.py` 规范的 `defects.json`。下载的 JSON 不构成批准。

`python scripts/revision_planner.py --video project/build/mixed-preview.mp4 --plan project/video-plan.json --critic project/quality/critic.json --findings project/quality/defects.json --revision-id rev-001 --out project/revisions/rev-001.json`

替换素材必须提前实际存在于原工程，且包含 SHA。写 `replacements.json`：version=1，revision_id=rev-001，replacements 按镜头 ID 索引，每项提供真实 `source_file` 和 `source_sha256`，或已注册真实 GIF 的新 `candidate_id`；对于修改语义的 v3.1 项目，还要提供经审核的 `director_plan`。语义重定时可附 `revised_visual_plan`。然后：

`python scripts/revision_execute.py --project project --revision project/revisions/rev-001.json --findings project/quality/defects.json --critic project/quality/critic.json --source-video project/build/mixed-preview.mp4 --plan project/video-plan.json --replacements project/replacements.json`

新工程在 `project/revisions/rev-001/project`，原始项目不覆盖；没改的来源和 FFmpeg 片段缓存被复用，但新的整片合成、字幕/审片/正式审批必须重新执行。若缺陷涉及自然配音，必须先重新录制并对齐实际声音，本脚本绝不伪造新音频。

## 5. 发布

视频只有经过 `mixed_release.py` 的真实逐镜审片，独立 `formal-mixed/final.mp4`，以及 `final_review.py` 的完整观看/试听与审批后才能记录发布质量。v3.1 若存在 `director-v2.json`，必须有绑定当前真正视频与剪辑计划的 `quality/critic.json` 和经过实际观察的 `quality/human-review.json`；两阶段都不能被 CI 模拟器替代。

高质量 Golden Sample 标准：真实自然中文配音、声学对齐、字幕、人物行为与一致性、知识增量以及有证据的主观质量评分。未满足时保留开放问题，不宣称全部完成。
