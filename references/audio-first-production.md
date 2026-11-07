# v3.0 Audio-first Visual Director

先锁定完整文案，再**整段**生成或导入真实配音，随后获取真实毫秒级声学对齐。不要把句长按平均字数拆分成伪造的「时间码」。

## 音轨先行

1. `script.json` 必须是已确认全文。
2. `audio/voiceover.wav` 为真实完整配音（可使用实际可用 TTS 或人工录音）。
3. 从合法可用的真实 forced aligner 导入毫秒区间，或人工逐句对齐并记录 reviewer。`audio-timeline.json` 必须附 `audio_sha256`、`duration_ms`、`source.method` 和语音段 text。
4. `scripts/audio_timeline.py` 检查真实音轨长度、SHA、句子的无重叠时间码，以及拼接后逐字与原文一致。它**只验证输入，不生成时间码，也不会假装已经做过 ASR**。
5. `visual-plan.json` 为每段时间码写 A-roll（人物、情绪、叙事）或 B-roll（知识、步骤、比较），以及镜头/素材类型、具体视觉事件和切点理由。A/B-roll 是叙事职责，不是渲染引擎。由 `scripts/visual_plan.py` 检查声音覆盖、时间线连续性与重复节奏。
6. 视频剪辑的最终真相是音轨时间线；原 `sequence.json` 是低层 FFmpeg EDL，要逐步由经过审核的视觉编排推导，不能两套时间线相互独立修改。

## 可执行入口

```bash
python3 scripts/project_flow.py init --project project
python3 scripts/project_flow.py status --project project
python3 scripts/project_flow.py plan --project project
python3 scripts/project_flow.py validate --project project

python3 scripts/audio_timeline.py --timeline project/audio-timeline.json --script project/script.json --audio project/audio/voiceover.wav
python3 scripts/visual_plan.py --plan project/visual-plan.json --timeline project/audio-timeline.json --script project/script.json --audio project/audio/voiceover.wav
```

`project_flow.py` 是第一批**只读诊断与项目清单入口**，不假称它已覆盖所有生产操作；即使全部通过，也不会自动批准发布。后续接入真实 TTS、参考图、生成适配器与流程恢复。

## 参考 xilo 的思路，不照搬插件

- 整段配音后做声学对齐，避免逐句 TTS 声色差异。
- A-roll 需要三视图、笔触和场景参考，可在后续 P0-4 落地。
- B-roll 按知识结构挑选真实素材，准确数据使用可靠的可控叠加，不以矢量图冒充 GPT GIF。
- 候选 GIF 多生成，剪辑时才按语义选片；样片验证通过后才大批量生产。

## 将视觉编排转为可剪辑 GIF 时间线（第一版）

明确为每条 `visual-plan.json.shots[]` 提供 `source_shot_id`、`candidate_id`，需要从 GIF 中部开始时提供 `source_in_ms`。素材必须已经真实生成并进入 `candidate_pool.py`。当前编译器只支持 `media_type=gpt_gif`；其他 B-roll 媒体类型拒绝伪装为 GIF，未来应交给独立的混合媒体渲染器。

```bash
python3 scripts/visual_to_sequence.py --project project \
 --script project/script.json --audio project/audio/voiceover.wav \
 --timeline project/audio-timeline.json --visual-plan project/visual-plan.json \
 --storyboard project/storyboard.json
python3 scripts/sequence_cut.py --project project --storyboard project/storyboard.json --verify
python3 scripts/sequence_cut.py --project project --preview --audio project/audio/voiceover.wav
```

编译器将毫秒音频区间按输出 FPS 转成镜头起止帧；真实 GIF 必须覆盖需要的时长，不能自动末帧定格或重复。产生的 EDL 仍是 `draft`，不等于审片通过。修改原始声音/视觉编排后，已生成的 v3 EDL 必须被重新验证并按需重建，禁止沿用旧审批。
