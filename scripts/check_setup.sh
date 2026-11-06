#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import sys
assert sys.version_info >= (3, 10), "Python 3.10+ required"
print("[OK] Python", sys.version.split()[0])
try:
    import PIL
    print("[OK] Pillow", PIL.__version__)
except ImportError:
    raise SystemExit("[MISSING] Pillow: python3 -m pip install -r requirements.txt")
PY
for cmd in ffmpeg ffprobe; do
  if ! command -v "$cmd" >/dev/null 2>&1; then echo "[MISSING] $cmd"; exit 1; fi
  echo "[OK] $cmd"
done
echo "Local compositing environment ready. Check GIF generation capability separately inside Codex."
