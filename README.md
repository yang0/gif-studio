# gif-studio 🎬

**基于 Codex 中实际可用的 GPT GIF 功能，制作多风格知识类与叙事类短视频。** 不绑定 Vox、半调拼贴或任何一种视觉模板。

## 核心规则：GPT GIF ONLY

正式视频**不能用蹩脚的矢量动画、PPT 动图或本地程序化示意图替换 GPT GIF**。如果生成跑题或质量不过关，立即停止正式合成、保留失败 GIF 和 QA 记录。默认 `--asset-mode gpt-only` 在代码层拦截程序化镜头。仅当用户明确授权混合模式，才能指定 `--asset-mode mixed`。ffmpeg 仍用于转码、字幕、音频，不负责替代主要视觉素材。

## 核心理念

- **Narrative-first**：先写一篇连贯口播、审核承接关系，再拆分镜；镜头不能反向决定句子的组织方式。
- **Style-first**：内容决定视觉处理；提供 7 套可扩展风格（极简信息图 / 手绘 / 黏土 3D / 水彩 / 像素 / 电影 / 编辑拼贴），也支持用户参考图。
- **Voice-first**：镜头时长按口播安排；字幕支持分镜级与带明确时间戳的 cue。
- **Directed**：独立的视觉导演方案，明确每镜头的起点、变化、终点及镜头间连接，不允许机械套用 PPT 卡片版式。
- **Provenance**：每条 GIF 绑定完整提示词、声明的实际生成工具、导演分镜与风格指纹；重复素材须标记为有意复用。
- **Verified**：技术 QA、contact sheet、视觉批准、源 GIF SHA256 均绑定，未过 QA 默认禁止合成。
- **Resumable**：每个镜头独立生产，状态脚本列出需要补做的镜头。
- **GPT GIF first, without substitution**：字幕和数字允许叠加，但不准替换主要画面。

> 本仓库脚本不会调用 OpenAI API 或任何第三方视频模型。生成 GIF 必须由实际支持 GIF 的 Codex 工具执行。无法调用时可以生成分镜与提示词，但不能冒充 GIF 已生成。

## 安装（Codex）

```bash
git clone https://github.com/yang0/gif-studio.git ~/.agents/skills/gif-studio
python3 -m pip install -r ~/.agents/skills/gif-studio/requirements.txt
bash ~/.agents/skills/gif-studio/scripts/check_setup.sh
```

在 Codex 里说：**“使用 $gif-studio 把我的这段稿子制作成 30 秒视频。先推荐三种不同视觉风格和分镜。”**

## 流程

1. 先写完整口播、审查叙事逻辑与自然口语，用户确认后锁定 script.json / voiceover.md。
2. 再推荐视觉风格与分镜，将镜头口播与完整原稿逐字核对。
3. 编写导演方案 director-plan.json：可见因果变化、构图、前后镜连接、素材来源策略。
4. 生成关键静帧（工具支持时），再使用 GPT GIF 生成对应动画。
5. GIF 技术检查+关键帧接触表，视觉审核后记录 SHA 绑定的批准文件。
6. 已通过 QA 的素材合成视频，支持外部配音、字幕、成片核验。

## 更严格的 GPT GIF 生产

现在每个镜头都必须指定 must_show / must_not_show，明确画面中必须发生什么、不能出现什么。用 build_gif_prompts.py 编译每镜独立提示词；GIF 跑题后使用 review_gif_attempt.py 登记失败并生成一次针对性修复提示词。连续两次失败就停止并修改导演方案，不再靠无限重试或矢量动画兜底。

详细说明：[GIF 生成与失败处理](references/gif-generation-playbook.md)。

## 从素材到成片

先保存确认后的 `project/script.json` 与完整口播，再保存 `project/storyboard.json`、`project/style-lock.json` 和 `project/director-plan.json`。每镜头保存独立的实际素材与原始生成提示词到 `project/gifs/` 和 `project/prompts/`。

```bash
python3 scripts/audit_script.py --script project/script.json --voiceover project/voiceover.md --report project/script-audit.json
python3 scripts/validate_storyboard.py --storyboard project/storyboard.json
python3 scripts/director_plan.py --director project/director-plan.json --storyboard project/storyboard.json
python3 scripts/build_gif_prompts.py --project project --storyboard project/storyboard.json
python3 scripts/audit_script.py --script project/script.json --storyboard project/storyboard.json
python3 scripts/register_asset.py --project project --storyboard project/storyboard.json --shot shot-01 --kind gpt_gif --tool ACTUAL_TOOL --reference ACTUAL_REFERENCE --prompt project/prompts/shot-01.txt
python3 scripts/inspect_gif.py --gif project/gifs/shot-01.gif --duration 5 --report project/qa/shot-01.json --contact-sheet project/qa/shot-01-sheet.jpg
# 真实审阅接触表与动画后才能审批（不可自动伪造通过）：
python3 scripts/approve_shot.py --project project --storyboard project/storyboard.json --shot shot-01 --reviewer REVIEWER --notes "记录具体所见" --semantic-pass --motion-pass --style-pass --composition-pass
python3 scripts/project_status.py --project project --storyboard project/storyboard.json
python3 scripts/compose_video.py --project project --storyboard project/storyboard.json --out project/final.mp4 --burn-subtitles
```

有真实旁白音频时，合成命令追加 `--audio project/audio/voiceover.wav`。如需严格逐字同步，须提供真实时间戳/对齐结果；一镜头一行字幕并不等于音频自动识别。

默认 GIF 只播放一次；时长不足则**保持末帧**，避免重复时突然跳回首帧。确实无缝循环时可以单独使用 `--duration-mode loop`。如有 QA 问题，默认拒绝合成；`--allow-unreviewed` 仅用于开发调试并应明确向用户披露。

## 参考

- [主 Skill](SKILL.md)
- [视觉导演协议](references/visual-storytelling.md) 与 [生产操作手册](docs/production-pipeline.md)
- [连贯口播写作规范](references/narrative-writing.md) 与 [口播声线](references/voice-profiles.md)
- [多风格目录](presets/styles.json) 与 [导演指南](references/style-guide.md)
- [提示词模板](references/prompt-templates.md)
- [异常排查](docs/troubleshooting.md)
- [两个示例分镜](examples/)

## 测试

本仓库**不再把上一轮三条失败的模板视频当作成功样片**。它们暴露的“单个 GIF 假充多个镜头、无配音冒充口播成片、固定 PPT 布局”已转化为审查与测试用例。真正可展示的样片需完成 GPT GIF 逐镜生成、真实配音与人工视觉验收；这部分尚未完成。


```bash
python3 -m unittest discover -s tests -v
```

GitHub CI 在 Python 3.10–3.12 下运行合成素材烟雾测试；不能代替真实 Codex GIF 工具的端到端验证。

## 边界

现有生产来源登记是执行者的声明，不是外部模型调用的密码学证明。禁止伪造模型产物或自报视觉 QA 通过。

系统不保证 GIF 生成能力已向任何特定 Codex 账号开放；不含自动语音识别/配音服务；视觉审核需实际读取接触表；准确公式和统计图需额外确定性渲染；配音长短与分镜不一致时最终按视频长度截断或填静音，须人工核对。

MIT License.
