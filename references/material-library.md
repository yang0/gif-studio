# gif-studio：素材先准备，剪辑后选择

核心：生成 GIF ≠ 决定最终使用该 GIF。一条知识段落可以拥有多个不同景别、动作与节奏的 GPT GIF 素材候选。

## 工作分工

素材导演：依据知识主线做 coverage plan，分别设计主镜、特写、关键动作、衔接镜头。不是对同一提示词机械重复三次。

GPT GIF 制片：每条真实生成的素材进入 library/candidates/shot-id/，配套保存完整提示词快照、生成工具身份、实际产物引用和哈希。初始状态为 unreviewed；只记录素材，不宣称质量通过。

剪辑导演：先观看所有候选，再根据语义准确度、动作时长、主体大小、构图变化、上下镜头衔接，决定选中哪一条。只有被选中的素材复制到 gifs/shot-id.gif，随后再走原本的来源登记、技术 QA、视觉 QA 和时间线审核。

## 素材数量

15–20 秒测试片可先准备约 5–8 条有不同叙事功能的素材，而不是三个分镜固定生成三个 GIF。优先让素材种类丰富，有不同的景别、切入角度、时间长度；不要用重复的通用图标凑数。这是制作建议，不是硬性生成额度。

## 使用方法

生成真实 GIF 后登记 A 候选：

    python3 scripts/candidate_pool.py --project project add --shot shot-01 --candidate take-a --gif /actual/a.gif --prompt /actual/a.txt --tool ACTUAL_GIF_TOOL --reference ACTUAL_RUN --notes "近景，动作清晰"

同一镜头继续登记 B 候选：

    python3 scripts/candidate_pool.py --project project add --shot shot-01 --candidate take-b --gif /actual/b.gif --prompt /actual/b.txt --tool ACTUAL_GIF_TOOL --reference ACTUAL_RUN_B --notes "全景，有自然的衔接"

审阅两条 GIF 后选择 B：

    python3 scripts/candidate_pool.py --project project select --shot shot-01 --candidate take-b --reason "主体更大，动作节奏更适合旁白"

选中素材进入 gifs/shot-01.gif，原始 A/B 两份永久保留。旧 QA 被失效；后续按 SKILL.md 登记真实工具与**选中的 B 提示词**，不能用 A 提示词冒充 B。

如要换素材，显式传 --overwrite 并重新做全部审核。脚本不会运行 GPT GIF 模型，也不会用 Python 绘图替代任何画面。

## 后续增强

可做联系表和候选画廊、景别标签、候选比较、多个备选剪辑版本。重要的是先将素材库与编辑分离，避免一条 GIF 一旦生成就被迫进入正式视频。


## 可视化挑选与剪辑预览

`review_workspace.py` 从素材库建立本地 `library/review.html`，展示可播放的 GIF、技术元数据、原始 prompt 和入选状态。只读设计意味着点击网页不能偷改选择，也不能自动批准素材。

`render_edit_preview.py` 只用已选入 `gifs/<id>.gif` 的真实文件，通过 ffmpeg 输出 `build/editorial-preview.mp4`。它不需要事先完成视觉 QA，因为**草稿本身就是导演进行视觉审核的输入**；其交付报告明确标注 UNREVIEWED_EDITORIAL_PREVIEW，不能当正式视频。实际素材缺失、哈希或选片对不上时会拒绝预览。长定格和音画时长问题在草稿报告中提示，即使勉强渲染成功也不等于通过门禁。

当 `edit-plan.json` 存在时，重新生成画廊，会显示可点击的时间线。点击镜头块可以让视频跳到相应秒数。正式合成仍调用 `compose_video.py`，必须走素材来源、单镜 QA、剪辑表及最终整片 QA 的全部门禁。
