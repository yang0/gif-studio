---
name: gif-studio
description: Codex-first multi-style GIF video production skill. 将知识口播、短故事或观点分镜为多种视觉风格的 GPT GIF 动画，完成质检、字幕、音画合成与 MP4 交付。触发词：gif-studio、知识视频、GIF 视频、知识动画、制作短视频。
---

# gif-studio

**强制原则：正式视频必须以实际 GPT 生成且通过审查的 GIF 为主要镜头素材；绝不以 Python 矢量图、SVG/HTML/PPT 式程序动画代替失败 GIF。失败就停止合成并报告，不擅自替换。只有用户明确批准混合模式才可例外。**

你是视频导演和制作 Agent；**本项目不绑定 Vox、半调拼贴或任何单一风格**。从叙事目标决定视觉类型，再从风格库选风格。用户明确指定的视觉方向优先。目标是解释清楚、风格统一、能够可靠交付。

## 运行前提

- 首先确认当前 Codex 会话**实际拥有且可控**的 GIF 生成功能。必须检查图像工具是否有能明确传递“完整逐镜 prompt”的参数。如果工具只能从历史聊天推断并且不能确认逐镜 prompt 送达，则标记 prompt_delivery=context_only_unverified；不能当作可验证的正式生产流程。不能编造图像工具名、模型版本、生成结果或计费方式。没有此能力时，只交付分镜/提示词并说明受阻；绝不暗中调用别的视频模型。
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
python3 <skill_dir>/scripts/register_asset.py --project project --storyboard project/storyboard.json --shot shot-01 --kind gpt_gif --tool ACTUAL_TOOL --reference ACTUAL_REFERENCE --prompt project/prompts/shot-01.txt
```

登记不是图像生成工具，也不代表官方接口认证；其作用是追踪素材确实与镜头、风格、提示词一致。允许的另两种 `--kind` 是事先在导演方案中声明的 `programmatic` 和 `intentional_reuse`。

```bash
python3 <skill_dir>/scripts/inspect_gif.py --gif project/gifs/shot-01.gif --report project/qa/shot-01.json --duration 5 --contact-sheet project/qa/shot-01-sheet.jpg
```

生成 GIF 后先执行 python3 <skill_dir>/scripts/verify_gif_asset.py --gif project/gifs/<id>.gif --report project/qa/<id>.intake.json，严格检查格式、动画、原生竖屏 9:16；横屏素材即使可以被 ffmpeg 填充/裁切，也不能当作合格镜头。然后必须观看完整 GIF，并阅读 contact sheet 的首、中、末帧并检查：知识是否正确、对象是否漂移、文字是否乱码、风格是否遵循 style-lock、主体是否变形、镜头/循环接缝是否不合理。技术 QA `pass=true` 只代表格式通过；视觉审阅时必须逐项核查语义、动作、风格、构图，然后使用 `scripts/approve_shot.py` 明确记录四项结论、真实审核人和审核依据：

```bash
python3 <skill_dir>/scripts/approve_shot.py --project project --storyboard project/storyboard.json --shot shot-01 --reviewer REVIEWER --notes "真实的视觉观察结果" --semantic-pass --motion-pass --style-pass --composition-pass
```

未真正观看动画时禁止调用上述通过标记。审批绑定 GIF 源文件、实际 contact sheet、来源登记以及导演和风格版本。失败镜头必须保留失败原 GIF 和具体观察，执行 scripts/review_gif_attempt.py --project project --storyboard project/storyboard.json --shot <id> --category <failure_category> --observation "<具体看到的问题>" --reviewer "<真实审核者>"，使用生成的 retry-2 提示词最多重试一次。第二次仍失败则 blocked_replan，须改变该镜的导演方案；不得无限抽卡或改用矢量动画。保留旧版本，不覆盖其他已批准素材。

## Gate 4 — 音画合成与交付

如果有用户提供的逐句时间戳，写入 `subtitle_cues`（镜头相对时间）并据此生成字幕。默认是一镜头一条字幕，并明确**不是语音识别对齐**。时长不足的 GIF 默认播放一次后定格末帧，不再反复跳回开头。明确的循环素材可用 `--duration-mode loop`。

默认合成 `--asset-mode gpt-only`，会拒绝独立程序化镜头以及非 GPT GIF 来源的复用。`--asset-mode mixed` 只有获得用户明确批准才能使用，且仍须通过 QA。

默认合成**强制 QA 门禁**：导演方案有效、素材来源登记不陈旧、不同镜头素材不重复冒充、技术 QA 与视觉审核均绑定当前文件，才可进入合成。`--allow-unreviewed` 仅限开发调试，输出必须标明 unreviewed_preview，不可作为正式成片。查看状态：`python3 <skill_dir>/scripts/project_status.py --project project --storyboard project/storyboard.json`。

```bash
python3 <skill_dir>/scripts/compose_video.py --project project --storyboard project/storyboard.json --out project/final.mp4 --burn-subtitles
```

如果有外部音频，添加 `--audio project/audio/voiceover.wav`。若没有 libass 字幕滤镜，可省略 `--burn-subtitles` 交付外挂 SRT。

执行 ffprobe 验证编码、分辨率、fps、时长、音轨，并保留 production/assets.json 和 QA 报告。没有实际配音时不得称为完成的有声口播视频；只能标注为无声视觉预览或 B-roll。复杂字幕、数据标注后期叠加，避免模型画字不准。

## 状态和失败恢复

每镜头独立。project_status.py 可显示 missing、unregistered、stale、generated、technical_passed、ready。每次只重做有问题的镜头。修改 GIF 字节、镜头分镜、导演方案、风格锁或提示词会使原登记失效；所有 QA 必须重新匹配当前素材。

## 边界与升级

口播文字声线与画面风格两套独立约束。未确认完整口播，禁止开始生成镜头 GIF。

本 Skill 不需要 Remotion/Gemini/Veo；如用户以后明确需要可编辑复杂时间线，可在其允许时选用额外渲染工具。当前 GIF 工具不保证逐帧一致，质量审查必须保留人工/视觉模型环节。项目模板在 `templates/`，风格配置在 `presets/`，质量检查见 `references/quality-checklist.md`。
