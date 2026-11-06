#!/usr/bin/env python3
"""Register actual GIF origin. This never generates an image or asserts visual quality."""
import argparse
import json
from pathlib import Path
from production_contract import register
from validate_storyboard import validate

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--storyboard", required=True)
    p.add_argument("--shot", required=True)
    p.add_argument("--kind", choices=("gpt_gif","programmatic","intentional_reuse"), required=True)
    p.add_argument("--tool", required=True, help="Actual tool used, not a guessed API")
    p.add_argument("--reference", required=True, help="Actual operation ID or artifact reference")
    p.add_argument("--prompt", help="Exact saved prompt, mandatory for gpt_gif")
    p.add_argument("--prompt-delivery", choices=("explicit_tool_argument","context_only_unverified"),
                   default="context_only_unverified",
                   help="Honest delivery mode; only a tool with a prompt argument can use explicit_tool_argument")
    a = p.parse_args()
    board = json.loads(Path(a.storyboard).read_text(encoding="utf-8"))
    problems = validate(board)
    if problems:
        raise ValueError("; ".join(problems))
    print(json.dumps(register(a.project, board, a.shot, a.kind, a.tool, a.reference, a.prompt, a.prompt_delivery),
                     ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
