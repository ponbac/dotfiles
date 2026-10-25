#!/bin/bash
# @vicinae.schemaVersion 1
# @vicinae.title gon
# @vicinae.mode silent
# @vicinae.icon icons/gon.svg
# @vicinae.keywords ["gon", "grok", "bot"]
# @vicinae.description Send a message to Gon, the coding-agent switchboard (Grok Bot)
# @vicinae.argument1 { "type": "text", "placeholder": "message for Gon" }

exec "$HOME/.local/bin/bot-hook" gon "$1"
