#!/usr/bin/env bash
# Run AFTER applying chezmoi. Ensure the four mise-managed coding agents and
# pinned Pi packages and Herdr integrations exist. Do not change other runtimes,
# OAuth, or project trust. Herdr owns generated integrations, not chezmoi.
set -euo pipefail
case "$(hostname)" in omarchy|omarchy-laptop|dev-1) ;; *) echo 'Unknown host' >&2; exit 1;; esac
# Bootstrap user-global declarations, not any project the caller is working in.
cd "$HOME"
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"
command -v mise >/dev/null
mise install pi codex claude npm:@opencode/cli github:herdrdev/herdr
mise reshim
# Back up local generated files and shared hook configs before reconciliation.
# Reject config-directory overrides: this setup deliberately manages $HOME.
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
# Local file installers only: no server stop, live handoff, or pane control.
for agent in pi codex claude opencode; do
  mise exec github:herdrdev/herdr -- herdr integration install "$agent"
done
command -v pi >/dev/null
# Built-in MCP replaces pi-mcp-adapter. A removed declaration alone leaves its
# old npm installation behind, so retire it after chezmoi applies the policy.
if [[ -d "$HOME/.pi/agent/npm/node_modules/pi-mcp-adapter" ]]; then
  npm --prefix "$HOME/.pi/agent/npm" uninstall --ignore-scripts --legacy-peer-deps pi-mcp-adapter
fi
# Clean up a desktop extension left by the old indiscriminate sync.
if [[ $(hostname) == dev-1 && -e "$HOME/.pi/agent/extensions/omarchy-system-theme.ts" ]]; then
  backup="$HOME/.local/state/chezmoi-deploy-backups/removed-desktop-extension-$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$backup"
  mv "$HOME/.pi/agent/extensions/omarchy-system-theme.ts" "$backup/"
fi
# `pi update` intentionally skips pinned sources, even if an older version is
# already present. Install only pins whose installed package metadata differs.
python3 - <<'PY'
import json
from pathlib import Path
import subprocess

home = Path.home()
settings = json.loads((home / '.pi/agent/settings.json').read_text())
for entry in settings.get('packages', []):
    source = entry['source'] if isinstance(entry, dict) else entry
    if not source.startswith('npm:'):
        raise SystemExit('Review non-npm package before provisioning: ' + source)
    name, separator, version = source[4:].rpartition('@')
    if not separator or not name or not version or version in ('latest', '*'):
        raise SystemExit('Package must have an explicit version: ' + source)
    package = home / '.pi/agent/npm/node_modules' / name / 'package.json'
    installed = json.loads(package.read_text()).get('version') if package.exists() else None
    if installed != version:
        subprocess.run(['pi', 'install', source, '--no-approve'], check=True)
    actual = json.loads(package.read_text()).get('version') if package.exists() else None
    if actual != version:
        raise SystemExit(f'Package reconciliation failed: {name}, expected {version}, got {actual}')
    print(f'{name}: {version} verified')
PY
