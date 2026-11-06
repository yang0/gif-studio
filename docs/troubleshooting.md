# gif-studio Troubleshooting

## Codex 没有 GIF 工具
本仓库仅定义制作协议与后期脚本，不会赋予 Codex 新模型功能。无法输出 GIF 时只能继续分镜和 prompt，不能虚构素材，也不自动切换第三方视频服务。

## 还想使用 Vox / 拼贴风？
从 `presets/styles.json` 选择 `editorial-collage`；它是可选预设之一，不是默认。

## 没有 ffmpeg / Pillow
执行 `python3 -m pip install -r requirements.txt`，通过系统包管理器安装 ffmpeg 和 ffprobe。运行 `bash scripts/check_setup.sh` 检测 libx264 和字幕滤镜。

## 报错 QA blocked
先运行 `inspect_gif.py` 生成 `qa/<id>.json` 和 contact sheet。实际观看后使用 `approve_shot.py` 创建 `qa/<id>.visual.json`。如果 GIF 被编辑/重生，旧审核因为 SHA256 不符失效。开发阶段可使用 `--allow-unreviewed`，禁止把这种成片误报为正式验收。

## GIF 短于镜头
默认只播放一次，后半段停在末帧。如需真正循环则显式 `--duration-mode loop`，并先复核循环接缝。

## 字幕时间偏差
默认每镜头一条字幕；可以在 shot 内提供 `subtitle_cues` 数组，每个条目包含相对时间 `start_sec`、`end_sec` 和 `text`。这些时间戳需来自真实语音对齐或人工标记，不是脚本自动生成的语音识别。

## 音频长度与视频不同
会裁切长音频或给短音频补静音；需人工确认对应叙事节奏。

## 缺少字幕滤镜
运行 `ffmpeg -filters | grep subtitles`。缺少 libass 时不使用 `--burn-subtitles`，导出外挂 SRT。

## v1.5 提示 provenance stale / unregistered
缺少 director-plan.json、style-lock.json、production/assets.json 或相应提示词。按 docs/production-pipeline.md 登记来源；如果修改了画面、分镜、风格或提示词，需重新登记和审核。

## duplicate GIF detected
检查是否把同一 GIF 复制成多个不同分镜。只有导演方案事先声明 intentional_reuse 且记录复用来源和理由时才允许复用。

## formal visual review rejected
必须先生成 contact sheet，真实核对语义、动作、风格和构图，再用 scripts/approve_shot.py 明确记录四项审核。不得由生成脚本自动填写通过结果。
