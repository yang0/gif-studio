# gif-studio Prompt 模板（风格无关）

## 1. 分镜导演

把 {{SCRIPT}} 变成 {{TARGET_DURATION}} 秒视频。分析受众与知识目标，按语义和实际配音时长设计镜头。为每镜头选择知识表达模式 visual_metaphor / structure_relation / mechanism_breakdown / compare_contrast / data_motion。**不要默认 Vox 或纸拼贴风格**。

## 2. 风格导演

User preference: {{USER_STYLE}}
Topic and audience: {{TOPIC_AUDIENCE}}
Available presets: presets/styles.json
Propose 2–3 visually distinct treatments with material, light, color, composition, motion grammar and risks. Respect user-supplied reference images. Once approved, emit project/style-lock.json. Never select a style merely because it was used in a previous project.

## 3. 关键静帧

Create a final keyframe for an educational video, style defined by the FULL style lock:
{{STYLE_LOCK}}
Knowledge goal: {{VISUAL_GOAL}}
Subject and composition: {{SUBJECT_COMPOSITION}}
Important objects and their identities: {{OBJECTS}}
The final state must express the point immediately. Keep a safe area for external subtitles. Do not invent text, statistics, UI or logos. If source imagery is given and supported, use it as visual reference; otherwise describe it explicitly.

## 4. GIF 动画

Generate an animated GIF, target {{DURATION_SEC}} seconds (only use supported output parameters).
Full style definition: {{STYLE_LOCK}}
Knowledge point: {{VISUAL_GOAL}}
Reference final frame (if tool can accept it): {{STILL_REFERENCE}}
Action choreography, including entry, behavior, landing, exit and final hold:
{{MOTION_PLAN}}
Motion grammar must reflect the selected style: hand-drawn uses drawing strokes, clay uses tactile physical animation, watercolor uses brush/pigment diffusion, cinematic uses motivated lens movement, pixel art uses discrete stepping, infographic uses diagram builds, collage uses paper layering.
Do not automatically apply assemble-from-empty. A static hold, transformation, reveal, diagram flow or loop is acceptable when semantically justified.
Preserve object identity, palette and design language. No unrelated text, invented numbers, logos, watermark or unexplained UI.

## 5. 回炉修正

Keep EXACT style-lock and subject identities; correct only {{QA_ISSUES}}. Avoid rebuilding all approved shots. Never claim an exact end-frame match if image referencing is unsupported.
