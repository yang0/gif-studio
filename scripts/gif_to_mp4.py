#!/usr/bin/env python3
"""GIF to exact-duration MP4: default play once and hold the final frame."""
import argparse
import subprocess
from pathlib import Path


def convert(source, dest, seconds, width=720, height=1280, fps=24, mode="hold"):
    if seconds <= 0 or width <= 0 or height <= 0 or fps <= 0:
        raise ValueError("Positive duration, dimensions and fps required")
    if mode not in ("hold", "loop"):
        raise ValueError("mode must be hold or loop")
    source, dest = Path(source), Path(dest)
    if not source.is_file():
        raise FileNotFoundError(source)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sizing = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
              f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
              f"setsar=1")
    # Hold: decoder consumes one GIF playback, tpad clones the last displayed frame.
    # Loop: repeat GIF only if it was designed to be seamless.
    timeline = f"fps={fps},{sizing},tpad=stop_mode=clone:stop_duration={seconds},format=yuv420p" if mode == "hold" else f"fps={fps},{sizing},format=yuv420p"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if mode == "loop":
        cmd += ["-stream_loop", "-1"]
    cmd += ["-ignore_loop", "1", "-i", str(source),
            "-vf", timeline, "-t", str(seconds), "-an", "-c:v", "libx264",
            "-r", str(fps), "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(dest)]
    subprocess.run(cmd, check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--duration", type=float, required=True)
    p.add_argument("--width", type=int, default=720)
    p.add_argument("--height", type=int, default=1280)
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--duration-mode", choices=["hold","loop"], default="hold")
    a = p.parse_args()
    convert(a.input, a.output, a.duration, a.width, a.height, a.fps, a.duration_mode)


if __name__ == "__main__":
    main()
