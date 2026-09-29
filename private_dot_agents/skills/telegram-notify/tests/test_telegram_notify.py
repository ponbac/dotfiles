from __future__ import annotations

import argparse
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib import error, request
from unittest import mock

SCRIPT = Path(__file__).parents[1] / "scripts" / "telegram_notify.py"
SPEC = importlib.util.spec_from_file_location("telegram_notify", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
telegram_notify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(telegram_notify)


class TelegramNotifyTest(unittest.TestCase):
    def test_builds_text_request(self) -> None:
        api_request = telegram_notify.build_request(
            "123:secret", "456", "hello world", False, None, None
        )

        self.assertTrue(api_request.full_url.endswith("/sendMessage"))
        self.assertEqual(
            api_request.headers["Content-type"],
            "application/x-www-form-urlencoded",
        )
        self.assertIn(b"text=hello+world", api_request.data)
        self.assertIn(b"disable_notification=false", api_request.data)

    def test_builds_image_multipart_request_with_caption(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "example.png"
            image.write_bytes(b"\x89PNG\r\n")

            api_request = telegram_notify.build_request(
                "123:secret", "456", "[Pi] done", True, "image", image
            )

        self.assertTrue(api_request.full_url.endswith("/sendPhoto"))
        self.assertTrue(
            api_request.headers["Content-type"].startswith("multipart/form-data;")
        )
        self.assertIn(b'name="photo"; filename="example.png"', api_request.data)
        self.assertIn(b"Content-Type: image/png", api_request.data)
        self.assertIn(b'[Pi] done', api_request.data)
        self.assertIn(b'disable_notification\"\r\n\r\ntrue', api_request.data)

    def test_builds_video_request_without_caption(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / "clip.mp4"
            video.write_bytes(b"video")

            api_request = telegram_notify.build_request(
                "123:secret", "456", "", False, "video", video
            )

        self.assertTrue(api_request.full_url.endswith("/sendVideo"))
        self.assertIn(b'name="video"; filename="clip.mp4"', api_request.data)
        self.assertNotIn(b'name="caption"', api_request.data)

    def test_media_caption_is_optional_and_source_can_stand_alone(self) -> None:
        args = argparse.Namespace(stdin=False, message=[], source=None)
        self.assertEqual(telegram_notify.build_message(args, "image"), "")

        args.source = "Pi"
        self.assertEqual(telegram_notify.build_message(args, "image"), "[Pi]")

    def test_rejects_caption_over_telegram_limit(self) -> None:
        args = argparse.Namespace(
            stdin=False,
            message=["x" * (telegram_notify.MAX_CAPTION_LENGTH + 1)],
            source=None,
        )
        with self.assertRaises(SystemExit):
            telegram_notify.build_message(args, "video")

    def test_dry_run_reports_media_without_sending(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "example.jpg"
            image.write_bytes(b"jpeg")
            argv = [
                str(SCRIPT),
                "--image",
                str(image),
                "--source",
                "Pi",
                "--dry-run",
                "caption",
            ]
            output = io.StringIO()
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.dict("os.environ", {}, clear=True),
                mock.patch("sys.stdout", output),
            ):
                self.assertEqual(telegram_notify.main(), 0)

        serialized = output.getvalue()
        result = json.loads(serialized)
        self.assertEqual(result["kind"], "image")
        self.assertEqual(result["caption"], "[Pi] caption")
        self.assertEqual(result["size"], 4)
        self.assertNotIn("chat_id", result)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", serialized)

    def test_rejects_empty_media(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "empty.jpg"
            image.touch()
            args = argparse.Namespace(image=image, video=None)
            with self.assertRaises(SystemExit):
                telegram_notify.media_from_args(args)

    def test_http_error_does_not_render_token(self) -> None:
        token = "123:distinctive-secret-token"
        api_request = request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=b"text=test"
        )
        response_body = io.BytesIO(
            b'{"ok":false,"description":"Bad Request: chat not found"}'
        )
        http_error = error.HTTPError(
            api_request.full_url, 400, "Bad Request", {}, response_body
        )
        stderr = io.StringIO()
        with (
            mock.patch.object(request, "urlopen", side_effect=http_error),
            mock.patch("sys.stderr", stderr),
            self.assertRaises(SystemExit),
        ):
            telegram_notify.send(api_request, 1)

        self.assertNotIn(token, stderr.getvalue())
        self.assertIn("chat not found", stderr.getvalue())

    def test_rejects_success_response_without_message_id(self) -> None:
        argv = [str(SCRIPT), "hello"]
        stderr = io.StringIO()
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.dict(
                "os.environ",
                {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat"},
                clear=True,
            ),
            mock.patch.object(
                telegram_notify, "send", return_value={"ok": True, "result": {}}
            ),
            mock.patch("sys.stderr", stderr),
            self.assertRaises(SystemExit),
        ):
            telegram_notify.main()

        self.assertIn("without a message ID", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
