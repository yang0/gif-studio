# Troubleshooting / 常见问题

## Codex 没有 GIF 工具

Skill 本身不能给 Codex 增加新模型能力。先检查当前会话实际可用的图像生成工具及是否支持 GIF 输出。无法确认时，只创建 storyboard 与 prompts，并停止在 Gate 3；不要调用未授权的外部 API。

## Pillow 模块缺失

```bash
python3 -m pip install -r requirements.txt
```

## ffmpeg 找不到

macOS: `brew install ffmpeg`；Ubuntu: `sudo apt-get install ffmpeg`。

## ffmpeg 字幕滤镜不可用

执行 `ffmpeg -filters | grep subtitles` 检查 libass 字幕滤镜。若缺失，先运行不带 `--burn-subtitles` 的合成命令；脚本仍会输出外挂 `subtitles/captions.srt`。

## GIF 尺寸不是 9:16

Inspector 报警告但不会错误地宣布生成失败。合成器用 scale + pad 保留比例，不拉伸。为了避免黑边，最好在生成阶段要求真正的 9:16。

## GIF 时长短于分镜时长

合成器会自动循环 GIF 至目标时长；长于分镜时则截断。为避免观众看到重复，最好把关键运动设计得接近目标时长。

## 音频比视频长或短

这是镜头级字幕与外部配音合成，不是自动配音对齐。合成器截断较长音轨，对较短音轨补静音。需要逐字同步时，请先制作带时间戳的字幕与镜头时长表。

## 质量检查已通过但视频很差

`inspect_gif.py` 只验证可解码、帧数与粗粒度相邻帧差异。动作错误、伪字、歧义、主体不一致等问题必须逐帧观看并在 prompt 中针对性修复。
