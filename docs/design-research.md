# gif-studio v2 · 从 GIF 生成走向真正的视频制作

研究日期：2026-11-06。Star 为当日 GitHub 查询快照，并非质量保证。

| 项目 | 约 Star | 借鉴的设计 |
|---|---:|---|
| [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) | 140k | 从脚本、语音、素材到字幕和导出的完整制作流程；不强制一次生成结果就作为最终素材 |
| [Remotion Skills](https://github.com/remotion-dev/skills) | 6.4k | 素材、时间线、预览、字幕、渲染分成独立能力；先预览并允许修改 |
| [create-storyboard-skill](https://github.com/TateZhouSiu/create-storyboard-skill) | 6 | 连续性与角色/道具/场景 bible；不是高 Star 项目 |

## 从之前失败样片得到的结论

曾经的问题不是 GIF 是否可以解码，而是以“一句口播对应一条 GIF”的机械方式剪辑。为了凑时长大幅定格，甚至用无声字幕和固定版式冒充可发布的知识视频。

## 当前架构（独立阶段）

1. Narrative: 完整口播与语义连贯性审稿。
2. Coverage: 为每个知识点设计多种可用镜头，例如建立场景、动作特写、结果与衔接镜。
3. Library: 生成不同真实 GPT GIF 候选，保存不可变原始文件、实际提示词、来源引用和 QA。
4. Selection: 由剪辑导演**先观看再挑选**，只将需要的候选复制到当前正式镜头槽位；未选素材保留。
5. Edit Decision List: 真实配音、帧级剪切、镜头选择原因、动作覆盖长度与长时间定格检查。
6. Review: 真正观看整体 MP4，检查画面语义、节奏、接续、音频与字幕，独立审批发布。

不将 MoneyPrinterTurbo 的其他模型当作 GPT GIF 的隐性替代；不强制引入 Remotion；不把抽象视觉风格绑定到 Vox 拼贴。

## 尚待实现/验证

- 对照式候选浏览画廊和一键视频剪辑预览。
- 完整语音生成/真实句子时间戳。
- 从素材库的同一个知识段落中支持多镜头可变数量的全动态 EDL（当前先通过选择入槽位实现）。
- GPT GIF 实际输出对导演约束的真实端到端验证。

现有自动测试只验证文件、状态、时长和门禁，不替代观众对成片质量的判断。
