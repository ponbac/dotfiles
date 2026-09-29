#!/usr/bin/env python3
"""Adapt Codex's agent-turn-complete notification to telegram_notify.py."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

MAX_BODY_LENGTH = 3900


def main() -> int:
    if len(sys.argv) != 2:
        return 0
    try:
        event = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        return 0
    if not isinstance(event, dict) or event.get("type") != "agent-turn-complete":
        return 0

    cwd = event.get("cwd")
    summary = event.get("last-assistant-message")
    parts = ["Task finished."]
    if isinstance(cwd, str) and cwd:
        parts.append(f"Working directory: {cwd}")
    if isinstance(summary, str) and summary.strip():
        parts.append(summary.strip())
    message = "\n\n".join(parts)
    if len(message) > MAX_BODY_LENGTH:
        message = message[: MAX_BODY_LENGTH - 1].rstrip() + "…"

    sender = Path(__file__).with_name("telegram_notify.py")
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(sender),
                "--source",
                "Codex",
                "--stdin",
            ],
            input=message,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"codex telegram notification failed: {exc}", file=sys.stderr)
        return 0
    if completed.returncode != 0:
        print(completed.stderr.strip(), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
