# gif-studio 🎬

**基于 Codex 中实际可用的 GPT GIF 功能，制作多风格知识类与叙事类短视频。** 不绑定 Vox、半调拼贴或任何一种视觉模板。

## 核心理念

- **Style-first**：内容决定视觉处理；提供 7 套可扩展风格（极简信息图 / 手绘 / 黏土 3D / 水彩 / 像素 / 电影 / 编辑拼贴），也支持用户参考图。
- **Voice-first**：镜头时长按口播安排；字幕支持分镜级与带明确时间戳的 cue。
- **Verified**：技术 QA、contact sheet、视觉批准、源 GIF SHA256 均绑定，未过 QA 默认禁止合成。
- **Resumable**：每个镜头独立生产，状态脚本列出需要补做的镜头。
- **Hybrid accuracy**：精确文字和数据后期绘制，GIF 负责创意运动。

> 本仓库脚本不会调用 OpenAI API 或任何第三方视频模型。生成 GIF 必须由实际支持 GIF 的 Codex 工具执行。无法调用时可以生成分镜与提示词，但不能冒充 GIF 已生成。

## 安装（Codex）

```bash
git clone https://github.com/yang0/gif-studio.git ~/.agents/skills/gif-studio
python3 -m pip install -r ~/.agents/skills/gif-studio/requirements.txt
bash ~/.agents/skills/gif-studio/scripts/check_setup.sh
```

在 Codex 里说：**“使用 $gif-studio 把我的这段稿子制作成 30 秒视频。先推荐三种不同视觉风格和分镜。”**

## 流程

1. 分析知识与叙事，推荐视觉风格，确认分镜和 style-lock。
2. 生成关键静帧（工具支持时），再使用 GPT GIF 生成对应动画。
3. GIF 技术检查+关键帧接触表，视觉审核后记录 SHA 绑定的批准文件。
4. 已通过 QA 的素材合成视频，支持外部配音、字幕、成片核验。

## 从素材到成片

将确认分镜保存为 `project/storyboard.json`，GIF 保存到 `project/gifs/shot-01.gif` 等。

```bash
python3 scripts/validate_storyboard.py --storyboard project/storyboard.json
python3 scripts/inspect_gif.py --gif project/gifs/shot-01.gif --duration 5 --report project/qa/shot-01.json --contact-sheet project/qa/shot-01-sheet.jpg
# 观看 contact sheet、核对知识和风格后，明确记录视觉审查结果：
python3 scripts/approve_shot.py --project project --shot shot-01 --reviewer "Codex visual review" --notes "画面一致，内容准确"
python3 scripts/project_status.py --project project --storyboard project/storyboard.json
python3 scripts/compose_video.py --project project --storyboard project/storyboard.json --out project/final.mp4 --burn-subtitles
```

有真实旁白音频时，合成命令追加 `--audio project/audio/voiceover.wav`。如需严格逐字同步，须提供真实时间戳/对齐结果；一镜头一行字幕并不等于音频自动识别。

默认 GIF 只播放一次；时长不足则**保持末帧**，避免重复时突然跳回首帧。确实无缝循环时可以单独使用 `--duration-mode loop`。如有 QA 问题，默认拒绝合成；`--allow-unreviewed` 仅用于开发调试并应明确向用户披露。

## 参考

- [主 Skill](SKILL.md)
- [多风格目录](presets/styles.json) 与 [导演指南](references/style-guide.md)
- [提示词模板](references/prompt-templates.md)
- [异常排查](docs/troubleshooting.md)
- [两个示例分镜](examples/)

## 测试

```bash
python3 -m unittest discover -s tests -v
```

GitHub CI 在 Python 3.10–3.12 下运行合成素材烟雾测试；不能代替真实 Codex GIF 工具的端到端验证。

## 边界

系统不保证 GIF 生成能力已向任何特定 Codex 账号开放；不含自动语音识别/配音服务；视觉审核需实际读取接触表；准确公式和统计图需额外确定性渲染；配音长短与分镜不一致时最终按视频长度截断或填静音，须人工核对。

MIT License.
