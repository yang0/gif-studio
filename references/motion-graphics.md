# 知识类 B-roll 动效模板

本模块为知识视频生成可控的信息动效 MP4，不是 GPT GIF 生图工具，更不能冒充人物动画。

四类模板：process（2–5 步）、comparison（2–5 组真实/标明示意的数据）、timeline（2–5 个事件节点）、metric（数值变化）。
模板在 templates/motion-process.json、motion-comparison.json、motion-timeline.json、motion-metric.json。复制模板、填入准确数据，再执行：

    python scripts/motion_graphics.py --spec project/motion/steps.json --out project/media/steps.mp4 --fps 24 --width 720 --height 1280 --duration 3

输出来源报告 steps.mp4.motion.json，包含动画规格、媒体 SHA256、帧数和明确的程序图形来源标记。
在视觉编排中填写 roll=B、media_type=data_motion、source_file=media/steps.mp4，以及真实 source_sha256；video_cut.py 校验动画报告和原始 MP4 是否一致。
准确性优先：没有研究来源时不把示意条形图和数字冒充真实统计；字幕、字号、安全区及信息层次需要实际审片。
