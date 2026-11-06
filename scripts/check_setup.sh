#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("[MISSING] Python 3.10+")
print("[OK] Python", sys.version.split()[0])
try:
    import PIL
    print("[OK] Pillow", PIL.__version__)
except ImportError:
    raise SystemExit("[MISSING] Pillow: python3 -m pip install -r requirements.txt")
PY
for cmd in ffmpeg ffprobe; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "[MISSING] $cmd"; exit 1; }
  echo "[OK] $cmd"
done
ffmpeg -hide_banner -encoders 2>/dev/null | grep -q 'libx264' || { echo "[MISSING] libx264 encoder"; exit 1; }
echo "[OK] libx264"
if ffmpeg -hide_banner -filters 2>/dev/null | grep -q ' subtitles '; then
  echo "[OK] subtitles filter (libass)"
else
  echo "[WARNING] subtitles filter unavailable: use external SRT"
fi
echo "Local environment ready; actual Codex GIF generation capability must be checked separately."
