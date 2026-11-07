# v3.0 · 从 A/B-roll 视觉编排生产真实 GIF 候选

**先完整配音和真实声学对齐，才安排镜头和候选。** 不要用每句一张图、重复同一 GIF 或通用拼贴来凑时长。

## 1. 在 visual-plan.json 给镜头编制多种实际视觉方案

保持 `audio_segment_ids`、`start_ms`、`end_ms`、`roll`、`media_type` 等音频优先字段不变，给 `media_type=gpt_gif` 的镜头增加 `source_shot_id` 和 `production`：

```json
{
  "id": "v001", "start_ms": 0, "end_ms": 1800,
  "audio_segment_ids": ["s001"], "roll": "A",
  "role": "character_action", "media_type": "gpt_gif",
  "source_shot_id": "shot-01",
  "visual_event": "主持人被手机通知打断后抬头，表达疑惑",
  "cut_reason": "建立故事冲突",
  "production": {
    "reference_pack": "reference-pack.json",
    "candidates": [
      {
        "candidate_id": "wide",
        "framing": "中远景：人物坐在书桌旁，手机位于画面一角",
        "distinctive_motion": "手机通知亮起后，人物从键盘缓慢移开手并抬头看手机",
        "must_show": ["人物与书桌同框", "手机实际发光并引起人物反应"],
        "must_not_show": ["无关的大脑、灯泡符号", "字幕乱码"],
        "notes": "建立人物与环境关系"
      },
      {
        "candidate_id": "reaction",
        "framing": "角色半身特写，保持同一服装和面部特征",
        "distinctive_motion": "角色双手停在键盘上，听到通知后目光转向右下角",
        "must_show": ["角色表情清晰变化", "目光看向对应的手机方向"],
        "notes": "抓取情绪反应和动作切点"
      }
    ]
  }
}
```

`shot-01` 必须存在于 `storyboard.json.shots[]`。A-roll 人物镜头必须指定**真实**五种参考图文件：front / side / back / stroke_detail / scene，全部 SHA 校验通过。B-roll 的 GPT GIF 可以不需要人物参考；但当涉及一致角色时仍应附带。

## 2. 编译任务，不自行生成素材

```bash
python scripts/visual_assets.py --project project --prepare
python scripts/visual_assets.py --project project --status
```

输出每候选独立的 `prompts/v3/<shot>/<candidate>.txt` 和 `production/visual-asset-plan.json`。镜头原稿、实际声音、style-lock、参考图和候选规格都会参与校验。重新执行不覆盖已准备的不同提示词，输入修改后明确 blocked，需归档修改版本和更换候选 ID。

## 3. 有实际可用 GIF 工具时执行（可选）

```bash
# backend-command.json 是命令数组，例如 ["python", "/trusted/path/to/gif_backend.py"]
# 后端必须支持 gif_batch.py 的 --capabilities 和 --generate JSON 协议。
python scripts/visual_assets.py --project project --run \
  --backend-file project/backend-command.json --workers 2 --max-attempts 2
```

此命令复用 `gif_batch.py`，每个请求传递真实完整 prompt、参考图路径和 SHA；只有后端实际产生符合技术要求的 GIF 才登记到候选库。没有授权的后端或能力探测失败时必须停止，**不能回退到 SVG、PPT、重复 GIF 以及伪造来源数据。**

## 4. 素材入库不等于作品合格

`--status` 的 `produced_unreviewed` 只意味着候选 GIF 已在素材池且字节与提示词登记一致。必须使用 `review_workspace.py` 和 `candidate_review.py` 真实观看，校验语义、动作、角色一致性、画幅及画面质量，然后才能供 `visual_to_sequence.py` / `video_cut.py` 使用。

截图和录屏 B-roll **不是 GIF 生成任务**：它们由 `video_cut.py` 按真实媒体引用剪辑，不能被自动替换成动画。精确图表/文字动效仍需专门的可控媒体渲染器，不能被伪装为已实现。
