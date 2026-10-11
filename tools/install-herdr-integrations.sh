#!/usr/bin/env bash
# Use the just-installed binary directly: never recurse into mise from its hook.
# File installers only: do not stop servers, hand off sessions, or control panes.
set -euo pipefail
binary="${1:?Expected the installed Herdr binary path}"
[[ -x "$binary" ]] || { echo "Missing Herdr binary: $binary" >&2; exit 1; }
# Serialize writers with Plannotator's hook; both touch shared agent configs.
mkdir -p "$HOME/.local/state"
exec 9>>"$HOME/.local/state/agent-integration-update.lock"
flock 9
python3 - <<'PY'
import datetime
import json
import os
from pathlib import Path
import shutil

home = Path.home()
for key, expected in {'PI_CODING_AGENT_DIR': home / '.pi/agent',
                      'CODEX_HOME': home / '.codex',
                      'CLAUDE_CONFIG_DIR': home / '.claude',
                      'XDG_CONFIG_HOME': home / '.config'}.items():
    value = os.environ.get(key)
    if value and Path(value).expanduser().resolve() != expected.resolve():
        raise SystemExit(f'Review {key} before installing home-scoped integrations')
files = ['.pi/agent/extensions/herdr-agent-state.ts',
         '.codex/herdr-agent-state.sh', '.codex/hooks.json', '.codex/config.toml',
         '.claude/hooks/herdr-agent-state.sh', '.claude/settings.json',
         '.config/opencode/plugins/herdr-agent-state.js',
         '.config/opencode/herdr-tui-session.js', '.config/opencode/herdr-opencode/tui.js',
         '.config/opencode/tui.json', '.config/opencode/tui.jsonc', '.config/opencode/cli.json']
backup = home / '.local/state/herdr-integration-backups' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
backup.mkdir(parents=True, mode=0o700)
existing = []
for name in files:
    source = home / name
    if source.exists():
        target = backup / name
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copy2(source, target)
        target.chmod(0o600)
        existing.append(name)
(backup / 'manifest.json').write_text(json.dumps({'existing': existing, 'targets': files}, indent=2))
print('Herdr integration recovery backup:', backup)
PY
for agent in pi codex claude opencode; do
  "$binary" integration install "$agent"
done
