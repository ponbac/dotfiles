#!/bin/bash
# @vicinae.schemaVersion 1
# @vicinae.title nudge
# @vicinae.mode silent
# @vicinae.icon icons/nudge.svg
# @vicinae.keywords ["nudge", "grok", "bot"]
# @vicinae.description Send a reminder request to Nudge (Grok Bot), e.g. call mum 17:00
# @vicinae.argument1 { "type": "text", "placeholder": "reminder for Nudge" }

exec "$HOME/.local/bin/bot-hook" nudge "$1"
