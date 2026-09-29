#!/usr/bin/env python3
"""Interactively configure a private Telegram notification bot."""

from __future__ import annotations

import getpass
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, NoReturn
from urllib import error, parse, request

DEFAULT_TIMEOUT_SECONDS = 15


def fail(message: str) -> NoReturn:
    print(f"telegram-notify setup: {message}", file=sys.stderr)
    raise SystemExit(1)


def config_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return base / "telegram-notify" / "config"


def api_call(token: str, method: str, fields: dict[str, str] | None = None) -> Any:
    encoded_token = parse.quote(token, safe=":")
    url = f"https://api.telegram.org/bot{encoded_token}/{method}"
    body = parse.urlencode(fields or {}).encode("utf-8")
    api_request = request.Request(url, data=body, method="POST")
    try:
        with request.urlopen(api_request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            detail = payload.get("description", "request failed")
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            detail = "request failed"
        fail(f"Telegram rejected the request: {detail}")
    except error.URLError as exc:
        reason = getattr(exc, "reason", None)
        fail(f"could not reach Telegram: {reason or 'network error'}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        fail("Telegram returned a non-JSON response")

    if not isinstance(payload, dict) or payload.get("ok") is not True:
        detail = payload.get("description", "unknown error") if isinstance(payload, dict) else "unknown error"
        fail(f"Telegram rejected the request: {detail}")
    return payload.get("result")


def discover_chat_id(token: str) -> str | None:
    updates = api_call(
        token,
        "getUpdates",
        {
            "limit": "100",
            "timeout": "0",
            "allowed_updates": json.dumps(["message"]),
        },
    )
    if not isinstance(updates, list):
        return None

    for update in reversed(updates):
        if not isinstance(update, dict):
            continue
        message = update.get("message")
        if not isinstance(message, dict):
            continue
        chat = message.get("chat")
        if isinstance(chat, dict) and chat.get("id") is not None:
            return str(chat["id"])
    return None


def write_config(path: Path, token: str, chat_id: str) -> None:
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
            handle.write(f"TELEGRAM_BOT_TOKEN={token}\n")
            handle.write(f"TELEGRAM_CHAT_ID={chat_id}\n")
        os.replace(temporary_path, path)
        os.chmod(path, 0o600)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main() -> int:
    print(
        "Create a bot by messaging @BotFather in Telegram and using /newbot.\n"
        "Do not paste the token into an agent chat."
    )
    token = getpass.getpass("Bot token (hidden): ").strip()
    if not token:
        fail("bot token is empty")

    bot = api_call(token, "getMe")
    if not isinstance(bot, dict):
        fail("getMe returned an unexpected response")
    username = bot.get("username")
    if not isinstance(username, str) or not username:
        fail("bot has no username")

    print(f"\nOpen https://t.me/{username}, press Start, and send /start.")
    input("Press Enter here after the message has been sent: ")

    chat_id = discover_chat_id(token)
    if chat_id is None:
        chat_id = input(
            "No recent private chat was found. Enter the target chat ID: "
        ).strip()
    if not chat_id:
        fail("chat ID is empty")

    destination = config_path()
    write_config(destination, token, chat_id)
    print(f"Saved credentials to {destination} with mode 600.")

    api_call(
        token,
        "sendMessage",
        {"chat_id": chat_id, "text": "[Setup] Telegram notifications are working."},
    )
    print("Sent a test notification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
