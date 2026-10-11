#!/usr/bin/env bash
# Run after applying 98-agent-browser.toml. Keep one current installation only.
set -euo pipefail
cd "$HOME"
mise cache clear npm:agent-browser
mise upgrade --global --yes --no-prune npm:agent-browser
mise install npm:agent-browser
# Provision even if the CLI was already installed and postinstall did not run.
# System dependencies requiring sudo remain an explicit administrator action.
mise exec npm:agent-browser -- agent-browser install
mise exec npm:agent-browser -- agent-browser --version

# Remove only this package from known user-owned legacy global npm prefixes.
# Do not touch system packages, project dependencies, browsers, or profiles.
shopt -s nullglob
for prefix in "$HOME/.npm-global" "$HOME"/.local/share/mise/installs/node/*; do
  [[ -d "$prefix/lib/node_modules/agent-browser" ]] || continue
  npm uninstall --global --prefix "$prefix" --ignore-scripts agent-browser
done

# Do not prune any other tool. Refuse cleanup without one verified active version.
python3 - <<'PY'
import json
import subprocess

entries = json.loads(subprocess.check_output(
    ['mise', 'ls', '--installed', '--json', 'npm:agent-browser'], text=True))
active = [entry for entry in entries if entry.get('active') and entry.get('installed')]
if len(active) != 1:
    raise SystemExit('Expected one active agent-browser version; refusing version cleanup')
current = active[0]['version']
for entry in entries:
    if entry.get('installed') and entry['version'] != current:
        subprocess.run(['mise', 'uninstall', '--yes', 'npm:agent-browser@' + entry['version']], check=True)
print('Sole mise agent-browser version:', current)
PY
mise reshim
# Postinstall runs before mise finishes registering a version: prune afterwards,
# never recursively from that hook. The timer handles future automatic upgrades.
systemctl --user daemon-reload
systemctl --user enable --now agent-browser-prune.timer
