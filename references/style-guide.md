# gif-studio 多风格导演规范

本项目不指定默认审美风格；Vox/半调纸拼贴只是可选预设之一。**自动风格选择是推荐，不是审美强制**。

## 风格决策

- 用户给风格或参考图：优先尊重。
- 未给风格：根据受众、主题、情绪、视频长度推荐 2–3 种风格，并写明各自取舍。用户确认后锁定。
- 不要把视觉类型（隐喻/流程/对比）等同于视觉风格（手绘/3D/极简等）。这两个维度独立。
- 一条视频可混用风格，但应有清楚的段落理由与共享连接元素（配色、字体、角色或转场）；默认先保证统一。
- 精确的文字、公式、数据图和字幕须后期编程绘制；GIF 模型生成的是创意运动层。

## style-lock.json

字段：style_id、reference_paths（真实文件才填写）、palette、materials、lighting、camera、motion_grammar、negative_constraints、characters、typography、subtitle_safe_area、shot_overrides。

合成提示词必须引用完整 style-lock 对象。每次重生保持 style-lock 与实体词典一致，不要对单镜头偷偷变换风格。

## 画面语言

- clean-infographic：精确的空间层级、少量抽象形状、节点流向。
- hand-drawn：逐笔绘制、擦除与重画。
- clay-3d：可塑物体与稳定的光影关系。
- watercolor：染色、晕染、渐次显现。
- pixel-art：离散步进、清晰像素网格。
- cinematic：通过镜头和灯光叙事，但避免身份漂移。
- editorial-collage：纸片裁切与排版；不是默认模式。

## 质量原则

镜头的变化应增加信息，而非炫技。色彩适用于语义但不机械映射。字幕安全区通常保留下 15–20%，并根据平台 UI 测试调整。镜头间避免完全重复的主动效，保持节奏对比。
