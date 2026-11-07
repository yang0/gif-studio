---
name: gif-studio
description: Codex-first video director and editor for narrated knowledge videos. 根据真实音轨策划 A/B-roll、镜头行为、剪辑节奏及视觉表达，制作或导入真实素材，完成真实审片与可恢复局部返工。触发：gif-studio、知识视频、视频自动剪辑、GIF 动画、视觉导演。
---

# gif-studio · Video Director v3.1

**唯一目标：交付真正能看的视频。** 不能以“能把 GIF 拼成 MP4”“CI 全绿”“所有 QA 字段打勾”冒充成片质量。项目不绑定号池、单一生图模型或任何固定画风。已有录屏、GIF、图片、真实视频都可使用；图形动效明确标为信息图，绝不假冒 AI 生成素材。

## 视觉素材红线（强制）

- **禁止用 SVG、Pillow、Canvas、程序绘图、矢量卡片或 PPT 式信息图制作、充当或填充视频镜头。** 不允许改换渲染引擎（例如 FFmpeg drawtext/drawbox）规避本规则；也不能把此类画面称为 GIF 或真实生成画面。
- 主体视觉素材应是用户提供或合法取得的实拍视频、真实录屏、摄影素材，或**真实图像/视频模型生成**并保存原始产物和来源记录的素材。禁止编造模型调用或生成结果。
- Python/FFmpeg 可用于转码、裁切、混音、剪辑、字幕和质量检测；允许在真实镜头上叠加必要且克制的字幕，但禁止用字幕/转场/动效去替代缺失的主体画面。
- 缺少真实视觉素材时，流程必须停止并列出缺口，不能自动退化为矢量/程序动画填时长。历史 SVG、Pillow 或数据动效相关脚本仅作 legacy 技术兼容，不是新作品推荐路径。
- 工程测试所用色块视频必须明确标记 **synthetic test fixture / 不得作为样片**。先有高质量镜头再谈剪辑，禁止用技术上可播放的 MP4 冒充成品。

## 制作优先顺序

1. **内容与声音**：定稿完整口播；有条件则整段 TTS/录音并做真实语句级声学对齐。若音质、对齐无法完成，不得宣称正式音画同步。参考 [声音流程](references/audio-first-production.md)、[Provider 契约](references/voice-provider-contract.md)。
2. **视觉导演**：先理解用户希望观众记住什么、怎样通过画面表现因果或人物动作，再选 A/B-roll 和素材实现方式。先输出独立 **Visual Director v2** 语义方案（见下文），审核后才开始大量制作素材。不要把整篇稿均分为 3 秒镜头。
3. **素材制作/选片**：优先实际有用的角色表演、真实演示、因果动画、机制拆解、对比实验或清晰的准确图解。人物需要动作与道具交互；B-roll 要增加新的知识信息。可控数据必须来自可靠来源或明确标“示意”。参阅 [A-roll](references/acting-and-viewpoints.md)、[B-roll](references/motion-graphics.md)、[媒体剪辑](references/mixed-media-video.md)。
4. **镜头剪辑**：从真实配音时间轴和具体动作/语义变化决定切点，允许一个口播段落对应多个镜头、或一个镜头跨多个语句。剪辑器视频输出标为未审预览，不能通过重复 GIF、定格帧、无意义条形图补足时长。
5. **实际观看/试听 + 评审**：使用 video_critic 获取基于解码实际视频的风险证据；由实际看过和听过全片的审阅者记录独立内容/视觉/节奏/声音/一致性打分。综合 ≥80/100，单项 ≥6/10，知识错误、误报来源和严重音画错位必须为 False，否则进入返工。机器检测**不能**自动赋予主观评分。
6. **局部返工与发布**：把每条问题（镜头 ID、客观观察、改动、复验方法）转成版本锁定的局部返工任务；未受影响素材继续复用，源音轨改变必须重验时间码与字幕；正式发布仍走 mixed_release + final_review 门禁。

## v3.1 新增：导演方案与质量闭环

**A. 构建真实音频和视觉时间轴**（已有 final script、audio、timed segments）：

```bash
python scripts/project_flow.py init --project project
python scripts/audio_timeline.py --script project/script.json --audio project/audio/voiceover.wav --timeline project/audio-timeline.json
python scripts/visual_plan.py --script project/script.json --audio project/audio/voiceover.wav --timeline project/audio-timeline.json --plan project/visual-plan.json
```

音频制作可以选择实际可用的整段 TTS、录音或已存在音频。没有音频时先解决音频，不得生成“按字数平均分配”的伪对齐时间码。

**B. 编写真正的语义镜头方案**：`project/shot-briefs.json` 必须包含每个真实视觉段落的具体初态、事件、结果、观众额外获得的信息、视觉策略和合理素材来源；A-roll 还需角色意图、动作、情绪及道具交互。两种风格候选只有在 briefs **显式给出真实不同的备选设计**时才可比较；不能凭空用固定公式给出不同方案。

```bash
python scripts/visual_director.py --visual project/visual-plan.json --timeline project/audio-timeline.json --briefs project/shot-briefs.json --variant dramatic --out project/director-v2.json
python scripts/visual_director.py --visual project/visual-plan.json --timeline project/audio-timeline.json --check project/director-v2.json
```

`director-v2.json` 是**未审核导演草案**，同时引用真实音频时间轴与旧视觉计划的 hash；变更后必须重新验证。规范参见 [v3.1 导演与观感评审](references/quality-director-v31.md)。

**C. 素材和编辑**：优先使用真实可用来源并记录 SHA。视频混合剪辑：

```bash
python scripts/video_cut.py --project project --compile --allow-mixed-media
python scripts/audio_subtitles.py --project project
python scripts/video_cut.py --project project --preview --allow-mixed-media --subtitles project/subtitles/captions.srt
```

没有正式字幕时，可以先制作明确标记的无字幕编辑预览，但**不能**说已完成发布字幕。GPT GIF 只是可选素材；若生成工具不可用，不要尝试虚构 API。需要视觉资产调度时详见 [素材生产](references/visual-asset-production.md)。

**D. 风险检测与实际审片**：

```bash
python scripts/video_critic.py --video project/build/mixed-preview.mp4 --plan project/video-plan.json --report project/quality/critic.json
# 实际观看/试听全片，填入 reviewer、具体 observations、五维 scores 和三个 blocking_findings 后
python scripts/video_critic.py --video project/build/mixed-preview.mp4 --plan project/video-plan.json --report project/quality/critic.json --review-input project/quality/review-input.json --review-out project/quality/human-review.json
```

技术风险报告会提示相邻图像近似、长时间运动变化很小、四镜头近似等长、音频轨缺失等**需要看片判断的风险**，不自动判断艺术质量。缺少真实观感观察不能生成虚假的人工通过记录。

**新版执行入口**：如果由当前 Codex Agent 负责实际视觉导演，应先运行 `director_brief_agent.py` 输出基于真实文案和声学时间码的创意任务，Codex 亲自写好 `shot-briefs.json`，再运行 `visual_director.py` 与 `character_performance.py` / `broll_strategy.py` 检查；音画素材齐备后可使用 `production_run.py --until mixed_preview` 创建实际 MP4。语义切点用 `editorial_engine.py` 与 `semantic_recut.py`，不能均分时长。完整命令见 [v3.1 端到端操作](references/v31-execution.md)。

**E. 局部返工**：

```bash
python scripts/revision_planner.py --video project/build/mixed-preview.mp4 --plan project/video-plan.json --critic project/quality/critic.json --findings project/quality/defects.json --revision-id rev-001 --out project/revisions/rev-001.json
```

通过 `revision_execute.py` 读取已验证的 revision 与真实替换素材，创建全新的工程修订版；自动复用未修改片段的 FFmpeg 缓存，但不继承人工审批。音轨需要重录时明确阻断，不能伪造声音。使用 `review_compare.py` 在浏览器双视频对照、点击定位镜头并下载人工缺陷清单。项目状态可用 `scripts/project_flow.py status --project project` 查看，v3.1 导演文件存在时自动检查质量证据。详细规范与格式见 [v3.1 质量流程](references/quality-director-v31.md)。

## 正式交付的硬门禁

- 全片配音自然、字幕对齐、知识准确、主体清楚、镜头真实有变化；形似 PPT 的无意义动效必须返工。
- 使用 `mixed_release.py --approve-shot` 按实际画面逐镜审阅，再 `mixed_release.py --release` 输出独立正式 MP4；最终 `final_review.py --inspect` 后真实观看/听完，才可 `--approve`。[发布规范](references/mixed-formal-release.md)
- 启用了 `director-v2.json` 的 v3.1 项目需要 **同一实际视频文件**的 `quality/critic.json` 和 `quality/human-review.json`；最终门禁会校验来源、分数与阻断项的一致性。人写的审核结果仍是*声明*，不是机器证实观众喜欢。
- **若用户要一条合格视频，必须交付实际可播放 MP4 并观看复评**。不足之处如实说明，不能以示例测试代替。
- v1/v2/v3 旧版操作细节移到 [旧流程参考](references/legacy-production.md)；遇到冲突，以 v3.1 的质量和声学优先原则为准。
