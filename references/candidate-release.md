# gif-studio v2.3：候选 GIF 独立审核与多镜头正式交付

核心原则：每条真正进入时间线的 GPT GIF 都有自己的技术/视觉审核记录。备用特写不可以借用主镜头的批准记录。

## 工作流

1. 使用 candidate_pool.py add 将实际生成的 GIF 和原始完整提示词、工具引用、prompt_delivery 登记到素材池。
2. 使用 review_workspace.py 观看所有候选，挑出不同景别和动作；未入选候选保留。
3. 使用 candidate_review.py --inspect 为所有实际进入剪辑时间线的候选生成严格格式检测和接触表。
4. 真正观看完整 GIF 后，使用 candidate_review.py --approve，记录具体的画面观察与语义、动作、风格、构图、连续性五项核查。
5. 通过 sequence_cut.py 编辑/预览自由时间线；实际看过预览后填写 sequence.json 的 approved 状态和详细审核备注。
6. 真实旁白和字幕就位后，使用 release_sequence.py 合成有音轨与烧录字幕的视频。
7. 成片仍然只能标记 PENDING_FINAL_VIDEO_REVIEW。必须真正看/听完整 MP4，再使用 final_review.py 进行最终批准。

## 命令

```bash
python3 scripts/candidate_review.py --project project --storyboard project/storyboard.json --shot shot-01 --candidate take-b --inspect
# 人工观看 GIF 与接触表后，显式批准并记录真实依据：
python3 scripts/candidate_review.py --project project --storyboard project/storyboard.json --shot shot-01 --candidate take-b --approve --reviewer REVIEWER --notes '实际观察到的镜头动作、衔接与语义关系' --prompt-delivery explicit_tool_argument --semantic-pass --motion-pass --style-pass --composition-pass --continuity-pass

python3 scripts/sequence_cut.py --project project --sequence project/sequence.json --verify
python3 scripts/sequence_cut.py --project project --sequence project/sequence.json --preview

# 导演真正审过预览并批准 sequence.json 后：
python3 scripts/release_sequence.py --project project --storyboard project/storyboard.json --sequence project/sequence.json --audio project/audio/voiceover.wav --subtitles project/subtitles/captions.srt --out project/final.mp4
python3 scripts/final_review.py --project project --video project/final.mp4 --inspect
# 完整观看/试听后再调用 final_review.py --approve 与五项审核标记
```

## 质量边界

- 候选审核的来源登记是执行者声明，不是外部模型调用的密码学认证。
- 技术检测不能证明 GIF 视觉语义正确；不能自动勾选人工检查。
- 有音轨不等于里面是自然配音，必须完整试听。测试所用静音音轨不是合格口播。
- 修改候选源文件、提示词、导演决策、风格锁或审核记录，相关批准会失效。
- 不能以 Python 矢量动画、SVG、PPT 示意图替代 GPT GIF。
