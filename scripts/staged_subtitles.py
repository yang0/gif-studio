"""Portable FFmpeg subtitles-filter input avoiding Windows drive-colon parsing.

FFmpeg filter expressions treat colons as option separators even when Python
subprocess uses argument arrays. Stage an ASCII relative filename and run the
filter from its own working directory; original SRT and its SHA stay unchanged.
"""
from pathlib import Path

def prepare(subtitles, work):
    path=Path(subtitles).resolve()
    if not path.is_file():
        raise FileNotFoundError("Actual subtitle source is missing")
    folder=Path(work).resolve()
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/"gif-studio-burnin.srt"
    target.write_bytes(path.read_bytes())
    return "subtitles=gif-studio-burnin.srt",folder
