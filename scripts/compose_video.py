#!/usr/bin/env python3
"""Build shot clips, SRT and final MP4. Uses only local ffmpeg and standard Python."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from gif_to_mp4 import convert
from generate_srt import render


def run(cmd):
    subprocess.run(cmd, check=True)


def compose(project, storyboard, out, audio=None, burn=False):
    project, out = Path(project).resolve(), Path(out).resolve()
    data = json.loads(Path(storyboard).read_text(encoding="utf-8"))
    shots = data.get("shots", [])
    if not shots:
        raise ValueError("No storyboard shots")
    width, height, fps = (int(data.get("width", 720)), int(data.get("height", 1280)),
                          int(data.get("fps", 24)))
    clips, total = [], 0.0
    for shot in shots:
        shot_id = str(shot["id"])
        if not shot_id or "/" in shot_id or "\\" in shot_id or shot_id in (".", ".."):
            raise ValueError("Invalid shot id")
        dur = float(shot["duration_sec"])
        if dur <= 0:
            raise ValueError("Duration must be positive")
        src = project / "gifs" / (shot_id + ".gif")
        dst = project / "clips" / (shot_id + ".mp4")
        convert(src, dst, dur, width, height, fps)
        clips.append(dst)
        total += dur

    subtitle = project / "subtitles" / "captions.srt"
    subtitle.parent.mkdir(parents=True, exist_ok=True)
    subtitle.write_text(render(data), encoding="utf-8")
    build = project / "build"
    build.mkdir(parents=True, exist_ok=True)
    joined = build / "joined.mp4"
    # concat demuxer uses normalized clips; rebuild timeline instead of copy to avoid timestamp oddities.
    listing = build / "clips.txt"
    def quote(p):
        return str(p).replace("'", "'\\''")
    listing.write_text("".join("file '" + quote(p.resolve()) + "'\n" for p in clips), encoding="utf-8")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(joined)])

    current = joined
    if burn:
        # Use a relative SRT from the project working directory to minimize escaping issues.
        # ffmpeg subtitles filter needs libass support.
        subtitled = build / "subtitled.mp4"
        subtitle_filter = "subtitles=filename='subtitles/captions.srt'"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(current), "-vf", subtitle_filter, "-c:v", "libx264",
             "-pix_fmt", "yuv420p", "-an", str(subtitled)] if False else
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(current), "-vf", "subtitles=" + str(subtitle).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'"),
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(subtitled)])
        current = subtitled

    out.parent.mkdir(parents=True, exist_ok=True)
    if audio:
        audio = Path(audio).resolve()
        if not audio.is_file():
            raise FileNotFoundError(audio)
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(current), "-i", str(audio),
             "-filter_complex", "[1:a]apad[a]", "-map", "0:v:0", "-map", "[a]",
             "-c:v", "copy", "-c:a", "aac", "-t", str(total),
             "-movflags", "+faststart", str(out)])
    else:
        shutil.copyfile(current, out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--storyboard", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--audio")
    ap.add_argument("--burn-subtitles", action="store_true")
    a = ap.parse_args()
    print(compose(a.project, a.storyboard, a.out, a.audio, a.burn_subtitles))


if __name__ == "__main__":
    main()
