# gif-studio 视觉导演协议（v1.4）

目标：每一个镜头都要**用可观察的画面变化解释或证明一件事**，而不是在画面中摆放和口播有关的物件。

## 三段式视觉事件

每镜头写入 director-plan.json：spoken_point（口播要点）、source_anchor（逐字稿原文片段）、visual_proof（画面证明什么）、start_state（开头状态）、change_event（因果变化）、end_state（末尾状态）、composition（主体尺度和空间关系）、entry_transition / exit_transition（前后衔接）、asset_policy（素材方式）。

## 避免失败作品的四道检查

1. **语义互换测试**：把画面拿到其他镜头是否也说得通？若是，画面过于泛化。
2. **无动画测试**：去掉变化，只看最后一帧，知识表达是否完全不受影响？若是，动作可能没有必要。
3. **PPT 检查**：不能把每个镜头强制安排为顶部大标题、中间小动图、底部标签的固定版式。
4. **前后连续性测试**：上一镜给下一镜留下了具体问题、对象、形状或动作的衔接点吗？

导演计划必须由 scripts/director_plan.py 验证；警告属于人工评估，不等于自动通过审美质量。风格遵从用户的 style-lock.json，不强制使用 Vox 或半调拼贴。

## 素材来源

- new_gpt_gif：每镜有独立的实际 GPT GIF 生成记录和完整提示词。
- intentional_reuse：故意复用已生产的画面，必须写 reuse_source_id 与 reuse_justification；不可伪装为新镜头。
- programmatic：精确数据、公式或其他确定性动画，需事先声明 programmatic_reason；不允许在生成失败后暗中替代。

每条素材登记实际来源并通过技术质检、contact sheet 和视觉审核。录入的生成工具身份属于执行人声明，不能当成 API 的可验证签名。
