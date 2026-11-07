# Video Director v3.1 · 视觉语义与质量评审契约

## 目标
旧样片的问题是：八镜头等长、小人物卡片、无意义的数字动画、机械声学；现有 CI 只能验收文件不是视频质量。本方案提升导演决策和实际视频评审，不增加和号池相关的服务。

## 真正的导演输入（项目中准备）
\`audio-timeline.json\` 为真实配音时间轴，\`visual-plan.json\` 为可剪辑 A/B-roll 计划，\`shot-briefs.json\` 为逐镜的真实视觉创意简报。后一份必须由导演结合具体文案写出来，而不是让代码用随机模板臆造：
- initial_state：开头真实可见状态
- trigger_event：屏幕上发生的可观察动作/事件
- final_state：结束时的实质变化
- new_information：与旁白相较，画面真正增加的理解
- viewer_takeaway：观众看到后应当记住什么
- narrative_function、visual_strategy、movement_type：故事职责、视觉策略及有意义的动态
- source_policy / preferred_media：用已有、录屏还是原创动画以及实际来源类别
- A-roll 的 performance：character_id、intention、action、emotion_change、prop_interaction
- 对比或真实数据需要写 comparison_basis / data_provenance；没来源就必须标明示意，不可自造统计

\`visual_director.py\` 只生成两个*基于作者显式备选*的未审核方案；若缺少备选，不会凭代码虚构两套创意。重复镜头签名和无实际状态变化会拦截。连续相同策略当前仅报警，不能机械地要求交替 A/B。

## 视频 Critic 只做实测风险
\`video_critic.py\` 必须基于完整真实 MP4 抽帧，检查关键时点的画面相似度、镜头停滞、近似等时长、视频/音频轨等；只有潜在风险，不自动宣称主体太小或内容不正确。低变化镜头可能是正确的停顿，需人工确认。
真实审阅者看完并听完全片后，以具体场景观察提交五维得分：content=25%，visual=25%，pacing=20%，audio=15%，continuity=15%。发布建议门槛 ≥80/100 且单项 ≥6/10；知识错误、伪造来源、严重音画错位任一为 True 均不能通过。
\`human-review.json\` 只是具名审核者的声明（非远程防伪签名），不能用 CI 的模拟分数当真实电影审片；该审核不能直接替代正式 mixed_release + final_review。

## Revision Planner
\`defects.json\` 是实际发现的缺陷，一条必须有：id、issue_type、severity、shot_id（或全局 null）、evidence、proposed_fix、verification。来源必须绑定当次 critic SHA 和视频剪辑计划 SHA。
\`revision_planner.py\` 输出只重做的问题镜头源、可复用的其他候选及下游应当失效的产物。即使只替换一个镜头，混合预览、审片、正式交付必须重新生成；如果修改声音，时间码/字幕/全部镜头切点也必须重新验证。

## Golden Sample 对照
旧 24s 样片只证明 8 条镜头能够导出，未达到发布标准。不得在新的质量记录中对旧样片虚构通过。
同题重拍应有一条真实自然配音、分句声学对齐、字幕、角色演绎与有因果变化的知识 B-roll；全片真实看/听后证明优于旧片，再关闭 Issue #2 的 Golden Sample。
