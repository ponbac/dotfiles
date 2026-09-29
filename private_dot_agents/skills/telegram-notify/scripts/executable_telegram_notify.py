#!/usr/bin/env python3
"""Send one text, image, or video notification through the Telegram Bot API."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
from pathlib import Path
import secrets
import stat
import sys
from typing import NoReturn
from urllib import error, parse, request

MAX_TEXT_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 60
ALLOWED_CONFIG_KEYS = {"TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"}


def fail(message: str) -> NoReturn:
    print(f"telegram-notify: {message}", file=sys.stderr)
    raise SystemExit(1)


def default_config_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return base / "telegram-notify" / "config"


def read_config(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    if not path.is_file():
        fail(f"configuration path is not a regular file: {path}")

    permissions = stat.S_IMODE(path.stat().st_mode)
    if permissions & 0o077:
        fail(f"configuration permissions must be 600 or stricter: {path}")

    values: dict[str, str] = {}
    try:
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
    except OSError as exc:
        fail(f"could not read configuration: {exc.strerror or exc}")
    return values


def load_credentials(path: Path) -> tuple[str, str]:
    environment_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    environment_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if environment_token and environment_chat_id:
        return environment_token, environment_chat_id

    config = read_config(path)
    token = environment_token or config.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = environment_chat_id or config.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        fail(
            "missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID; "
            "run scripts/configure.py in your own terminal"
        )
    return token, chat_id


def media_limit(kind: str) -> int:
    return MAX_IMAGE_BYTES if kind == "image" else MAX_VIDEO_BYTES


def inspect_media(kind: str, path: Path) -> int:
    try:
        with path.open("rb") as media_file:
            file_stat = os.fstat(media_file.fileno())
    except OSError as exc:
        fail(f"could not open {kind}: {exc.strerror or exc}")
    if not stat.S_ISREG(file_stat.st_mode):
        fail(f"{kind} path is not a regular file: {path}")
    size = file_stat.st_size
    if size == 0:
        fail(f"{kind} file is empty: {path}")
    maximum = media_limit(kind)
    if size > maximum:
        fail(
            f"{kind} is {size} bytes; Telegram permits at most {maximum} bytes "
            "for bot uploads"
        )
    return size


def media_from_args(args: argparse.Namespace) -> tuple[str | None, Path | None]:
    if args.image is not None:
        kind, path = "image", args.image.expanduser()
    elif args.video is not None:
        kind, path = "video", args.video.expanduser()
    else:
        return None, None

    inspect_media(kind, path)
    return kind, path


def build_message(args: argparse.Namespace, media_kind: str | None) -> str:
    if args.stdin:
        if args.message:
            fail("pass the message either as arguments or with --stdin, not both")
        message = sys.stdin.read()
    else:
        message = " ".join(args.message)

    message = message.strip()
    if not message and media_kind is None:
        fail("message is empty")

    if args.source:
        message = f"[{args.source}] {message}" if message else f"[{args.source}]"

    maximum = MAX_CAPTION_LENGTH if media_kind else MAX_TEXT_LENGTH
    label = "caption" if media_kind else "message"
    if len(message) > maximum:
        fail(
            f"{label} is {len(message)} characters; Telegram permits at most "
            f"{maximum}"
        )
    return message


def parse_response(payload: bytes) -> dict[str, object]:
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        fail(
            "Telegram returned a non-JSON response; delivery is unknown, so it "
            "was not retried"
        )
    if not isinstance(parsed, dict):
        fail(
            "Telegram returned an unexpected response; delivery is unknown, so "
            "it was not retried"
        )
    return parsed


def telegram_error_description(payload: bytes) -> str:
    try:
        parsed = json.loads(payload.decode("utf-8"))
        if isinstance(parsed, dict) and isinstance(parsed.get("description"), str):
            return parsed["description"]
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    return "request failed"


def multipart_body(
    fields: dict[str, str],
    file_field: str,
    file_path: Path,
    content_type: str,
    media_kind: str,
) -> tuple[bytearray, str]:
    boundary = f"telegram-notify-{secrets.token_hex(16)}"
    boundary_bytes = boundary.encode("ascii")
    body = bytearray()

    for name, value in fields.items():
        body.extend(b"--" + boundary_bytes + b"\r\n")
        body.extend(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(
                "ascii"
            )
        )
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")

    # Strip control characters and quote metacharacters before placing a local
    # filename in a multipart header. Telegram does not need the full path.
    filename = file_path.name.replace("\\", "_").replace('"', "_")
    filename = "".join(character for character in filename if ord(character) >= 32)
    body.extend(b"--" + boundary_bytes + b"\r\n")
    body.extend(
        (
            f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{filename}"\r\n'
        ).encode("utf-8")
    )
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("ascii"))

    maximum = media_limit(media_kind)
    total = 0
    try:
        with file_path.open("rb") as media_file:
            if not stat.S_ISREG(os.fstat(media_file.fileno()).st_mode):
                fail(f"{media_kind} path is not a regular file: {file_path}")
            while chunk := media_file.read(64 * 1024):
                total += len(chunk)
                if total > maximum:
                    fail(
                        f"{media_kind} exceeds Telegram's {maximum}-byte bot "
                        "upload limit"
                    )
                body.extend(chunk)
    except OSError as exc:
        fail(f"could not read {media_kind}: {exc.strerror or exc}")
    if total == 0:
        fail(f"{media_kind} file is empty: {file_path}")

    body.extend(b"\r\n--" + boundary_bytes + b"--\r\n")
    return body, boundary


def build_request(
    token: str,
    chat_id: str,
    text: str,
    silent: bool,
    media_kind: str | None,
    media_path: Path | None,
) -> request.Request:
    encoded_token = parse.quote(token, safe=":")
    fields = {
        "chat_id": chat_id,
        "disable_notification": "true" if silent else "false",
    }

    if media_kind is None:
        url = f"https://api.telegram.org/bot{encoded_token}/sendMessage"
        fields["text"] = text
        body = parse.urlencode(fields).encode("utf-8")
        content_type = "application/x-www-form-urlencoded"
    else:
        if media_path is None:
            raise AssertionError("media path is required for a media request")
        method = "sendPhoto" if media_kind == "image" else "sendVideo"
        file_field = "photo" if media_kind == "image" else "video"
        if text:
            fields["caption"] = text
        guessed_type = mimetypes.guess_type(media_path.name)[0]
        fallback_type = "image/jpeg" if media_kind == "image" else "video/mp4"
        body, boundary = multipart_body(
            fields,
            file_field,
            media_path,
            guessed_type or fallback_type,
            media_kind,
        )
        url = f"https://api.telegram.org/bot{encoded_token}/{method}"
        content_type = f"multipart/form-data; boundary={boundary}"

    return request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": content_type},
    )


def send(api_request: request.Request, timeout: int) -> dict[str, object]:
    try:
        with request.urlopen(api_request, timeout=timeout) as response:
            parsed = parse_response(response.read())
    except error.HTTPError as exc:
        # Avoid rendering the exception itself: its URL contains the bot token.
        fail(f"Telegram rejected the request: {telegram_error_description(exc.read())}")
    except error.URLError as exc:
        reason = getattr(exc, "reason", None)
        fail(
            "Telegram transport failed; delivery is unknown, so it was not "
            f"retried: {reason or 'network error'}"
        )
    except TimeoutError:
        fail("Telegram request timed out; delivery is unknown, so it was not retried")

    if parsed.get("ok") is not True:
        description = parsed.get("description")
        fail(
            "Telegram rejected the request: "
            + (description if isinstance(description, str) else "unknown error")
        )
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send one text, image, or video Telegram notification."
    )
    parser.add_argument("message", nargs="*", help="message text or media caption")
    parser.add_argument("--source", help="agent label to prefix")
    parser.add_argument("--silent", action="store_true", help="send without sound")
    parser.add_argument(
        "--stdin", action="store_true", help="read the message or caption from stdin"
    )
    media = parser.add_mutually_exclusive_group()
    media.add_argument("--image", type=Path, help="upload one image file")
    media.add_argument(
        "--video", type=Path, help="upload one video (Telegram requires MPEG-4)"
    )
    parser.add_argument(
        "--config", type=Path, default=default_config_path(), help="credential file"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="request timeout in seconds",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and print non-secret request metadata without sending",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.timeout <= 0:
        fail("--timeout must be positive")
    media_kind, media_path = media_from_args(args)
    message = build_message(args, media_kind)

    if args.dry_run:
        output: dict[str, object] = {
            "ok": True,
            "dry_run": True,
            "kind": media_kind or "text",
            "silent": args.silent,
        }
        if media_path is None:
            output["text"] = message
        else:
            output.update(
                {
                    "caption": message,
                    "path": str(media_path),
                    "size": media_path.stat().st_size,
                }
            )
        print(json.dumps(output, ensure_ascii=False))
        return 0

    token, chat_id = load_credentials(args.config)
    api_request = build_request(
        token, chat_id, message, args.silent, media_kind, media_path
    )
    response = send(api_request, args.timeout)
    result = response.get("result")
    message_id = result.get("message_id") if isinstance(result, dict) else None
    if not isinstance(message_id, int) or isinstance(message_id, bool):
        fail(
            "Telegram returned success without a message ID; delivery may have "
            "succeeded, so it was not retried"
        )
    print(
        json.dumps(
            {"ok": True, "message_id": message_id, "kind": media_kind or "text"}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
