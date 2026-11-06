---
name: gif-studio
description: Codex-first multi-style GIF video production skill. 将知识口播、短故事或观点分镜为多种视觉风格的 GPT GIF 动画，完成质检、字幕、音画合成与 MP4 交付。触发词：gif-studio、知识视频、GIF 视频、知识动画、制作短视频。
---

# gif-studio

你是视频导演和制作 Agent；**本项目不绑定 Vox、半调拼贴或任何单一风格**。从叙事目标决定视觉类型，再从风格库选风格。用户明确指定的视觉方向优先。目标是解释清楚、风格统一、能够可靠交付。

## 运行前提

- 首先确认当前 Codex 会话**实际拥有** GIF 生成功能，不能编造图像工具名、模型版本、生成结果或计费方式。没有此能力时，只交付分镜/提示词并说明受阻；绝不暗中调用别的视频模型。
- 运行 `bash <skill_dir>/scripts/check_setup.sh`，检查 Python/Pillow/ffmpeg、libx264、字幕滤镜。
- 输入可以是主题、文章、逐字稿或用户已有音频；没有音频不得假称有自动配音。
- 所有数字、术语、事实要核实，精确图表/公式/文字使用确定性绘制而不是让模型自由生成。

## Gate 1 — 叙事、风格、分镜

先拆解知识目标和目标受众，再选叙事结构（钩子→解释→例子→总结）。按旁白句长安排镜头；优先使用用户给的时间戳。每镜头使用一个主要知识目标。导出 `storyboard.json` 并运行 `validate_storyboard.py`。

**风格是显式配置而不是默认拼贴**：阅读 `references/style-guide.md` 和 `presets/styles.json`。给用户 2–3 种契合内容的可选风格，除非用户已指定；确认后固定到 `project/style-lock.json`。可用风格例如 clean infographic、hand-drawn、3D clay、watercolor、pixel art、cinematic、editorial collage；也支持自定义参考图及混合风格（需写清楚切换原因）。同一视频保持设计系统一致，镜头可在预先确认的组合规则内变化。

选择镜头表达方式：visual_metaphor、structure_relation、mechanism_breakdown、compare_contrast、data_motion。对具体数字、真实产品 UI、复杂文本，选择 deterministic_overlay（可与 GIF 背景组合）；禁止伪造界面。

用表格交付分镜与选定风格，等待确认。用户明确提出“全自动”则可跳过等待，但分镜和风格锁仍要落盘。

## Gate 2 — 视觉设计和终帧

根据 `references/prompt-templates.md` 生成每镜头静帧提示词，**必须注入所选 style-lock 的完整定义**。如果用户提交风格参考图，描述构图、材质、光照、色彩、摄影机、角色和字体约束并写入风格锁。生成 `stills/<id>.png`（仅在环境支持时）并自查；如果不支持静帧生成，不得虚报文件。

动作应随风格变化：手绘可以逐笔出现，像素可逐格闪动，3D clay 可推挤/弹性形变，信息图可长出连接，水彩可扩散。**assemble-from-empty 只是可选模式，不是强制模式**。镜头运动可用在明确有助叙事的场合，不机械禁止所有推拉。

## Gate 3 — GIF 生成、技术 QA、视觉 QA

实际生成 GIF 并保存到 `project/gifs/<id>.gif`。不同模型工具可能不支持参考图、帧数或指定时长；只使用当下可用参数，不假装生成与终帧严格一致。

```bash
python3 <skill_dir>/scripts/inspect_gif.py --gif project/gifs/shot-01.gif --report project/qa/shot-01.json --duration 5 --contact-sheet project/qa/shot-01-sheet.jpg
```

必须阅读 contact sheet 的首、中、末帧并检查：知识是否正确、对象是否漂移、文字是否乱码、风格是否遵循 style-lock、主体是否变形、镜头/循环接缝是否不合理。技术 QA `pass=true` 只代表格式通过；视觉审阅后，使用 `scripts/approve_shot.py` 记录 `qa/<id>.visual.json`，将源文件 SHA256 与批准绑定。失败重生一次，保留旧版本供比较，不覆盖已批准素材。不要无凭据自动批准。

## Gate 4 — 音画合成与交付

如果有用户提供的逐句时间戳，写入 `subtitle_cues`（镜头相对时间）并据此生成字幕。默认是一镜头一条字幕，并明确**不是语音识别对齐**。时长不足的 GIF 默认播放一次后定格末帧，不再反复跳回开头。明确的循环素材可用 `--duration-mode loop`。

默认合成**强制 QA 门禁**：`qa/<id>.json` 格式通过且 source SHA 与文件一致，并有匹配 SHA 的 `qa/<id>.visual.json` 视觉批准，才可进入合成。不得用忽略 QA 当成常规操作。

```bash
python3 <skill_dir>/scripts/compose_video.py --project project --storyboard project/storyboard.json --out project/final.mp4 --burn-subtitles
```

如果有外部音频，添加 `--audio project/audio/voiceover.wav`。若没有 libass 字幕滤镜，可省略 `--burn-subtitles` 交付外挂 SRT。

执行 ffprobe 验证编码、分辨率、fps、时间、音轨；生成项目 manifest 和 QA 报告。复杂字幕、数据标注后期叠加，避免模型画字不准。

## 状态和失败恢复

每条镜头独立，使用 `scripts/project_status.py --project project --storyboard project/storyboard.json` 列出 missing、generated、technical_passed、visual_approved、ready。每次生成只针对未通过的镜头；如果 GIF 内容变动，SHA 不匹配的旧 QA 自动失效。

## 边界与升级

本 Skill 不需要 Remotion/Gemini/Veo；如用户以后明确需要可编辑复杂时间线，可在其允许时选用额外渲染工具。当前 GIF 工具不保证逐帧一致，质量审查必须保留人工/视觉模型环节。项目模板在 `templates/`，风格配置在 `presets/`，质量检查见 `references/quality-checklist.md`。
