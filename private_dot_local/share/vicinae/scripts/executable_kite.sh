#!/bin/bash
# @vicinae.schemaVersion 1
# @vicinae.title kite
# @vicinae.mode silent
# @vicinae.icon icons/kite.svg
# @vicinae.keywords ["kite", "grok", "bot"]
# @vicinae.description Send a request to Kite (Grok Bot); the reply shows up in the Kite chat
# @vicinae.argument1 { "type": "text", "placeholder": "message for Kite" }

exec "$HOME/.local/bin/bot-hook" kite "$1"
