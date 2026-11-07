# gif-studio 🎬

**基于 Codex 中实际可用的 GPT GIF 功能，制作多风格知识类与叙事类短视频。** 不绑定 Vox、半调拼贴或任何一种视觉模板。

## v3.0 研发中 · 音频优先的知识视频生产

[总任务 Issue #1](https://github.com/yang0/gif-studio/issues/1) · 开发按 v3 设计契约逐步落地。参考 xilo 的 Codex 知识视频实践：整段配音 → 实际声学对齐 → A/B-roll 视觉编排 → 角色三视图与场景参考 → 多候选素材 → 剪辑 → 完整审片。

已落地（尚非完整自动生产器）：

- `scripts/audio_timeline.py`：检查完整音轨 SHA、语句级毫秒区间、原文一致性和非伪造的对齐来源。
- `scripts/voice_pipeline.py`：可配置的整段真实 TTS + 声学对齐命令执行器，失败可重用已有音轨。
- `scripts/voice_production.py`、`scripts/forced_align.py`：可选 edge-tts 和 stable-ts 实际 Provider（需要联网/下载模型/安装额外依赖），不能把离线 CI 当成真实生成验收。
- `scripts/production_run.py`：带显式联网/模型授权开关的分阶段可恢复执行入口。
- `scripts/visual_plan.py`：按实际语音段构建 A/B-roll 视觉编排校验，检查覆盖、时间线空隙及错误镜头类型。
- `scripts/project_flow.py`：统一项目清单和阶段 `init/status/plan/validate`，是只读诊断/依赖检查，而不是生成器。
- `scripts/reference_pack.py`：校验角色三视图、笔触和场景的真实参考图 SHA256。
- `scripts/generator_adapter.py`：为真实 Codex GIF 生成准备完整提示词/参考包请求，并将实际输出与工具来源登记入候选池；不会自行发起虚构的 GPT API 请求。
- `scripts/gif_batch.py`：对接真实本地 GIF 后端执行程序，最多四条候选并发、超时与有限重试、失败状态和哈希绑定的断点恢复；生成能力由实际可用的外部后端提供。
- `scripts/visual_to_sequence.py`：把绑定真实音轨的毫秒级视觉计划编译成现有 `sequence.json` 自由剪辑草案，要求真实素材覆盖时长。
- `scripts/audio_subtitles.py`：直接使用真实声学时间码生成句级字幕和来源报告；v3 正式发布检查其音轨/时间码/字幕哈希是否一致。
- `scripts/voice_production.py`：可选 `edge-tts` 整段配音，输出真实 WAV 与来源报告，不能冒充音频时间码。
- `scripts/forced_align.py`：可选 `stable-ts` 模型对**实际音频+定稿文案**执行强制对齐；任何句子遗漏或文字不符都会失败。
- `scripts/production_run.py`：统一同步执行 `voice → alignment → sequence`，支持失败停止与已有产物校验恢复，日志写入 `build/workflow-status.json`。

```bash
python3 scripts/project_flow.py init --project project
# 先准备 project/script.json 与 audio/voiceover.wav，提供真实对齐时间码
python3 scripts/audio_timeline.py --script project/script.json --audio project/audio/voiceover.wav --timeline project/audio-timeline.json
python3 scripts/visual_plan.py --script project/script.json --audio project/audio/voiceover.wav --timeline project/audio-timeline.json --plan project/visual-plan.json
python3 scripts/project_flow.py status --project project
# 完成真实声学对齐后生成句级 SRT（不是把句子平均分摊）
python3 scripts/audio_subtitles.py --project project

# 角色 reference-pack.json 必须指向真实图片，不能用模板占位符直接生成
python3 scripts/reference_pack.py --project project --manifest project/reference-pack.json
python3 scripts/generator_adapter.py --project project --prepare --shot shot-01 --candidate take-a --prompt project/prompts/shot-01.txt --references project/reference-pack.json
# Codex/其他真实工具执行生成，记录实际回执后才可登记真实输出
python3 scripts/generator_adapter.py --project project --ingest --shot shot-01 --candidate take-a --gif /actual/generated.gif --receipt /actual/receipt.json --notes "具体素材观察"
```

将候选 GIF 与 A/B-roll 视觉计划中的 `source_shot_id`、`candidate_id` 关联后，可以使用：

```bash
python3 scripts/visual_to_sequence.py --project project --script project/script.json --audio project/audio/voiceover.wav --timeline project/audio-timeline.json --visual-plan project/visual-plan.json --storyboard project/storyboard.json
```

该命令生成待导演审阅的 v2 EDL；如果素材不够长或没有对应候选，它会报错而非自动凑时长。混合媒体 B-roll 引擎尚未落地。此流程不会将音轨时长按字数均摊伪装“声学对齐”，也不会把任意 GIF 注册为自动视觉通过。**v3 完整真实样片、混合媒体 B-roll、全自动外部 GIF 生成和正式发布闭环仍未完成**，见 Issue #1。

### v3 音频与剪辑真实执行入口

此批新增的语音模块是**可选择安装的真实 Provider**，不会默默使用本地机器发声，也不会在没有网络或模型的情况下冒充合成/对齐成功：

```bash
python -m pip install -r requirements-voice.txt
# 真实强制对齐另行安装 stable-ts / openai-whisper 和所需模型环境
python3 scripts/production_run.py --project project --until voice --allow-network-tts --voice zh-CN-XiaoxiaoNeural
python3 scripts/production_run.py --project project --until alignment --allow-alignment-model --align-model base
# 在项目内准备完整已审核的 visual-plan.json、真实 GPT GIF 候选后：
python3 scripts/production_run.py --project project --until sequence
```

可以先将已有音频放在 `project/audio/voiceover.wav`，直接运行 `--until alignment`。现有音频/对齐文件符合 SHA 和时间码规则就**校验后复用**；错误或过期的结果不会被静默覆盖。网络 TTS 与本地大型对齐模型都必须显式开启。不应在用户没有真实配音环境时拿测试用静音轨代替口播。

这仍是“音频 → 已有视觉素材 → 剪辑草稿”的同步执行器；**不具备从主题全自动生成最终高质量视频的能力**，实际生成 GPT GIF 与整片视觉审阅仍需通过真实工具完成。

### v3.0 · 多候选真实 GIF 调度

先准备不同的逐镜提示词与可用的原始角色参考图，然后按 [GIF 生成后端协议](references/gif-generator-runtime.md) 配置已连接实际生成工具的可信后端。**本仓库不附带一个能凭空调用 Codex GIF 额度的命令**；工具不具备 GIF 生成功能时，调度器必须失败，而不是生成矢量动画或虚报成功。

```bash
python3 scripts/gif_batch.py --project project --tasks project/gif-batch.json --backend-file backend-command.json --workers 2 --timeout 180 --max-attempts 2
```

候选只被登记为 `unreviewed`，仍需要真实查看动画、单候选质量审核和导演选片。生成任务与项目正式发布审核彼此独立。

## 核心规则：GPT GIF ONLY

正式视频**不能用蹩脚的矢量动画、PPT 动图或本地程序化示意图替换 GPT GIF**。如果生成跑题或质量不过关，立即停止正式合成、保留失败 GIF 和 QA 记录。默认 `--asset-mode gpt-only` 在代码层拦截程序化镜头。仅当用户明确授权混合模式，才能指定 `--asset-mode mixed`。ffmpeg 仍用于转码、字幕、音频，不负责替代主要视觉素材。

## 运行时工具限制与严格画幅验收

**重要发现：本会话中的图像工具即使切换了种子发芽等完全不同的画面主题，仍反复返回相同的电脑/大脑/灯泡拼贴 GIF，且输出为横屏。** 这不是可发布的镜头结果。Skill 必须检查生成工具能否真正接收逐镜提示词；无法确认时标记 context_only_unverified，不宣称跑通。

新增 scripts/verify_gif_asset.py：正式镜头要求实际 GIF、有效动作帧、接近原生 9:16、足够尺寸。横屏 GIF 后期加黑边不算通过。详见 references/gif-runtime-contract.md。

## v2 制作方法：先准备素材，再剪辑选片

**制作 GIF 与决定用哪一条 GIF 必须分开。** 同一个知识点可以先准备不同景别、动作、节奏的 A/B/C 候选，存入 library/candidates/；不立即进入正式视频。剪辑时逐个观看、选出最贴合旁白的素材，并登记选片理由。未选素材保留以供重新剪辑，不能偷偷用矢量动画兜底。

- scripts/candidate_pool.py：管理 GIF 候选、原始提示词、来源和最终入选版本。
- scripts/review_workspace.py：生成可浏览的原始动图画廊和选片对照。
- scripts/render_edit_preview.py：把实际选中的 GIF 剪成未审批草稿 MP4，供导演观看。
- 一旦重新选片，旧镜头视觉审核自动失效，必须重新执行注册和质量检查。
- 素材池启用后，正式合成会核对入选候选与登记来源一致，防止 A 的素材冒充 B 的生成记录。
- 详细说明：[素材池与剪辑分离](references/material-library.md)。

### 可视化画廊与草稿剪辑预览

在素材池登记不同 GPT GIF 候选后，先生成一个**只读本地 HTML 画廊**，展示每条实际 GIF 的动态预览、原始提示词、工具来源、尺寸、帧数、技术问题及入选状态：

```bash
python3 scripts/review_workspace.py --project project --storyboard project/storyboard.json
# 用浏览器打开 project/library/review.html
```

观看候选后用 `candidate_pool.py select` 明确选片。确认所选素材全部来自真实 GIF，再导出一条**未审核的剪辑草稿**（不需要先虚报视觉审核）：

```bash
python3 scripts/render_edit_preview.py --project project --storyboard project/storyboard.json
python3 scripts/edit_plan.py --project project --storyboard project/storyboard.json --audio project/audio/voiceover.wav
python3 scripts/review_workspace.py --project project --storyboard project/storyboard.json --edit-plan project/edit-plan.json
```

再次打开画廊即可看到实际草稿 MP4 和可点击跳转的镜头时间线。默认位置为 `project/build/editorial-preview.mp4`，状态强制标为 `UNREVIEWED_EDITORIAL_PREVIEW`。它允许在质量审核前观看完整节奏，但**不能替代正式 GIF QA、剪辑导演签核和成片验收**。没有真实配音的草稿必须明确标注为无声预览。

## v2.2 · 一段口播可以剪出多个 GIF 镜头

**不再把“分镜数量”等同于“成片镜头数量”。** 可以从素材池里的不同候选，自由选择几个特写、全景和动作镜头，决定各自截取的真实 GIF 时间范围，并按输出帧精确排列。新模块是独立的可变镜头剪辑预览器，不替代原有正式 QA。

```bash
# 从已经选好初始候选的素材池建立剪辑草稿
python3 scripts/sequence_cut.py --project project --storyboard project/storyboard.json --init

# 自行编辑 project/sequence.json 中的 clips（可增加来自同一口播段落的多个候选）
python3 scripts/sequence_cut.py --project project --verify
python3 scripts/sequence_cut.py --project project --preview

# 可在本地画廊浏览每个候选，并点击时间线跳转到草稿视频的具体镜头
python3 scripts/review_workspace.py --project project --storyboard project/storyboard.json --sequence project/sequence.json
```

剪辑 v2 使用的是真实候选 GIF 字节，不会画任何矢量替代素材。会检查原始 GIF 的 SHA256、所选时段不超过真实 GIF 时长、时间线无空隙重叠，以及切镜原因。旁白音轨长度不匹配会出警告，且不会悄悄截短音频冒充配音成功。输出明确标记为 **UNREVIEWED_SEQUENCE_PREVIEW**；正式多镜头交付现由 candidate_review.py 和 release_sequence.py 完成独立候选审核、有声字幕合成；成片仍需 final_review.py 实际审片批准。

详细操作：[可变镜头剪辑台](references/sequence-editing.md) 与 [候选独立审核 + 正式成片流程](references/candidate-release.md)。

## v2 剪辑导演：GIF 不等于视频

受到 [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) 和 [Remotion Skills](https://github.com/remotion-dev/skills) 的启发，gif-studio 增加了**真实配音→帧级剪辑决策→整片预览→最终验收**环节。GPT GIF 仍然是唯一默认主要视觉素材，绝不以 Python 矢量动画替代。

- `scripts/edit_plan.py`：基于实际 GIF 长度与真实音轨生成剪辑决策草案。
- 每一镜的 `cut_reason` 都要说明为何在此切镜，不允许只按四等份或 7.5 秒分段。
- 默认单镜末帧定格不得超过该镜时长 25%，避免无聊的大幅停滞。
- 正式视频必须有真实旁白，且音画总时长偏差不超过 0.35 秒；无声素材只能作为明确标记的预览交付。
- 详见 [剪辑导演规范](references/editorial-director.md)。

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
python3 scripts/register_asset.py --project project --storyboard project/storyboard.json --shot shot-01 --kind gpt_gif --tool ACTUAL_TOOL --reference ACTUAL_REFERENCE --prompt project/prompts/shot-01.txt --prompt-delivery explicit_tool_argument
python3 scripts/verify_gif_asset.py --gif project/gifs/shot-01.gif --report project/qa/shot-01.intake.json
python3 scripts/inspect_gif.py --gif project/gifs/shot-01.gif --duration 5 --report project/qa/shot-01.json --contact-sheet project/qa/shot-01-sheet.jpg
# 真实审阅接触表与动画后才能审批（不可自动伪造通过）：
python3 scripts/approve_shot.py --project project --storyboard project/storyboard.json --shot shot-01 --reviewer REVIEWER --notes "记录具体所见" --semantic-pass --motion-pass --style-pass --composition-pass
python3 scripts/project_status.py --project project --storyboard project/storyboard.json
python3 scripts/edit_plan.py --project project --storyboard project/storyboard.json --audio project/audio/voiceover.wav
# 观看完整镜头组合后编辑 cut_reason、review_notes、review_status，并再次验收
python3 scripts/edit_plan.py --project project --storyboard project/storyboard.json --audio project/audio/voiceover.wav --verify
python3 scripts/compose_video.py --project project --storyboard project/storyboard.json --audio project/audio/voiceover.wav --out project/final.mp4 --burn-subtitles
python3 scripts/final_review.py --project project --video project/final.mp4 --inspect
# 真正观看并试听整片后，记录审核结论（不能由生产脚本自己宣布通过）
python3 scripts/final_review.py --project project --video project/final.mp4 --approve --reviewer REVIEWER --notes "逐段审核的具体观察及修改结果" --semantic-pass --pacing-pass --continuity-pass --subtitles-pass --audio-pass
```

正式有声作品要求真实旁白；如果只是无声视觉预览，显式传 `--allow-silent-preview`，不得声称已经交付口播成片。如需严格逐字同步，须提供真实时间戳/对齐结果；一镜头一行字幕并不等于音频自动识别。

默认 GIF 只播放一次；时长不足则**保持末帧**，避免重复时突然跳回首帧。确实无缝循环时可以单独使用 `--duration-mode loop`。如有 QA 问题，默认拒绝合成；`--allow-unreviewed` 仅用于开发调试并应明确向用户披露。

## 参考

- [主 Skill](SKILL.md)
- [视觉导演协议](references/visual-storytelling.md) 与 [生产操作手册](docs/production-pipeline.md)
- [连贯口播写作规范](references/narrative-writing.md) 与 [口播声线](references/voice-profiles.md)
- [多风格目录](presets/styles.json) 与 [导演指南](references/style-guide.md)
- [提示词模板](references/prompt-templates.md)
- [异常排查](docs/troubleshooting.md)
- [可复现的三镜 GPT GIF 试验项目](examples/focus-interruption/) 与 [其他分镜](examples/)

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
