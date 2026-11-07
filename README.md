# gif-studio 🎬

**Codex-first knowledge video director and editor.** 从真实口播出发，完成 A/B-roll 叙事导演、真实素材剪辑、知识动效、字幕、完整审片和局部返工。**视频是产品，GIF 只是可选素材之一。**

仓库：[yang0/gif-studio](https://github.com/yang0/gif-studio) · [当前 v3.1 优化 Issue #2](https://github.com/yang0/gif-studio/issues/2) · [完整 Skill](SKILL.md)

## 制作流程

1. **声音先行**：定稿文案、真人录音或经过试听的整段 TTS，以及实际声学对齐；不能按字数虚构时间码
2. **视觉导演**：Codex 从真实语句与节奏设计角色行为、知识增量和因果视觉事件；提供两种**实质不同**的视觉方案
3. **素材制作**：使用已有录屏、实际视频、真实生成 GIF、截图、可控知识动效；不能用一套信息卡替代真实镜头
4. **实际剪辑**：依据实际音频切点编排素材、审核字幕、输出真实 MP4 预览；支持按内容哈希复用未修改镜头缓存
5. **审片与返工**：从真正 MP4 解码提取技术风险，实际观看/试听并记录五维评审；只重新制作不合格镜头并失效旧审批
6. **正式交付**：混合媒体逐镜来源审核 + 独立正式成片 + 全片观感批准，技术 CI 不能自称代表真实视频质量

## 新版 v3.1：从导演到剪辑

详细的 [端到端操作手册](references/v31-execution.md) 包含 Windows / macOS / Linux 命令与文件结构。

```bash
# 真实音轨、visual-plan.json 就绪后，为当前 Codex 生成导演创作任务
python scripts/director_brief_agent.py --script project/script.json \
  --timeline project/audio-timeline.json --visual project/visual-plan.json \
  --out project/director-assignment.md

# 当前 Codex 按任务真正写好 project/shot-briefs.json 后验证两种方案
python scripts/director_brief_agent.py --script project/script.json \
  --timeline project/audio-timeline.json --visual project/visual-plan.json \
  --briefs project/shot-briefs.json

python scripts/visual_director.py --visual project/visual-plan.json \
  --timeline project/audio-timeline.json --briefs project/shot-briefs.json \
  --variant dramatic --out project/director-v2.json

# 按已有已审核真实音轨 + 源素材制作未审视频
python scripts/production_run.py --project project --until mixed_preview

# 从实际 MP4 获取证据，不代表自动审批
python scripts/video_critic.py --video project/build/mixed-preview.mp4 \
  --plan project/video-plan.json --report project/quality/critic.json
```

进一步的实际镜头审核、修改与发布：[v3.1 操作说明](references/v31-execution.md) · [质量检查契约](references/quality-director-v31.md)。

### 支持的媒体

| 媒体 | 用途 | 真实来源要求 |
| --- | --- | --- |
| `gpt_gif` | 有实际动作的动画片段 | 必须登记真实生成文件及工具来源、独立审片 |
| `real_video` | 已拍摄人物、实验或纪录视频 | 已存在合法取得的真实视频文件 |
| `screen_recording` | 软件操作 / 实际界面讲解 | 真实录屏，不虚构用户界面 |
| `screenshot` | 文献、证据和 UI 特写 | 明确是静态镜头，不冒充动画 |
| `original_animation` | 已有原创动画视频 | 实际视频源、来源 SHA 校验 |
| `data_motion` | 流程 / 对比 / 时间线 / 数字 | 原创知识动效的来源报告；示意数字应标明 |

视频支持混合使用不同媒体，**不依赖 DSH、号池、某个特定生图 API，也不需要 Docker**。所有媒体仍需验证相关使用权和准确性。

## 质量标准

视频评审分成技术风险分析和真正的人工/视觉理解审片。建议独立评分：内容 25%、视觉 25%、剪辑节奏 20%、声音 15%、连续性 15%；加权 ≥80/100，单项 ≥6/10 且无实质知识错误、来源伪造或严重音画错位，才能进入独立正式发布审查。

旧 24 秒《手机通知为什么打断专注？》样片仍是**失败对照案例**，并非合格成片。真实高质量 Golden Sample 的验收需要自然中文配音、正确声学对齐、角色/风格一致性和完整实际审片。未能获得这些证据前，Issue #2 不能关闭。

## 开发与兼容

- Python 3.10–3.12、FFmpeg；可选 Pillow；TTS 和声学模型按实际需要安装
- `scripts/project_flow.py` 用于阶段状态和旧/新项目读取；`scripts/production_run.py` 增加 `director` 与 `mixed_preview` 真实执行阶段
- 新编译的 `video-plan.json` 与 `director-v2.json` 的哈希绑定，后者更新时旧 EDL 失效
- [已归档的 v3 及更旧 README](references/legacy-readme.md) 和 [旧 Skill Gate 操作](references/legacy-production.md) 仅供历史排错，不再是默认制作流程

本仓库以实际视频效果为目标；不提供无法证实的发布质量承诺。
