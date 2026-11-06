# 通知打断专注：GPT GIF-only 金标准试验

这是可复现的**制作输入**，不是已经通过的 GPT GIF 成片，也不包含任何假冒的程序化 GIF。

先复制本文件夹到一个项目工作目录，再执行：

```bash
python3 scripts/audit_script.py --script project/script.json --voiceover project/voiceover.md --storyboard project/storyboard.json
python3 scripts/director_plan.py --director project/director-plan.json --storyboard project/storyboard.json
python3 scripts/build_gif_prompts.py --project project --storyboard project/storyboard.json
```

检查三条不同的 prompt，在 Codex 当前真正可用的 GIF 工具中分别生成三条 GIF，后续按 docs/production-pipeline.md 做登记、抽帧、完整 GIF 视觉审查、合成。没有真实 GIF 绝不以 Python 绘画冒充测试成功。

时长只是初始示例预算，旁白最终时长应以真实音频为准；这套分镜是制作输入而非已批准成片。
