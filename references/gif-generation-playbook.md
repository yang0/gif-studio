# gif-studio | GPT GIF 镜头执行手册

本项目的主要镜头必须来自实际可验证的 GPT GIF。脚本只能编译提示词、质检素材、记录来源和合成；不能替代 GIF 生成。

## 为什么会反复出现电脑、大脑和灯泡？

过去只写“注意力”“知识”“AI”等抽象主题，模型倾向于用通用图标来表现，而没有发生真正的剧情。现在对每一镜头要求：
- must_show：至少两个具体对象或连续行为；
- must_not_show：该镜头坚决不能出现的通用符号；
- visual_proof：观众不看字幕也能观察到的因果关系；
- start_state / change_event / end_state：必须可分辨的开始、动作、结果；
- composition：主体大小和构图，避免长时间播放顶部标题+中央小图的模板。

## 生成流程

1. 完整口播与分镜确认后写 style-lock.json、director-plan.json。
2. 用 director_plan.py 检查每镜头是否有真正的可见事件。
3. 执行 build_gif_prompts.py --project project --storyboard project/storyboard.json，为每个 new_gpt_gif 镜头编译不同的 prompts/<shot>.txt。
4. 当前 Codex 必须真的具备 GIF 工具。将每镜头提示词分别发送给可用工具，记录真实输出，不擅自改用 SVG/矢量动画或第三方视频模型。
5. 执行 inspect_gif.py 生成 contact sheet。**除了看 contact sheet，还应观看完整 GIF**；确认语义、动作、风格、构图，以及必须/禁止元素。
6. 审核通过的素材登记来源，然后运行 approve_shot.py 写入基于哈希的正式视觉审核记录。
7. 不合格则先保存失败 GIF、具体观察和错误类型，再执行 review_gif_attempt.py。它会生成一次定向修复提示词（retry-2）。
8. 第二次仍不合格时停止生产，重新设计该镜头的导演方案，不无限抽卡、也不使用劣质矢量动画填坑。

## 失败的例子

目标：通知打断专注。
错误 GIF：只有电脑、书本、大脑和灯泡；没有通知弹出，也没有中断事件。
正确约束：
- must_show：人物正在工作，连续的手绘思路线；手机弹出通知；思路线可见地断开；
- must_not_show：独立大脑图标、灯泡、书堆、随机 AI 符号、固定 PPT 卡片布局；
- 视觉证据：观众无需字幕就能看出从连续工作到被打断的变化。

生成失败后示例：

    python3 scripts/review_gif_attempt.py --project project --storyboard project/storyboard.json --shot shot-01 --category generic_symbols --observation "画面只有电脑大脑灯泡，没有出现通知弹出或思路断裂" --reviewer "真实审核人"

先备份第一轮 GIF，使用新生成的 prompts/shot-01.retry-2.txt 再生成一次。第二次失败会锁住镜头；只有修改 director-plan.json 中具体的视觉决策，才可以开始下一轮，并保留之前的失败记录。

## 重要边界

- 提示词编译器能使约束更具体，但不能保证模型遵循约束。
- 技术 QA 不能自动证明语义正确；审核必须实际看到动画内容，不能编造视觉审核结论。
- 生成器的工具名称、版本、参考图与时间参数必须以当前实际工具能力为准。
- 输出 GIF 不合格，宁愿交付失败记录，也不要把替代动画冒充正式成片。
