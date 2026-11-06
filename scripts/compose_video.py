#!/usr/bin/env python3
"""Compose QA-approved GIF shots with captions and optional audio into MP4."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from gif_to_mp4 import convert
from generate_srt import render
from qa_gate import shot_quality
from validate_storyboard import validate


def run(cmd):
    subprocess.run(cmd, check=True)


def compose(project, storyboard, out, audio=None, burn=False,
            allow_unreviewed=False, duration_mode="hold"):
    project, out = Path(project).resolve(), Path(out).resolve()
    data = json.loads(Path(storyboard).read_text(encoding="utf-8"))
    problems = validate(data)
    if problems:
        raise ValueError("Invalid storyboard: " + "; ".join(problems))
    if duration_mode not in ("hold", "loop"):
        raise ValueError("Unknown duration mode")
    shots = data["shots"]
    width = int(data.get("width", 720))
    height = int(data.get("height", 1280))
    fps = int(data.get("fps", 24))
    if width % 2 or height % 2:
        raise ValueError("H.264 yuv420p requires even dimensions")
    clips, total = [], 0.0
    # Preflight *all* inputs before generating output.
    for shot in shots:
        source = project / "gifs" / (shot["id"] + ".gif")
        if not source.is_file():
            raise FileNotFoundError(source)
        status, reason = shot_quality(project, shot["id"])
        if status != "ready" and not allow_unreviewed:
            raise RuntimeError(f"Shot {shot['id']} blocked ({status}): {reason}")
    for shot in shots:
        src = project / "gifs" / (shot["id"] + ".gif")
        dst = project / "clips" / (shot["id"] + ".mp4")
        duration = float(shot["duration_sec"])
        convert(src, dst, duration, width, height, fps, mode=duration_mode)
        clips.append(dst)
        total += duration
    subtitle = project / "subtitles" / "captions.srt"
    subtitle.parent.mkdir(parents=True, exist_ok=True)
    subtitle.write_text(render(data), encoding="utf-8")
    build = project / "build"
    build.mkdir(parents=True, exist_ok=True)
    joined = build / "joined.mp4"
    listing = build / "clips.txt"
    def quote(p):
        return str(p).replace("'", "'\\''")
    listing.write_text("".join("file '"+quote(p.resolve())+"'\n" for p in clips),
                       encoding="utf-8")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "concat", "-safe", "0", "-i", str(listing),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(joined)])
    current = joined
    if burn:
        subtitled = build / "subtitled.mp4"
        arg = ("subtitles=" + str(subtitle).replace("\\", "\\\\")
               .replace(":", "\\:").replace("'", "\\'"))
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(current), "-vf", arg,
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(subtitled)])
        current = subtitled
    out.parent.mkdir(parents=True, exist_ok=True)
    if audio:
        audio = Path(audio).resolve()
        if not audio.is_file():
            raise FileNotFoundError(audio)
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(current), "-i", str(audio), "-filter_complex",
             "[1:a]apad[a]", "-map", "0:v:0", "-map", "[a]",
             "-c:v", "copy", "-c:a", "aac", "-t", str(total),
             "-movflags", "+faststart", str(out)])
    else:
        shutil.copyfile(current, out)
    info = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format",
         "-of", "json", str(out)], text=True))
    video = next((s for s in info.get("streams", [])
                  if s.get("codec_type") == "video"), None)
    if not video or video.get("codec_name") != "h264":
        raise RuntimeError("Final video is not H.264")
    if (video.get("width"), video.get("height")) != (width, height):
        raise RuntimeError("Final dimensions mismatch")
    if audio and not any(s.get("codec_type") == "audio" for s in info["streams"]):
        raise RuntimeError("Expected audio track missing")
    actual = float(info.get("format", {}).get("duration", 0))
    if abs(actual-total) > max(.25, 2/fps):
        raise RuntimeError(f"Final duration mismatch: {actual} vs {total}")
    (project/"build"/"delivery-report.json").write_text(
        json.dumps({"video": str(out), "duration_sec": actual,
                    "expected_duration_sec": total, "width": width, "height": height,
                    "fps": fps, "audio": bool(audio), "qa_enforced": not allow_unreviewed},
                   ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--storyboard", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--audio")
    p.add_argument("--burn-subtitles", action="store_true")
    p.add_argument("--allow-unreviewed", action="store_true",
                   help="Development only: bypass required technical + visual QA")
    p.add_argument("--duration-mode", choices=("hold","loop"), default="hold")
    a = p.parse_args()
    print(compose(a.project, a.storyboard, a.out, a.audio,
                  a.burn_subtitles, a.allow_unreviewed, a.duration_mode))


if __name__ == "__main__":
    main()
