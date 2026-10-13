#!/usr/bin/env bash
# Run AFTER applying chezmoi. Upgrade all shared agent tools and reconcile
# matching Plannotator, pinned Pi packages and Herdr integrations; stage desktop T3
# nightly on Omarchy hosts. Do not change other runtimes, OAuth, or project trust.
# Herdr owns generated integrations, not chezmoi.
set -euo pipefail
case "$(hostname)" in omarchy|omarchy-laptop|dev-1) ;; *) echo 'Unknown host' >&2; exit 1;; esac
# Resolve sibling helpers before changing directories, including relative callers.
tools_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Bootstrap user-global declarations, not any project the caller is working in.
cd "$HOME"
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"
command -v mise >/dev/null
# Retire all Vite+ launchers, including its runtime and agent shims. Keep the
# installation and a private recovery backup; do not rewrite host shell files.
if [[ -e "$HOME/.vite-plus/bin" || -L "$HOME/.vite-plus/bin" ]]; then
  backup="$HOME/.local/state/vite-plus-launcher-backups/$(date +%Y%m%d-%H%M%S)-$$"
  mkdir -p -m 700 "$backup"
  mv "$HOME/.vite-plus/bin" "$backup/bin"
  printf 'Vite+ launcher recovery backup: %s\n' "$backup"
fi
# Refresh coding-agent caches; preserve old installs for running agents.
mise cache clear pi codex claude npm:@opencode/cli github:herdrdev/herdr github:backnotprop/plannotator
mise upgrade --global --yes --no-prune pi codex claude npm:@opencode/cli github:herdrdev/herdr
# Upgrade Plannotator only after its Pi dependency and the other agents are ready.
mise upgrade --global --yes --no-prune github:backnotprop/plannotator
# Install Plannotator last: its official installer detects the other agents.
mise install pi codex claude npm:@opencode/cli github:herdrdev/herdr
# Browser automation deliberately retains only the current version.
bash "$tools_dir/bootstrap-agent-browser.sh"
mise install github:backnotprop/plannotator
# REA is deliberately pinned; install without upgrading it or host runtimes.
# Its setup is skill-only: chezmoi already applied the shared MCP registrations.
mise install npm:rea-agents
python3 "$tools_dir/install-rea-skills.py" "$(mise where npm:rea-agents)"
mise reshim
# Reconcile bundled hooks even when Herdr was already installed (no postinstall).
bash "$tools_dir/install-herdr-integrations.sh" "$(mise where github:herdrdev/herdr)/herdr"
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
# Reconcile fixed Pi packages and the extension matching the installed Plannotator.
# Chezmoi preserves the extension's host-local release pin across applies.
python3 "$tools_dir/reconcile-pi-packages.py"
# Desktop T3 uses the same explicit sync workflow, with its own upstream update
# owner rather than mise's CLI backends. Only stage; never restart working T3.
case "$(hostname)" in
  omarchy|omarchy-laptop)
    t3code-nightly-update
    systemctl --user daemon-reload
    systemctl --user enable --now t3code-nightly-update.timer
    ;;
esac
