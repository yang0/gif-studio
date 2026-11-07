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

配置见 `templates/voice-providers.json`，目前默认指向仓库内真实可执行的可选实现：`voice_production.py`（edge-tts 整段生成）和 `forced_align.py`（stable-ts/Whisper 强制对齐）。这两个外部库和模型并非默认已安装，也未在 GitHub CI 中执行在线生成。请先按服务条款和环境安装 `pip install -r requirements-voice.txt`；对齐还需要独立安装兼容的 `stable-ts`/Whisper 依赖及模型。没有网络、模型或许可时不得声称在线已执行。若要使用火山引擎/豆包、Azure 或本地其它引擎，可替换配置中的完整 argv。

配置支持 `{python}`（本次 Python 可执行文件）、`{skill_dir}`（仓库 scripts 目录）和输入输出参数占位。使用 `{python}` 而不是硬编码 `python`，避免 Windows 多 Python 环境出错。

`python3 scripts/voice_pipeline.py --project project --providers project/voice-providers.json`

`python3 scripts/voice_pipeline.py --project project --providers project/voice-providers.json --reuse-audio`

TTS 与 alignment 的外部调用费用、凭据和使用许可取决于选定服务；该脚本不自行开通账号或调用未经授权的服务。

## 质量边界

FFprobe 能证明音轨存在与时长，不证明发音自然或音质好。必须完整试听真人/实际 TTS 输出并审核，不得将测试静音 WAV 当作合格旁白。强制对齐工具也可能给出错误时间码，需听审并核实关键句。任何 synthetic fixture 不能被作为真实作品来源报告。

## 推荐的实际调用入口

```bash
python scripts/project_flow.py init --project project
# 从 templates/voice-providers.json 复制到 project/voice-providers.json，安装允许使用的语音服务
python scripts/voice_pipeline.py --project project --providers project/voice-providers.json
# 如果生成声音成功但声学模型失败：继续重用完整音轨，绝不重新分句生成
python scripts/voice_pipeline.py --project project --providers project/voice-providers.json --reuse-audio
# 确认两个实际文件均存在后继续查看下一步
python scripts/project_flow.py status --project project
```

另提供 `production_run.py` 阶段性恢复入口：`--until voice|alignment|sequence`，在线生成必须明确加 `--allow-network-tts`，加载/下载声学模型必须加 `--allow-alignment-model`；未授权时会明确阻断，不会静默访问网络。它与 `voice_pipeline.py` 当前是两种工作方式（可配置 Provider 与内建可选 Provider），不要在同一项目中同时执行两条路径并覆盖音轨。两者产生的声音/时间码依旧要由用户实际试听、审片。
