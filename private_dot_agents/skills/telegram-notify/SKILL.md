---
name: telegram-notify
description: Send the user a concise Telegram message, image, or video through their private notification bot. Use when the user explicitly asks to be messaged, notified, pinged, sent media, or sent a status update on Telegram, including a request to notify them when the current task finishes or becomes blocked. Do not use for unrequested notifications.
---

# Telegram Notify

Send exactly one concise text or media notification only when the user has
explicitly requested it.

## Send a message

1. Finish the requested work, or determine the concrete blocker.
2. Compose a self-contained plain-text update. Include the agent name, outcome,
   and only the detail needed to act. Do not send secrets, credentials, private
   file contents, raw logs, or speculative claims.
3. Keep the complete message at or below 4,096 characters. Prefer a short
   summary and a path, URL, command, or next action over a transcript.
4. Run the bundled sender once:

   ```bash
   python3 "$HOME/.agents/skills/telegram-notify/scripts/telegram_notify.py" \
     --source "<Codex|Pi|OpenCode>" --stdin <<'TELEGRAM_MESSAGE'
   <message>
   TELEGRAM_MESSAGE
   ```

5. Treat a successful JSON response as delivery confirmation. If delivery
   fails, report the error to the user in the normal conversation. Do not retry
   an ambiguous result because that can create duplicate messages.

Use `--silent` only when the user asks for a silent notification.

## Send an image or video

Send one local image or one local MP4 video by adding `--image <path>` or
`--video <path>`. The options are mutually exclusive. Before sending, verify
that the chosen file is the media the user requested and does not expose
secrets, credentials, private file contents, or unrelated personal data.

A message supplied as arguments or through `--stdin` becomes the media caption.
Captions are optional unless context is needed, and may be at most 1,024
characters including the source prefix.

```bash
# Image with a caption
python3 "$HOME/.agents/skills/telegram-notify/scripts/telegram_notify.py" \
  --source "<Codex|Pi|OpenCode>" --image "/absolute/path/to/image.png" \
  --stdin <<'TELEGRAM_CAPTION'
<caption>
TELEGRAM_CAPTION

# Video without a caption
python3 "$HOME/.agents/skills/telegram-notify/scripts/telegram_notify.py" \
  --video "/absolute/path/to/video.mp4"
```

The sender validates that the file is non-empty and within Telegram's standard
Bot API upload limits: 10 MiB for an image and 50 MiB for a video. Telegram
performs final image-format/dimension validation and requires MPEG-4 for
`sendVideo`. Treat the single JSON response exactly like a text-message
response, and do not retry an ambiguous failure.

## Missing configuration

If the sender reports missing configuration, tell the user to run this in
their own terminal:

```bash
python3 "$HOME/.agents/skills/telegram-notify/scripts/configure.py"
```

When the user explicitly asks to copy an existing OpenClaw Telegram bot token,
use `scripts/import_openclaw.py --host <ssh-user@host>`. This transfers the
token through SSH without displaying it. Pass `--chat-id <id>` only after the
target has been identified unambiguously.

Never ask the user to paste a bot token into the agent conversation. Never read
or display the credential file. The configuration helper stores credentials in
`${XDG_CONFIG_HOME:-$HOME/.config}/telegram-notify/config` with user-only
permissions.

## Automatic completion notifications

This skill supports explicit, model-initiated messages. Automatic notification
after every run requires a host lifecycle adapter. Read
`references/automatic-completion.md` only when the user asks to install,
enable, disable, or troubleshoot automatic completion notifications.
