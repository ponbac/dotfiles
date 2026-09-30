#!/usr/bin/env bash
# Run AFTER applying chezmoi. Ensure the four mise-managed coding agents and
# pinned Pi packages exist. Do not change other runtimes, OAuth, or project trust.
set -euo pipefail
case "$(hostname)" in omarchy|omarchy-laptop|dev-1) ;; *) echo 'Unknown host' >&2; exit 1;; esac
# Bootstrap user-global declarations, not any project the caller is working in.
cd "$HOME"
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"
command -v mise >/dev/null
mise install pi codex claude npm:@opencode/cli
mise reshim
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
