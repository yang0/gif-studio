# 整段语音与声学对齐 Provider 接口（v3.0）

`voice_pipeline.py` 是真实执行适配器，不是语音模型：它调用你明确配置的 CLI TTS/声学对齐工具，严格要求落地真实音轨，并验证音频时间码。没有配置时不会合成假的声音，也不会伪造时间戳。

## Provider argv 契约

在 `voice-providers.json` 里配置可信任的真实程序：

- `tts.argv` 是数组，不能用 shell 管道或任意 shell 语句。支持 `{text_file}`、`{audio_out}`、`{script_file}`、`{project}`。只调用**一次**，传入整段原稿；Provider 必须产生可由 ffprobe 识别的音频文件（建议 16-bit PCM WAV）。
- `alignment.argv` 接受 `{audio_file}`、`{text_file}`、`{timeline_out}`、`{script_file}`、`{project}`。Provider 必须输出 `audio-timeline.json` v1，真实段落的毫秒区间，`source.method=forced_alignment`，`source.tool_or_reviewer` 等于配置 name，并带音频 SHA256/真实时长/全文一致的分段文本。
- 环境变量携带密钥；密钥不可写到 argv、项目 JSON、输出报告。程序以列表调用 subprocess，不会通过 shell 执行。请只使用受信任的 provider。
- 失败后可以运行 `--reuse-audio`，不重复产生配音。禁止覆盖已有音频、伪造 provider 成功或自动批准语音质量。
- 已有真实录音可直接放到 `audio/voiceover.wav`，只配置 alignment 并使用 `--reuse-audio`。没有强制对齐引擎时，允许人工逐句听审后按 `manual_verified` 格式输入时间码，再运行 `audio_timeline.py` 验证。

## 接入示例

配置见 `templates/voice-providers.json`；它是接口模板，所写的示例 module 名称不是已安装的工具。需用你实际已配置的火山引擎/豆包、Azure、或本地真实 TTS/aligner 的 CLI 替代。

`python3 scripts/voice_pipeline.py --project project --providers project/voice-providers.json`

`python3 scripts/voice_pipeline.py --project project --providers project/voice-providers.json --reuse-audio`

TTS 与 alignment 的外部调用费用、凭据和使用许可取决于选定服务；该脚本不自行开通账号或调用未经授权的服务。

## 质量边界

FFprobe 能证明音轨存在与时长，不证明发音自然或音质好。必须完整试听真人/实际 TTS 输出并审核，不得将测试静音 WAV 当作合格旁白。强制对齐工具也可能给出错误时间码，需听审并核实关键句。任何 synthetic fixture 不能被作为真实作品来源报告。
