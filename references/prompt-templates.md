# 可复用提示词

## 1. 分镜导演

任务：将 {{SCRIPT}} 制作成 {{TARGET_DURATION}} 秒知识短视频。先判断论点是否成立，再按每镜头 3–6 秒拆分。每镜头只有一个知识目标。输出镜头 ID、原始口播、简短字幕、视觉类型、3–6 个物件、主背景色、动作顺序、时长。禁止生硬把所有概念都变成视觉隐喻；科学机制优先结构图，数据关系优先图解。未经确认不要出图。

## 2. 统一风格基准

Editorial halftone paper collage. A flat solid colored uncoated paper background, black-and-white photographic halftone cutouts with visible print dots, clean mechanical paper edges, thin warm-ivory keylines, soft paper shadows and subtle fibers, restrained accent color cardstock. No gradients, no glossy 3D, no busy photorealistic environment. Clear large objects and strongly readable visual hierarchy. Vertical 9:16 composition, center-weighted main subject, clear bottom subtitle-safe area.

## 3. 终帧静图

Create a FINAL KEYFRAME for an educational animated GIF.
Knowledge goal: {{VISUAL_GOAL}}
Mode: {{VISUAL_MODE}}
Main objects: {{KEY_OBJECTS}}
Composition: {{COMPOSITION}}
Background and accents: {{COLORS}}
Reference style: {{STYLE_SPEC}}
This frame must be visually complete, simple, and legible, with 3–6 separable main pieces whenever possible. Keep the camera locked and provide enough clean background for elements to later assemble from empty space.
Do not put narration text in the frame; the video editor adds subtitles separately.
Negative: gibberish, letters, numbers, watermark, logo, app UI, stray cutouts, tiny illegible objects, clutter, gradients, smooth 3D.

## 4. GIF 动画

Create an animated GIF, target {{DURATION_SEC}} seconds, vertical 9:16.
The END STATE should visually match the supplied final-keyframe reference WHEN the tool supports an image reference. If no reference is supported, follow this complete description: {{FINAL_FRAME_DESCRIPTION}}.
Concept: {{VISUAL_GOAL}}.
Start on a blank solid paper background. Assemble the object groups using physical stop-motion verbs: slide, drop, snap into place, hinge, rotate, unfold, align, lock. Use this exact ordered choreography: {{MOTION_PLAN}}.
Reserve the final portion for a clearly legible hold, then optionally cleanly return to blank for looping. All elements keep their identity and material texture across frames.
Camera fixed; no zoom, camera movement, fades, floating drift, text, logo, watermark, new objects, morphing, or jitter.

## 5. 针对不同知识类型的动作

- visual_metaphor: 基础物件 → 隐喻主角 → 行为 → 结果；物件形态不可变化。
- structure_relation: 模块逐个进入 → 连接线形成 → 重点流向被强调。
- mechanism_breakdown: 外部框架 → 层级拆开 → 输入输出 → 结构复位。
- compare_contrast: 状态 A 稳定 → 状态 B 展开 → 形成两侧清楚对照。
- data_motion: GPT 只负责抽象动势；准确比例、数值和标签由后期程序叠加，不让生成模型绘制精确数据。
