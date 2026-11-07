# gif-studio 🎬

**Codex 主导的知识视频导演与剪辑 Skill。** 从真实口播设计镜头，使用真实 AI 生成 GIF/视频、实拍或录屏素材，使用 FFmpeg 剪辑、字幕和混音，实际观看/试听并逐镜返工。**GIF 是可选素材；最终产品是好看的视频，不是通过测试的程序。**

[制作 Skill](SKILL.md) · [真实素材契约](references/real-source-contract.md) · [架构纠偏 Issue #3](https://github.com/yang0/gif-studio/issues/3) · [真实样片 Issue #2](https://github.com/yang0/gif-studio/issues/2)

## 最短制作流程

1. 定稿脚本 → 自然中文配音/真实声学时间码；
2. Codex 写导演分镜：初态、动作、结果、镜头切点、视觉信息增量；
3. **先真实制作/导入一个合格素材，再扩展其他镜头**：实际生成的 GIF/视频、拍摄、录屏或明确静态的真实证据图；
4. 逐镜素材来源与 SHA256 检查，缺什么就停止并列出缺口，**不退化成程序绘图**；
5. FFmpeg 按真实语义/动作时间码剪辑 MP4，字幕/声音同步；
6. 全片实际看/听后独立评分、局部返工，合格才进入正式发布。

```bash
python scripts/project_flow.py init --project project

# Codex 编写 script/audio-timeline/visual-plan/director-v2/storyboard，
# 实际生成或导入素材并登记 source_provenance，再执行预检：
python scripts/real_source_gate.py --project project

# 一旦素材、声音、分镜满足约束，运行真实剪辑（默认目标 mixed_preview）
python scripts/production_run.py --project project --until mixed_preview

# 对真正的成片做技术风险扫描；必须另行真实观看和试听
python scripts/video_critic.py --video project/build/mixed-preview.mp4 \
  --plan project/video-plan.json --report project/quality/critic.json
```

## 重要限制

- **禁止**用 SVG、Pillow、Canvas、程序动画、PPT 卡片、数据图表替代主体视频素材；不允许用 FFmpeg 绕道绘图。必要字幕可以叠加在真实镜头上。
- **真实素材缺失则阻断**；新预检会报告每个镜头缺少的原始文件、正确哈希或来源声明。支持生成模型真实输出、摄像拍摄、真实录屏及来源清晰的静态证据图片；不依赖特定号池、平台或付费 API。
- 元数据与 SHA256 只验证声明和文件一致，**无法自动证明画面真是由某个模型制作或质量合格**；独立真实审片始终必要。
- Python 3.10–3.12、FFmpeg；部分审片/图像检测需 Pillow。旧版本工作流仅保留为 legacy 技术参考。

## 当前状态

- 真实素材门禁与默认预览/发布命令集成；工程测试素材与合格作品严格区分。
- 前一版《手机通知为什么会打断专注？》Pillow/程序卡片 + espeak 预览**已作废**，不作为 Golden Sample。
- 20–30 秒正式 Golden Sample 仍未完成，需真实生成素材、自然配音、实际观看/试听和独立评分 ≥80/100；因此 [Issue #2](https://github.com/yang0/gif-studio/issues/2) 保持开放。
- CI 仅验证代码行为，不能证明艺术质量。
