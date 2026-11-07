# 混合媒体视频正式发布门禁

第一阶段：video_cut.py 编译真实配音、GIF/录屏/截图/信息动效为未审核预览。样片只能称为 UNREVIEWED_MIXED_PREVIEW。
第二阶段：导演真实观看每个镜头，逐条使用 mixed_release.py --approve-shot --shot v001 --reviewer 审核者 --notes 具体视觉观察 --semantic-pass --continuity-pass --readability-pass --source_legitimacy-pass 签核。
第三阶段：全部镜头有 SHA256 绑定的审核记录后，运行 mixed_release.py --project project --release，复制独立正式 MP4 到 build/formal-mixed/final.mp4，状态 PENDING_FINAL_VIDEO_REVIEW。
第四阶段：运行 final_review.py --project project --video project/build/formal-mixed/final.mp4 --inspect；实际看完整片、听完整段旁白且符合字幕/节奏/知识要求后再执行 --approve 与五项审核标记。

快捷操作：
    python scripts/video_cut.py --project project --compile --allow-mixed-media
    python scripts/audio_subtitles.py --project project
    python scripts/video_cut.py --project project --preview --allow-mixed-media --subtitles project/subtitles/captions.srt
    python scripts/mixed_release.py --project project --approve-shot --shot v001 --reviewer 审核者 --notes 实际观察说明二十四字以上 --semantic-pass --continuity-pass --readability-pass --source_legitimacy-pass
    python scripts/mixed_release.py --project project --release
    python scripts/mixed_release.py --project project --verify
    python scripts/final_review.py --project project --video project/build/formal-mixed/final.mp4 --inspect

正式 MP4、原始配音、字幕、视觉计划、剪辑计划、逐镜审核和源媒体均按哈希绑定；任何源文件变更导致旧正式发布验证失败。人工审核属于执行者声明，自动测试不能代替整片创意和音质审片。
