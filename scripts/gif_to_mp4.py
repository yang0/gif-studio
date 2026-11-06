#!/usr/bin/env python3
"""Normalize GIF to an exact-length, constant-frame-rate H.264 video clip."""
import argparse
import subprocess
from pathlib import Path


def convert(source, dest, seconds, width=720, height=1280, fps=24):
    if seconds <= 0 or width <= 0 or height <= 0 or fps <= 0:
        raise ValueError("Positive seconds, dimensions and fps required")
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(source)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    vf = (f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,"
          f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,format=yuv420p")
    # -stream_loop -1 loops the GIF indefinitely; -t cuts to exact shot duration.
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-stream_loop", "-1", "-ignore_loop", "1", "-i", str(source),
           "-t", str(seconds), "-vf", vf, "-an", "-c:v", "libx264",
           "-pix_fmt", "yuv420p", "-r", str(fps), "-movflags", "+faststart", str(dest)]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--duration", required=True, type=float)
    ap.add_argument("--width", type=int, default=720)
    ap.add_argument("--height", type=int, default=1280)
    ap.add_argument("--fps", type=int, default=24)
    a = ap.parse_args()
    convert(a.input, a.output, a.duration, a.width, a.height, a.fps)


if __name__ == "__main__":
    main()
