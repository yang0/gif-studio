# v3.0 · 音频优先的混合素材视频预览

> **当前制作优先遵循 [真实素材来源门禁](real-source-contract.md)**：本文部分表格来自旧版接口。所有默认 CLI 入口现在要求 `source_provenance`；不允许 `data_motion`/程序图形卡片作为主体镜头。仅历史低层函数/测试仍保留旧类型用于回归。


`scripts/video_cut.py` 是视频制作工具，不是生图服务。它按真实语音时间轴直接剪入用户已有的动画、视频与截图，面向知识类 A/B-roll。无需号池，也无需 Docker。

## 当前支持

| 视觉计划 media_type | 素材 | 规则 |
| --- | --- | --- |
| `gpt_gif` | 已登记的原始 GIF 候选 | 通过 `source_shot_id` / `candidate_id` 引用，必须与素材库 SHA 一致 |
| `screen_recording` | 已有 MP4 / MOV / MKV / WebM 录屏 | 用 `source_file` 与 `source_sha256` 引用；按源视频时间戳截取，不静帧凑秒数 |
| `screenshot` | PNG / JPG / WebP 静态截图 | 用 `source_file` 与 `source_sha256` 引用；允许作为明确的静态信息镜头，不得假称 GIF 动画 |
| `data_motion`, `text_overlay` | 尚未实现 | 不偷偷用 PPT 或 SVG 伪装；需要未来独立、可控的信息动效引擎 |

**A/B-roll 是内容职责而非素材类型。** A-roll 可用角色 GIF，B-roll 可用正确截图、实际录屏或解释机理的 GIF。严格的 GPT-GIF 画面模式仍保留；使用截图、录屏时必须显式加 `--allow-mixed-media`。已存在的视频/截图可以直接用于剪辑，无需重新生成 GIF。

## 项目字段

先有真实 `script.json`、`audio/voiceover.wav`、`audio-timeline.json`、`visual-plan.json` 和 `storyboard.json`。在 `visual-plan.json.shots[]` 中添加真实媒体引用：

```json
{
  "id": "v2", "roll": "B", "role": "demo", "media_type": "screen_recording",
  "start_ms": 1800, "end_ms": 3200, "audio_segment_ids": ["s002"],
  "visual_event": "实际软件操作演示", "cut_reason": "讲到功能时切换真实录屏",
  "source_file": "media/demo.mp4",
  "source_sha256": "填写 demo.mp4 的真实 SHA256",
  "source_in_ms": 1000
}
```

对于截图，把 `media_type` 设为 `screenshot`，`source_file` 设为如 `media/actual.png`，不设置 `source_in_ms`。系统不会从截图中制造虚假动画。GIF 则用现有素材池的 `source_shot_id` 与 `candidate_id`。

## 预览流程

```bash
# 有声学时间码、视觉计划及真实素材后执行
python scripts/video_cut.py --project project --compile --allow-mixed-media

# 可选：先使用 audio_subtitles.py 从真实时间码生成字幕
python scripts/audio_subtitles.py --project project

# 生成带原始旁白与字幕的预览，仍需整片人工审阅
python scripts/video_cut.py --project project --preview --allow-mixed-media --subtitles project/subtitles/captions.srt
```

输出默认 `project/build/mixed-preview.mp4`，报告 `project/build/video-preview/preview-report.json`，状态固定 `UNREVIEWED_MIXED_PREVIEW`。重复导出必须显式采用新输出文件名，不静默覆盖已审版本。

代码会检查：真实语音时间、素材文件 SHA、视频是否含视频轨、镜头源时长是否足够、图像格式、实际输出帧数和是否有声轨。任何素材/视觉时间线变化必须重新编译剪辑计划。

## 质量边界

- 该路径是**混合素材编辑预览**，不是旧 GIF-only `release_sequence.py` 的正式审核替代物。正式审片签核仍未接入混合媒体发布流程，不能把预览误认为正式成片。
- 仍需导演实际检查画面与口播语义、画面主体连续性、中文字幕可读性、音量、信息准确性和动作切点。技术测试无法验证这些质量标准。
- 字幕可以直接使用经过真实音频对齐得到的 SRT，不根据每镜长度平均猜时间。
- `screen_recording`、`screenshot` 需要用户合法获得/使用的素材；未自动获得第三方版权许可。

明确：视频制作不要求强制生成新 GIF，混合媒体是 v3 的正当使用场景；`--allow-mixed-media` 是当前预览器的显式安全开关，不表示强制使用任何外部模型或号池。
