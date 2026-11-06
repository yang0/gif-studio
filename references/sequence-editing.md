# gif-studio：多镜头自由剪辑（sequence.json v2）

原有剪辑计划假设一段口播对应一条 GIF。本模块允许一段口播自由剪成多个真实 GPT GIF 镜头；原始素材保存在候选素材库里，不再受原分镜数量限制。

每个 clip 有独立的 clip id、shot_id、candidate_id、source_sha256、start_frame、in_frame、duration_frames、narration_anchor 和 cut_reason。start_frame 必须连续无重叠。in_frame 与 duration_frames 使用最终输出 fps 的帧单位，不能超过 GIF 原始动画总时长，不能靠末帧长定格填时长。

## 命令

先准备素材池并选入每个知识段落的基础候选：

    python3 scripts/sequence_cut.py --project project --storyboard project/storyboard.json --init

这个命令输出 project/sequence.json 草稿。按需要手动拆分、增加或删除 clips，修改其他候选和入点、出点，重新计算 start_frame 和 total_frames。

    python3 scripts/sequence_cut.py --project project --verify
    python3 scripts/sequence_cut.py --project project --preview

预览默认路径：project/build/sequence-preview.mp4，状态明确为 UNREVIEWED_SEQUENCE_PREVIEW。可以追加 --audio project/audio/voiceover.wav；如果音频比镜头时间线长短差距超过 0.35 秒，预览报告会提示，并且不静默截短旁白来冒充音画同步。

本阶段实现的是可变镜头预览，并非已经具备正式成片发布审核。正式版仍需每条候选各自的素材来源和视觉审核，以及最终整体成片审核。不能因为 ffmpeg 成功运行就自报视觉 QA 通过。

参考 MoneyPrinterTurbo 的素材生产与选片拆分、Remotion 的独立时间线及预览工作方式。GPT GIF 始终是主要视觉来源，不以 SVG、Python 矢量图替代。
