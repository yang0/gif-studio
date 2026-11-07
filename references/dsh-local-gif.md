# DSH 本地号池 GIF 后端（可选）

基于 [yang0/chatgpt2api-dsh](https://github.com/yang0/chatgpt2api-dsh) 的本机 `POST /v1/images/generations` 原生 GIF 接口。继续使用自己的本地账号池，不购买额外的 OpenAI API 或视频模型额度。上游是否开放 GIF 能力取决于账号，不保证每次成功。

## 使用条件

启动最新 chatgpt2api-dsh 托管后端，并在“API 接入”中生成用户 API Key；不要把账号密码、2FA、access_token 或 API Key 提交到 GitHub。

目前此号池的 GIF 模式**不支持参考图**。有角色正侧背三视图或场景参考强约束的 A-roll 镜头会被批量调度器拒绝，不能偷偷省略参考图。适合先试没有角色 IP 强一致性要求的真实机制动画/B-roll。

## Windows PowerShell

将 `templates/gif-batch-dsh.json` 复制到 `project/gif-batch.json`，并创建其中所列的两条完整、内容不同的 prompt 文件。运行命令：

```powershell
$env:GIF_STUDIO_DSH_API_KEY = '本机DSH插件生成的用户API Key'
$env:GIF_STUDIO_DSH_BASE_URL = 'http://127.0.0.1:38650/v1'
$env:GIF_STUDIO_DSH_MODEL = 'gpt-image-2.6'
$env:GIF_STUDIO_GIF_FRAMES = '9'
$env:GIF_STUDIO_GIF_FRAME_MS = '200'
python scripts/gif_batch.py --project project --tasks project/gif-batch.json --backend-file backend-command.json --workers 2 --max-attempts 2 --timeout 300
```

仓库根目录 `backend-command.json` 内容：

```json
["python", "scripts/backends/dsh_pool_gif.py"]
```

## 结果检查

原始 GPT GIF 保存在 `project/library/candidates/<shot>/<candidate>.gif`，每次任务状态保存在 `project/production/batch/`。`ingested_unreviewed` 只代表真正的 GIF 已通过技术格式检查与入库；必须再人工审查镜头动作、叙事、风格与角色连续性。

仅允许本机回环 HTTP /v1 地址，API Key 只从环境变量读取，不记录到素材、回执或项目文件。上游返回普通 PNG/JPEG 或其他字节会拒绝，不制作假 GIF。生成的纵横比例仍需技术 QA，横屏图即使被后期加黑边也不能算原生 9:16 通过。

更多后端格式与通用任务恢复说明见 [GIF 调度协议](gif-generator-runtime.md)。
