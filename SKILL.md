---
name: gif-studio
description: Codex-first video director/editor. 用真实配音和真实 AI 视频/GIF、实拍、录屏做知识视频，分镜、素材审片、FFmpeg 剪辑、局部返工；绝不使用矢量/程序动画补视频。
---

# gif-studio · 作品优先的制作 Skill

**视频效果是目标，代码只是工具。** Codex 负责理解内容、设计镜头、判断观感；真实图像/视频模型、实拍和录屏提供画面；Python/FFmpeg 仅负责素材校验、剪辑、字幕、声音和技术审查。**GIF 是可选素材，绝不绑定某个模型、号池、收费接口或 Docker。**

## 不可绕过的素材红线

- **禁止 SVG / Pillow / Canvas / 程序绘图 / FFmpeg drawbox、drawtext 卡片动画 / PPT 式信息图充当主体画面。** 更换程序绘图技术仍然禁止。
- **无真实素材就停止。** 不用矢量图、空镜、重复图、定格帧或 TTS 假配音凑成 MP4。严禁把实际未调用的 AI 模型登记为已使用。
- 允许真实拍摄视频、合法素材、实际录屏、可追溯的生成模型 GIF/视频，以及**明确标为静态证据**的真实截图/照片；字幕只是叠加，不是视频主体。
- 每个镜头记录真实来源和源文件 SHA256。来源声明与技术测试都**不能替代**实际审片。
- 历史 `motion_graphics` / `data_motion` / v1-v3 老流程只在 legacy 维护，不再进入默认创作与交付。

## 只保留六个制作步骤

1. **脚本与声音**：完成 20–30 秒知识口播；录制或使用经过实际试听的自然完整中文配音，按真实录音做声学对齐，严禁按字数均分伪造时间码。
2. **导演（Codex 亲自做）**：逐镜交代人物动机、初态→触发→动作→结果，或具体展示知识机制；标注为什么切镜、观众额外看懂什么。至少提供可比较的不同镜头方案；不要用代码模板自动编造创意。
3. **真实素材**：先做一个合格镜头，亲自检查主体、动作、角色和一致性，再扩展素材。GIF/视频模型生成是真实调用并登记原始文件、工具与参考信息；真实录屏保留原件；没有素材就列出缺口。
4. **剪辑预览**：根据真实声音和动作事件决定切点，FFmpeg 只做剪辑/混音/字幕；输出永远是 `UNREVIEWED_MIXED_PREVIEW`。
5. **看片返工**：实际观看、听完整片；记录具体镜头缺陷；仅重做失败片段，来源变化必须令旧审批失效。五维内容/视觉/节奏/声音/连贯性 ≥80/100，单项 ≥6/10 且无严重知识/音画问题，才可提交独立最终审核。
6. **正式发布**：逐镜来源审查 + `mixed_release.py` + `final_review.py`；没有真正人工/视觉审片证据，不得宣称发布质量达标。

## 最少命令：先判断能不能做，再制作

```bash
# 新项目（只建配置，不假造音轨/素材）
python scripts/project_flow.py init --project project

# 配置真实 script.json、audio/voiceover.wav 和 audio-timeline.json，
# 由 Codex 完成 visual-plan.json、director-v2.json 与 storyboard.json。
# 根据 references/real-source-contract.md 登记每镜 source_provenance。

# 在渲染前逐镜列出真实素材缺口，非零退出 = 不准继续
python scripts/real_source_gate.py --project project --report project/quality/media-gaps.json

# 只有真实素材与导演、声音、字幕文件都有效时才能合成未审预览
python scripts/production_run.py --project project --until mixed_preview

# 实际 MP4 技术风险证据（不是自动打分）
python scripts/video_critic.py --video project/build/mixed-preview.mp4 \
  --plan project/video-plan.json --subtitles project/subtitles/captions.srt \
  --report project/quality/critic.json

# 查看各阶段是否存在阻塞
python scripts/project_flow.py status --project project
```

**契约与命令细节**：[真实素材门禁](references/real-source-contract.md) · [声学流程](references/audio-first-production.md) · [真实导演/审片/返工](references/v31-execution.md) · [发布门禁](references/mixed-formal-release.md)。

**特别注意**：`project_flow.py` 不代写导演方案。Codex 需要使用 `director_brief_agent.py` 生成任务并实际写出 `shot-briefs.json`，用 `visual_director.py` 校验导演结果；不满足则停止。导演完整格式见 [导演契约](references/quality-director-v31.md)。

## 验收现实

此前 Pillow/图形卡片预览、机械 espeak 测试音轨**作废**，不能作为 Golden Sample 候选。正式 20–30 秒同题样片要求自然中文配音、实际音频对齐、角色/场景一致、画面确实有新信息、可追溯素材及独立全片观看/试听。**CI 通过不等于艺术质量通过。** 未达标保持 [Issue #2](https://github.com/yang0/gif-studio/issues/2) 开放。

## Legacy

旧的构图动效实验、数据动画、 v1/v2/v3 脚本可供兼容读取或单元测试技术夹具，不再作为推荐视频生产路径，不能绕过真实素材与发布门禁。见 [legacy 操作](references/legacy-production.md)、[历史 README](references/legacy-readme.md)。新的工作请遵循 [Issue #3](https://github.com/yang0/gif-studio/issues/3)。
