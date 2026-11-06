# gif-studio v1.4/v1.5 生产流程

1. 写完整的 script.json 与 voiceover.md；先确认连贯口播。
2. 根据口播写 storyboard.json、style-lock.json 和 director-plan.json。
3. 执行导演校验：

    python3 scripts/director_plan.py --director project/director-plan.json --storyboard project/storyboard.json

4. 保存每镜完整提示词 project/prompts/shot-01.txt，并用 Codex 当下**实际存在**的 GIF 工具生成 project/gifs/shot-01.gif。脚本本身不调用图片模型。
5. 登记每个实际文件（把占位符替换为真实的工具名和操作引用，不得编造）：

    python3 scripts/register_asset.py --project project --storyboard project/storyboard.json --shot shot-01 --kind gpt_gif --tool ACTUAL_TOOL --reference ACTUAL_RUN_REFERENCE --prompt project/prompts/shot-01.txt

6. 质检，生成真实的抽帧接触表：

    python3 scripts/inspect_gif.py --gif project/gifs/shot-01.gif --duration 5 --report project/qa/shot-01.json --contact-sheet project/qa/shot-01-sheet.jpg

7. 在确实观看关键帧并判断语义、动作、风格、构图正确后，显式确认四项视觉检查：

    python3 scripts/approve_shot.py --project project --storyboard project/storyboard.json --shot shot-01 --reviewer REVIEWER --notes "实际观察和审核依据" --semantic-pass --motion-pass --style-pass --composition-pass

8. 查询状态：

    python3 scripts/project_status.py --project project --storyboard project/storyboard.json

9. 正式合成：

    python3 scripts/compose_video.py --project project --storyboard project/storyboard.json --out project/final.mp4 --audio project/audio/voiceover.wav --burn-subtitles

修改 GIF、提示词、风格锁、导演决策或单镜分镜后，原注册与审核失效，需要重新生产审核。

## 复用与程序化画面

复用必须由导演提前写明 intentional_reuse、reuse_source_id 和 reuse_justification，并且复用素材字节需一致。程序化动画必须在导演阶段写明 programmatic 和 programmatic_reason，不能冒充 GPT GIF。

## 交付边界

生产来源登记由执行者填写，不是远端服务的不可伪造签名。视觉检查四项必须经过真实审阅，不应自动写通过。FFmpeg 能证明编解码正常，不能证明知识表达正确。没有音频的输出只叫无声预览/B-roll，不叫完成的有声口播作品。
