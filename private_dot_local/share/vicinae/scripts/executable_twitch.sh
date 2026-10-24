#!/bin/bash
# @vicinae.schemaVersion 1
# @vicinae.title tw
# @vicinae.mode silent
# @vicinae.icon icons/twitch.svg
# @vicinae.keywords ["tw", "twitch", "mpv"]
# @vicinae.description Watch a Twitch channel in mpv at best quality (1080p60 source)
# @vicinae.argument1 { "type": "text", "placeholder": "channel" }

channel="${1,,}"
channel="${channel// /}"
setsid -f mpv --force-window=immediate --ytdl-format='best[height<=1080][fps<=60]/best' "https://www.twitch.tv/${channel}" >/dev/null 2>&1
echo "Opening ${channel} in mpv"
