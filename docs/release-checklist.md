# 发布前检查

- [ ] `bash scripts/check_setup.sh` 完整通过
- [ ] `python3 scripts/validate_storyboard.py --storyboard templates/storyboard.json` 通过
- [ ] `python3 -m unittest discover -s tests -v` 通过
- [ ] 通过 GitHub Actions Python 3.10/3.11/3.12 CI
- [ ] 真实 Codex 会话能使用该 Skill，并确认 GIF 生成工具是否存在
- [ ] 至少生成一个知识镜头的静帧与 GIF 并查看逐帧 QA
- [ ] 使用 9:16 GIF、外部配音和 SRT 合成真实 H.264 视频
- [ ] 不能将静态脚本测试称为 GPT GIF 端到端测试
- [ ] CHANGELOG 与 README 已更新
