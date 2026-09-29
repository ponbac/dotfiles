# Automatic completion notifications

The shared skill handles explicit requests such as “Telegram me when this is
done.” To notify after every run without model involvement, connect the host's
lifecycle mechanism to the bundled sender.

Run `scripts/configure.py` before enabling any adapter.

## Codex

Add the following top-level setting to `~/.codex/config.toml`, replacing the
path with the absolute path to this skill:

```toml
notify = ["python3", "/home/USER/.agents/skills/telegram-notify/scripts/codex_notify.py"]
```

Codex passes an `agent-turn-complete` JSON payload to the adapter. Restart
Codex after changing the configuration.

## Pi

Pi automatically loads TypeScript extensions from
`~/.pi/agent/extensions/`. Link the bundled adapter:

```bash
mkdir -p "$HOME/.pi/agent/extensions"
ln -s "$HOME/.agents/skills/telegram-notify/scripts/pi_notify.ts" \
  "$HOME/.pi/agent/extensions/telegram-notify.ts"
```

The adapter sends a message on `agent_end`.

## OpenCode

OpenCode automatically loads JavaScript or TypeScript plugins from
`~/.config/opencode/plugins/`. Link the bundled adapter:

```bash
mkdir -p "$HOME/.config/opencode/plugins"
ln -s "$HOME/.agents/skills/telegram-notify/scripts/opencode_notify.js" \
  "$HOME/.config/opencode/plugins/telegram-notify.js"
```

The adapter sends a message on `session.idle` and `session.error`.

## Disable

Remove the relevant Codex `notify` entry or adapter symlink. The shared skill
and sender can remain installed for explicit notifications.

Automatic adapters notify on every matching lifecycle event. This can be noisy
and may send summaries or working-directory paths to Telegram. Enable only the
adapters whose behavior you want.
