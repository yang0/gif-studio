# Knowledge GIF Studio 🎞️

面向 **Codex** 的知识短视频 Skill：把口播文稿拆为分镜，使用当前 Codex 环境提供的 GPT 图像/GIF 工具生成画面，然后用 ffmpeg 做 GIF 检查、镜头时长规范化、字幕和 MP4 合成。

> 重要：本仓库 **不声称**能通过普通 Python 脚本免费调用 ChatGPT 的 GIF 生成额度。GIF 由 Codex 会话中实际可用的图像工具生成；没有 GIF 能力时会明确停止，不会偷偷调用第三方视频模型或伪造结果。

## 安装

```bash
git clone https://github.com/yang0/gif-studio.git ~/.agents/skills/knowledge-gif-studio
bash ~/.agents/skills/knowledge-gif-studio/scripts/check_setup.sh
```

依赖：Python 3.10+、ffmpeg/ffprobe；GIF 检测需要 Pillow（`python3 -m pip install -r requirements.txt`）。GIF 生成本身需要你的 Codex 会话提供图像/GIF 生成工具。

在 Codex 中说：**“用 knowledge-gif-studio 把这段口播制作成 30 秒知识短视频：……”**

## 工作流

1. Gate 1：知识拆解和分镜（人工确认一次）。
2. Gate 2：制定统一风格和终帧设计，生成静帧（允许自行质检重试）。
3. Gate 3：用 GPT GIF 工具逐镜头生成并执行技术与视觉 QA。
4. Gate 4：按 storyboard 时长规范化 GIF、生成 SRT、合成 MP4，可选配音。

默认 9:16 / 720×1280 / 24fps。每镜头 3–6 秒。视频 **不自动生成旁白**；传入已有音频才添加声音。导出的 SRT 按镜头近似定时，不是逐字语音对齐。

## 示例

```bash
python3 scripts/inspect_gif.py --gif project/gifs/shot-01.gif --report project/qa/shot-01.json --duration 5
python3 scripts/compose_video.py --project project --storyboard project/storyboard.json --out project/final-video.mp4 --burn-subtitles
# 带旁白：
python3 scripts/compose_video.py --project project --storyboard project/storyboard.json --out project/final-video.mp4 --audio project/audio/voiceover.wav --burn-subtitles
```

参见 [SKILL.md](SKILL.md)、[提示词](references/prompt-templates.md)、[示例分镜](examples/ai-judgment/storyboard.json)。

## 生成文件

```text
project/
├── storyboard.json
├── stills/shot-01.png
├── gifs/shot-01.gif
├── qa/shot-01.json
├── clips/shot-01.mp4
├── subtitles/captions.srt
└── final-video.mp4
```

## 已知边界

- 只保证静态图片及 GIF 的文件级技术检查；GIF 的文字伪影、隐喻清晰度、视觉连续性需 Codex 逐帧复核。
- GIF 的循环属性不是视频连续性的保证；合成默认让每个镜头恰好匹配 storyboard 时长，必要时重复/截断 GIF。
- 精确数字/公式与多行字幕交给后期程序渲染，不让图像模型直接拼写。
- 音轨长度与分镜总时长不同时会报告警告，合成按视频长度裁剪或补静音，不保证逐字同步。

License: MIT.
