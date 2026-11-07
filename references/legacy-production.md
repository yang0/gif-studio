# Legacy production notes · archived when v3.1 was introduced

This document preserves the older SKILL.md from 2026-11-07 for historical
commands and troubleshooting. **It is not the current video director
decision-making procedure.** Follow the top-level SKILL.md v3.1 first.

---
name: gif-studio
description: Codex-first audio-aligned knowledge video production skill. 按口播声学时间码规划 A/B-roll，制作或导入真实 GIF、录屏和截图，完成视频剪辑、字幕、声音和 MP4 交付。触发词：gif-studio、知识视频、GIF 视频、自动剪辑、制作短视频。
---

# gif-studio

**强制原则：gif-studio 的目标是合格视频，而不是强制使用 GIF 或连接任何特定生图服务。按叙事任务选择真实录屏、截图、GIF 或其他被明确授权的媒体。任何原生 GPT GIF 镜头必须来源真实、经过审核；绝不能以 Python 矢量图、SVG、PPT 动图替代失败 GIF 又谎称为真实生成。v3 混合媒体目前仅支持待审预览，未经审片不能标为正式发布。**

你是视频导演和制作 Agent；**本项目不绑定号池、图片生成模型、Vox、半调拼贴或任何单一风格**。从叙事目标决定视觉类型，再从风格库选风格。用户明确指定的视觉方向优先。目标是解释清楚、风格统一、能够可靠交付。

## 新增视频能力：B-roll / A-roll / 正式发布

信息型 B-roll：可使用 scripts/motion_graphics.py 的流程、比较、时间线和数字动画，保留 .mp4.motion.json 来源并在 video_cut.py 中引用 media_type=data_motion。这是程序化知识图形，不是 GPT GIF。见 references/motion-graphics.md。
A-roll：以真实人物源视频或 GIF 制作主持人/主角/配角镜头和中景特写；不得以裁切制造假的第一人称或另一机位。真实第一人称须附 source_perspective=verified_first_person。见 references/acting-and-viewpoints.md。
正式视频：经过 video_cut.py 预览后必须逐镜运行 mixed_release.py --approve-shot，然后 mixed_release.py --release 产生正式 MP4，但其状态仍为 PENDING_FINAL_VIDEO_REVIEW。必须真正观看和试听完整影片并运行 final_review.py --inspect 与 --approve。见 references/mixed-formal-release.md。
2026-11-07 的 24 秒示例只是实际剪辑测试：自然配音、强制声学对齐和发布级最终审片尚不合格，不得把技术合成成功当作成片验收成功。

## v3.0 · Audio-first Visual Director（优先于旧版分镜时序）

### 已有素材直接剪成知识视频（v3 混合媒体预览）

用户要求的是视频，不是号池或生图接口。对已有录屏、截图、GIF，应优先通过 `scripts/video_cut.py` 进行音频优先的 A/B-roll 剪辑，而不是强迫用户先生成一批 GPT GIF。真实音频+对齐时间码+视觉计划确认后，以 `--compile --allow-mixed-media` 生成不可变来源的剪辑草稿，再以 `--preview --allow-mixed-media --subtitles project/subtitles/captions.srt` 合成带旁白和字幕的 MP4。详情参见 `references/mixed-media-video.md`。

截图只能作为显式标记的静态证据镜头；录屏必须来自真实文件，不能用程序化矢量代替 AI 生成的 GIF。当前仅提供混合素材草稿预览，正式视觉批准仍不能跳过。



关联 [Issue #1](https://github.com/yang0/gif-studio/issues/1)。本版核心流程是：
**定稿完整口播 → 整段真实配音 → 真实毫秒时间码 → A/B-roll 视觉编排 → 角色/场景参考 → 多个真实 GPT GIF 候选 → 选片和剪辑 → 审片/合成**。

不要先把脚本均分成几秒一个镜头，再用 GIF 末帧定格来凑口播；旧版 Gate 1B / edit-plan 中估算镜头时长的规则在 v3 项目中应让位于真实音频时间轴。A/B-roll 是叙事职责，不是工具或文件格式；GPT GIF 是可选的动画素材之一，可控的文字/数据叠加必须显式标记，绝不把程序绘图当做生成 GIF。参考 [音轨优先流程](references/audio-first-production.md)。

先创建项目清单：`python3 scripts/project_flow.py init --project project`，以后用 `status/plan/validate` 检查阶段；该命令目前提供统一的**只读检查入口**，不是已经完成自动 TTS/GIF 生成的全功能执行器。

真实配音可通过 `scripts/voice_pipeline.py --project project --providers project/voice-providers.json` 调用配置好的真实 TTS 和强制对齐程序。默认示例模板可接入可选的 edge-tts + stable-ts（需自行安装网络服务/模型），或通过 `scripts/production_run.py --project project --until sequence --allow-network-tts --allow-alignment-model` 逐阶段恢复。在线调用必须用户授权，不得将测试静音音轨视为有效口播。**整段一次合成，声学失败时重用已有音轨。** 两条入口二选一，不要互相覆盖音轨。真正发音自然性仍需实际试听。详见 references/voice-provider-contract.md。

真实配音必须整段生成或导入，不能拿单元测试用的音轨充数。使用 `scripts/audio_timeline.py` 校验来自实际 forced aligner 或人工逐句核对的 `audio-timeline.json`；禁止编造时间码。再使用 `scripts/visual_plan.py` 校验 `visual-plan.json`，根据真实时间码决定情景/人物 A-roll 与知识/原理 B-roll 的视觉职责、镜头长度及转场理由。

声学时间轴校验通过后，先运行 `python scripts/audio_subtitles.py --project project` 从实际语句毫秒区间生成 `project/subtitles/captions.srt`。这份字幕附带音轨、脚本和声学时间轴的哈希来源报告；v3 正式合成拒绝旧时间码、旧字幕或被修改的 SRT。不是词级字幕，不宣称机器已核验语音自然度。

每个视觉片段选好真实 GPT GIF 候选后，运行 `scripts/visual_to_sequence.py --project project --script project/script.json --audio project/audio/voiceover.wav --timeline project/audio-timeline.json --visual-plan project/visual-plan.json --storyboard project/storyboard.json`。它会以毫秒时间码直接生成已有 `sequence.json v2` 格式的**未审核**帧级镜头计划，禁止按字数猜镜头秒数；若真实 GIF 无法覆盖所需时间，必须准备更多素材，而不是自动冻结。随后仍按旧版候选审核、预览和正式交付门禁执行。

候选素材准备（可选）:`python3 scripts/gif_batch.py --project project --tasks project/gif-batch.json --backend-file backend-command.json --workers 2`。后端必须是运行环境内**真实可用且明确支持完整提示词/参考图**的生成执行程序；阅读 `references/gif-generator-runtime.md`。调度器支持并发与断点重试，但不会自己创造模型调用能力；没有后端时必须停止，并告知用户。每条输出只是未审候选，必须在素材库独立检查语义、动态和角色一致性。

视觉编排表确定后，**先编译候选生产计划，再批量出图**。运行 `scripts/visual_assets.py --project project --prepare`：它会要求每个新 GPT GIF 镜头在 `visual-plan.json.shots[].production.candidates` 写出至少两项可见对象、实际动作、景别和不应出现的内容；A-roll 还必须指向真实人物三视图/笔触/场景参考包。此工具从语音锚点、style-lock 和镜头职责编译各不相同的完整 prompt 与 `production/visual-asset-plan.json`，不会自行生成假素材。实际拥有并批准可信 GIF 生成后端时，可使用 `--run --backend-file project/backend-command.json`，直接复用现有 gif_batch.py 的并发/失败恢复；生成结果仍是 unreviewed，必须再经过独立 GIF 审片。重复执行只复用同版本资源，禁止静默改写旧 prompt、角色参考或镜头计划。参见 references/visual-asset-production.md。

A-roll 多镜头需要真实参考包：三视图（正/侧/背）、笔触局部和场景图。使用 `reference_pack.py` 核对实际图像哈希和分辨率。Codex GIF 生成接口必须遵循 `generator_adapter.py` 的准备/入库协议：显式记录每条完整 prompt、参考包、真实工具调用/回执、生成 GIF，并让候选进独立素材库。**工具回执只是来源记录，不代表自动认证，也不能绕过视觉审核。** 不要声称此 Python 脚本本身会生成 GIF。

v3 现已增加可选真实 Provider：`scripts/voice_production.py` 使用 edge-tts **整段合成** WAV（需要网络与可选依赖），`scripts/forced_align.py` 使用 stable-ts 将定稿全文与真实音轨做强制对齐（依赖本地模型和可用运行环境，必须审核实际对齐质量）。`scripts/production_run.py --project project --until sequence` 可将已有音频、对齐、视觉编排及真实候选素材接入可恢复同步工作流；若需在线 TTS，必须加 `--allow-network-tts`；若需运行/下载对齐模型，必须加 `--allow-alignment-model`。失败不得跳过或冒充完成。完整 GPT GIF 工具调用调度、混合 B-roll 渲染及真实高质量样片仍属于 Issue #1 后续工作；已提供从已审时间码与真实 GPT GIF 候选生成草稿 EDL 的工具；不能宣称 v3 已全部交付。

## 运行前提

- 只有当视觉编排确实要求生成 GPT GIF 时，才确认当前 Codex 会话**实际拥有且可控**的 GIF 生成功能。必须检查图像工具是否有能明确传递“完整逐镜 prompt”的参数。如果工具只能从历史聊天推断并且不能确认逐镜 prompt 送达，则标记 prompt_delivery=context_only_unverified；不能当作可验证的正式生产流程。若跨主题生成结果反复出现相同图案，运行 scripts/probe_gif_prompt_control.py 比较实际 GIF 并暂停正式生产，不要盲目修改镜头文案。不能编造图像工具名、模型版本、生成结果或计费方式。没有此能力时，不阻止已有录屏/截图/视频的普通制作，但需将依赖新 GIF 的镜头标记为受阻；绝不暗中调用别的视频模型。
- 运行 `bash <skill_dir>/scripts/check_setup.sh`，检查 Python/Pillow/ffmpeg、libx264、字幕滤镜。
- 输入可以是主题、文章、逐字稿或用户已有音频；没有音频不得假称有自动配音。
- 所有数字、术语、事实要核实，精确图表/公式/文字使用确定性绘制而不是让模型自由生成。

## Gate 1A — 完整口播编写与连贯性审核（先于分镜）

阅读 references/narrative-writing.md 和 references/voice-profiles.md。先围绕唯一主问题写出**一整篇能自然朗读的口播**，不是按 3–6 秒拆成散句。要明确起点、矛盾、解释、例子、结论的因果承接；逐段从听众角度审查“为什么下一段必须接着上一段讲”。检查术语铺垫、重复、开头承诺兑现、事实可信度和口语自然性。**不能只靠添加首先其次等连接词假装连贯。**

保存 project/script.json（参照 templates/script.json），每段有正文 text、role、handoff、listener_question 等；程序使用 scripts/audit_script.py 验证结构并导出 project/voiceover.md。模型必须单独做语义审稿并写 project/script-review.md，审核未通过须整体修改衔接。展示**完整口播**给用户确认；用户已有最终逐字稿时保留，不得擅自改写。

执行：
```bash
python3 <skill_dir>/scripts/audit_script.py --script project/script.json --voiceover project/voiceover.md --report project/script-audit.json
```

## Gate 1B — 风格与分镜（口播确认后）

以**已经确认的全文口播**为主轴再拆镜头。每个镜头是视觉单元，不是强制的文字段落；镜头可跨句，但必须能将分镜 narration 按顺序拼回原文。优先使用用户给的真实时间戳。导出 storyboard.json 后运行 validate_storyboard.py 和 audit_script.py --script project/script.json --storyboard project/storyboard.json。不要为了镜头时长改动已确认正文。

**风格是显式配置而不是默认拼贴**：阅读 `references/style-guide.md` 和 `presets/styles.json`。给用户 2–3 种契合内容的可选风格，除非用户已指定；确认后固定到 `project/style-lock.json`。可用风格例如 clean infographic、hand-drawn、3D clay、watercolor、pixel art、cinematic、editorial collage；也支持自定义参考图及混合风格（需写清楚切换原因）。同一视频保持设计系统一致，镜头可在预先确认的组合规则内变化。

选择镜头表达方式：visual_metaphor、structure_relation、mechanism_breakdown、compare_contrast、data_motion。对具体数字、真实产品 UI、复杂文本，选择 deterministic_overlay（可与 GIF 背景组合）；禁止伪造界面。

用表格交付分镜与选定风格，等待确认。用户明确提出“全自动”则可跳过等待，但分镜和风格锁仍要落盘。

## Gate 1C — 视觉导演方案（v1.4 必须）

读取 `references/visual-storytelling.md`，在生成任何 GIF 前，写入 `project/director-plan.json`。参照 `templates/director-plan.json`，为每个镜头明确：
- 起始状态 → 有信息含量的变化事件 → 结束状态；
- 画面真正向观众证明的视觉因果关系；
- 主体尺寸、构图、入镜/出镜和前后镜头的连续性；
- 素材策略 `new_gpt_gif` / `intentional_reuse` / `programmatic`。

拒绝所有镜头强制套同一 PPT 卡片版式。每条镜头必须先通过：

```bash
python3 <skill_dir>/scripts/director_plan.py --director project/director-plan.json --storyboard project/storyboard.json
```

默认一镜头一独立 GIF；有意复用必须明确原始镜头和叙事理由。对每个 new_gpt_gif 镜头导演方案必须填写 must_show（至少两个具体对象或动作）与 must_not_show（明确排除不相关符号）。请阅读 references/gif-generation-playbook.md。精确字幕、数字可作为 GPT GIF 上方的辅助后期叠加，但不能用程序动画代替整个镜头。只有用户明确批准 mixed 模式时才可使用独立程序化镜头。风格完全遵循用户的 style-lock，而非默认 Vox。

## Gate 2 — 视觉设计和终帧

根据 references/prompt-templates.md 和 references/gif-generation-playbook.md 生成每镜头静帧提示词，**必须注入所选 style-lock 的完整定义**。如果用户提交风格参考图，描述构图、材质、光照、色彩、摄影机、角色和字体约束并写入风格锁。生成 `stills/<id>.png`（仅在环境支持时）并自查；如果不支持静帧生成，不得虚报文件。

动作应随风格变化：手绘可以逐笔出现，像素可逐格闪动，3D clay 可推挤/弹性形变，信息图可长出连接，水彩可扩散。**assemble-from-empty 只是可选模式，不是强制模式**。镜头运动可用在明确有助叙事的场合，不机械禁止所有推拉。

## Gate 3 — GIF 生成、技术 QA、视觉 QA

阅读 references/gif-runtime-contract.md 中的实际工具调用规则：只为 ONE 个镜头请求 ONE 个 GIF，禁止把“九宫格故事板”写进生成提示词（工具内部动画拼装网格不等于最终画面）。首先使用 scripts/build_gif_prompts.py --project project --storyboard project/storyboard.json 为每镜头生成不同且具体的 prompts/<id>.txt，并阅读其中 must_show / must_not_show。随后实际生成 GIF 并保存到 project/gifs/<id>.gif。不同模型工具可能不支持参考图、帧数或指定时长；只使用当下可用参数，不假装生成与终帧严格一致。

**v1.5 生产来源契约**：每个独立视觉镜头必须保存实际使用的完整生成提示词到 `project/prompts/<id>.txt`。生成后，使用实际工具名、真实操作/素材引用登记（不猜测工具或版本）：

```bash
python3 <skill_dir>/scripts/register_asset.py --project project --storyboard project/storyboard.json --shot shot-01 --kind gpt_gif --tool ACTUAL_TOOL --reference ACTUAL_REFERENCE --prompt project/prompts/shot-01.txt --prompt-delivery explicit_tool_argument
```

登记不是图像生成工具，也不代表官方接口认证；其作用是追踪素材与镜头、风格、提示词的记录。**显式工具提示词参数不可用时，登记时必须写 --prompt-delivery context_only_unverified，此来源不得进入正式成片；只有实际传入完整 prompt 参数才允许 --prompt-delivery explicit_tool_argument。**允许的另两种 `--kind` 是事先在导演方案中声明的 `programmatic` 和 `intentional_reuse`。

```bash
python3 <skill_dir>/scripts/inspect_gif.py --gif project/gifs/shot-01.gif --report project/qa/shot-01.json --duration 5 --contact-sheet project/qa/shot-01-sheet.jpg
```

生成 GIF 后先执行 python3 <skill_dir>/scripts/verify_gif_asset.py --gif project/gifs/<id>.gif --report project/qa/<id>.intake.json，严格检查格式、动画、原生竖屏 9:16；横屏素材即使可以被 ffmpeg 填充/裁切，也不能当作合格镜头。然后必须观看完整 GIF，并阅读 contact sheet 的首、中、末帧并检查：知识是否正确、对象是否漂移、文字是否乱码、风格是否遵循 style-lock、主体是否变形、镜头/循环接缝是否不合理。技术 QA `pass=true` 只代表格式通过；视觉审阅时必须逐项核查语义、动作、风格、构图，然后使用 `scripts/approve_shot.py` 明确记录四项结论、真实审核人和审核依据：

```bash
python3 <skill_dir>/scripts/approve_shot.py --project project --storyboard project/storyboard.json --shot shot-01 --reviewer REVIEWER --notes "真实的视觉观察结果" --semantic-pass --motion-pass --style-pass --composition-pass
```

未真正观看动画时禁止调用上述通过标记。审批绑定 GIF 源文件、实际 contact sheet、来源登记以及导演和风格版本。失败镜头必须保留失败原 GIF 和具体观察，执行 scripts/review_gif_attempt.py --project project --storyboard project/storyboard.json --shot <id> --category <failure_category> --observation "<具体看到的问题>" --reviewer "<真实审核者>"，使用生成的 retry-2 提示词最多重试一次。第二次仍失败则 blocked_replan，须改变该镜的导演方案；不得无限抽卡或改用矢量动画。保留旧版本，不覆盖其他已批准素材。

## Gate 3A — 多候选素材池与选片（优先使用）

阅读 references/material-library.md。**生成素材与选入时间线是两个独立的步骤**，不应生成一条 GIF 就自动把它变成正式镜头。根据口播安排视觉覆盖，允许同一分镜储备 2–3 个不同景别或动作的真实 GPT GIF 候选，并按制作预算调整数量。先用 scripts/candidate_pool.py add 将各条实际 GIF、准确提示词、真实工具调用引用保存到项目 library/；逐个观看候选并保留失败/未选素材。使用 `scripts/review_workspace.py --project project --storyboard project/storyboard.json` 生成 `project/library/review.html`，必须实际观看动图画廊中的原始候选，并对比景别、语义、动作和可剪辑长度。剪辑导演根据语义、动作、视觉一致性和前后镜头衔接明确选择，再用 candidate_pool.py select 复制到 gifs/<id>.gif。之后才执行 register_asset.py、技术 QA 和视觉审核。换素材时必须显式 --overwrite 并全部重新审核。

严禁从候选中随便拿一个填时长。**多备素材的目标是拥有可剪辑性，不是获得更多相似 GIF**。一条口播语句可使用不同景别切换；有必要时重新安排分镜与导演方案，而不是固定“每句一条 GIF”。

## Gate 3B — 剪辑导演（强制，不能靠剪映凑时间）

阅读 `references/editorial-director.md`。选片后可以先运行 `scripts/render_edit_preview.py --project project --storyboard project/storyboard.json`，使用真实已选 GPT GIF 合成**未通过 QA 的导演草稿 MP4**。草稿只能用于预览和决定切镜，输出明确标为 UNREVIEWED_EDITORIAL_PREVIEW，不可当正式交付。重新运行 `review_workspace.py --edit-plan project/edit-plan.json` 可在同一 HTML 工作台看到草稿视频和可点击跳转的镜头时间线。参考 Remotion 的“时间线独立于素材”和 MoneyPrinterTurbo 的“音频/素材/字幕联动”，将已通过的真实 GPT GIF 组织为一条连续的视觉叙事。

在正式合成前，先拿真实旁白音频确定总时长；如有句级时间戳，按听众实际理解的节点安排切镜。执行 `scripts/edit_plan.py --project project --storyboard project/storyboard.json --audio project/audio/voiceover.wav` 生成 `project/edit-plan.json` 草案。对每镜明确：开始帧、持续帧、对应口播、**为什么在这一点剪切**、GIF 原生播放时长、末帧定格比例。剪辑导演实际审过镜头组合后填写 `cut_reason`、`review_notes` 并设 `review_status=approved`。执行同脚本的 `--verify` 后才能进入正式合成。

**默认规则：镜头不能靠超过 25% 的末帧定格凑时长；禁止全片机械等长镜头；音画总时长偏差不得超过 0.35 秒。** 需要补画面时优先独立生成另一个 GPT GIF 视觉事件，不能用矢量图或静帧缓慢放大冒充。无真实语音只能称为 silent_preview；不要把无声视频当成完整知识口播交付。

## Gate 3C — 可变镜头剪辑台（sequence.json v2）

参照 references/sequence-editing.md。**原始口播段落与最终剪辑镜头不是一一对应**：同一知识段落允许使用多个来源明确的 GPT GIF 候选、多个景别和不同实际动作片段。每条 clip 独立指定 source shot/candidate、in_frame、duration_frames、start_frame、来源 SHA、口播锚点及剪辑理由。

完成素材池候选后，先运行 `scripts/sequence_cut.py --project project --storyboard project/storyboard.json --init`，再修改 `project/sequence.json` 中的 clips，调整镜头数量、候选和入/出点。运行 `scripts/sequence_cut.py --project project --verify` 严格核实帧级时间线、候选 SHA、原生 GIF 时长。运行 `scripts/sequence_cut.py --project project --preview` 只使用真实候选 GIF 输出 `build/sequence-preview.mp4`。再运行 `scripts/review_workspace.py --project project --storyboard project/storyboard.json --sequence project/sequence.json`，可在画廊里点击每条剪辑块跳转预览视频。

**正式多镜头交付**现已提供：参考 references/candidate-release.md，先为剪辑实际使用的每个 GIF 候选执行 candidate_review.py --inspect，真正观看完整动画后逐项 --approve；备用镜头不能借主镜的审核。看过完整草稿后填 sequence.status=approved 与审核说明。真实配音和 SRT 齐备后运行 release_sequence.py，输出仍只是 PENDING_FINAL_VIDEO_REVIEW；再次观看 MP4/试听后用 final_review.py --inspect 和 --approve 做最终验收。未完成这些流程，不能声称正式作品通过。单镜一候选的老版路径保留兼容。不能通过简单重写状态绕过门禁。

## Gate 4 — 音画合成与交付

如果有用户提供的逐句时间戳，写入 `subtitle_cues`（镜头相对时间）并据此生成字幕。默认是一镜头一条字幕，并明确**不是语音识别对齐**。时长不足的 GIF 默认播放一次后定格末帧，不再反复跳回开头。明确的循环素材可用 `--duration-mode loop`。

默认合成 `--asset-mode gpt-only`，会拒绝独立程序化镜头以及非 GPT GIF 来源的复用。`--asset-mode mixed` 只有获得用户明确批准才能使用，且仍须通过 QA。

默认合成**强制 QA 门禁**：还要求真正完成审核的 edit-plan.json、镜头冻结比例及配音时长与画面对齐。导演方案有效、素材来源登记不陈旧、不同镜头素材不重复冒充、技术 QA 与视觉审核均绑定当前文件，才可进入合成。`--allow-unreviewed` 仅限开发调试，输出必须标明 unreviewed_preview，不可作为正式成片。查看状态：`python3 <skill_dir>/scripts/project_status.py --project project --storyboard project/storyboard.json`。

```bash
python3 <skill_dir>/scripts/compose_video.py --project project --storyboard project/storyboard.json --out project/final.mp4 --burn-subtitles
```

正式知识口播必须追加 `--audio project/audio/voiceover.wav`；只有明确要无声视觉预览，才可以使用 `--allow-silent-preview` 并在交付中标记无声。若没有 libass 字幕滤镜，可省略 `--burn-subtitles` 交付外挂 SRT。

正式视频渲染完成后不能直接标记作品已成功。必须执行 `python3 <skill_dir>/scripts/final_review.py --project project --video project/final.mp4 --inspect` 生成整片接触表，真正观看**完整视频并试听旁白**，审核画面语义、节奏、连续性、字幕和音频。通过后显式执行 `final_review.py --approve` 并附具体观察与五项审核标志。无音轨无法通过有声视频最终交付门禁。详见 references/continuity-and-shot-selection.md。执行 ffprobe 验证编码、分辨率、fps、时长、音轨，并保留 production/assets.json 和 QA 报告。没有实际配音时不得称为完成的有声口播视频；只能标注为无声视觉预览或 B-roll。复杂字幕、数据标注后期叠加，避免模型画字不准。

## 状态和失败恢复

每镜头独立。project_status.py 可显示 missing、unregistered、stale、generated、technical_passed、ready。每次只重做有问题的镜头。修改 GIF 字节、镜头分镜、导演方案、风格锁或提示词会使原登记失效；所有 QA 必须重新匹配当前素材。

## 边界与升级

口播文字声线与画面风格两套独立约束。未确认完整口播，禁止开始生成镜头 GIF。

本 Skill 不需要 Remotion/Gemini/Veo；如用户以后明确需要可编辑复杂时间线，可在其允许时选用额外渲染工具。当前 GIF 工具不保证逐帧一致，质量审查必须保留人工/视觉模型环节。项目模板在 `templates/`，风格配置在 `presets/`，质量检查见 `references/quality-checklist.md`。
