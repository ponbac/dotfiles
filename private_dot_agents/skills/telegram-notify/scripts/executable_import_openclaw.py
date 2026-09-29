#!/usr/bin/env python3
"""Import an OpenClaw Telegram bot token over SSH without displaying it."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
from typing import NoReturn

ALLOWED_CONFIG_KEYS = {"TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"}
HOST_PATTERN = re.compile(r"^[A-Za-z0-9_.@-]+$")
TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9_-])([0-9]{6,}:[A-Za-z0-9_-]{20,})")
CHAT_PATTERN = re.compile(r"^(?:-?[0-9]+|@[A-Za-z0-9_]+)$")


def fail(message: str) -> NoReturn:
    print(f"telegram-notify import: {message}", file=os.sys.stderr)
    raise SystemExit(1)


def default_config_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return base / "telegram-notify" / "config"


def read_existing(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    if not path.is_file():
        fail(f"configuration path is not a regular file: {path}")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        fail(f"configuration permissions must be 600 or stricter: {path}")

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or key not in ALLOWED_CONFIG_KEYS:
            fail(f"invalid entry on line {line_number} of {path}")
        values[key] = value
    return values


def fetch_token(host: str) -> str:
    if not HOST_PATTERN.fullmatch(host):
        fail("SSH host may contain only letters, digits, dot, underscore, @, or hyphen")

    remote_command = (
        "python3 -c 'import json,pathlib; "
        'p=pathlib.Path.home()/".openclaw"/"openclaw.json"; '
        'print(json.loads(p.read_text())["channels"]["telegram"]["botToken"])\''
    )
    try:
        completed = subprocess.run(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=10",
                host,
                remote_command,
            ],
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        fail("could not execute the SSH import")

    # Never include stdout, stderr, or the completed command in an error:
    # OpenClaw's output can contain the token.
    if completed.returncode != 0:
        fail("OpenClaw did not return a Telegram bot token")

    matches = TOKEN_PATTERN.findall(completed.stdout)
    if len(set(matches)) != 1:
        fail("OpenClaw returned no unique Telegram bot token")
    return matches[0]


def write_config(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".config-", dir=path.parent, text=True
    )
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
                value = values.get(key)
                if value:
                    handle.write(f"{key}={value}\n")
        os.replace(temporary_path, path)
        os.chmod(path, 0o600)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import an OpenClaw Telegram token over SSH."
    )
    parser.add_argument("--host", required=True, help="SSH destination")
    parser.add_argument("--chat-id", help="optional Telegram chat ID or @username")
    parser.add_argument(
        "--config", type=Path, default=default_config_path(), help="credential file"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.chat_id and not CHAT_PATTERN.fullmatch(args.chat_id):
        fail("--chat-id must be a numeric Telegram chat ID or @username")

    values = read_existing(args.config)
    values["TELEGRAM_BOT_TOKEN"] = fetch_token(args.host)
    if args.chat_id:
        values["TELEGRAM_CHAT_ID"] = args.chat_id
    write_config(args.config, values)

    print(f"Imported the OpenClaw Telegram token into {args.config} with mode 600.")
    if "TELEGRAM_CHAT_ID" not in values:
        print("Telegram chat ID is not configured yet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
