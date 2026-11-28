#!/usr/bin/env bash
# Run AFTER applying chezmoi. Update a standalone mise, upgrade all shared agent
# tools (including Antigravity) and reconcile
# matching Plannotator, pinned Pi packages and Herdr integrations; stage desktop T3
# nightly on Omarchy hosts. Bun/.NET/pnpm also track latest; leave other runtimes,
# OAuth and project trust untouched.
# Herdr owns generated integrations, not chezmoi.
set -euo pipefail
case "$(hostname)" in omarchy|omarchy-laptop|dev-1) ;; *) echo 'Unknown host' >&2; exit 1;; esac
# Resolve sibling helpers before changing directories, including relative callers.
tools_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Bootstrap user-global declarations, not any project the caller is working in.
cd "$HOME"
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$PATH"
command -v mise >/dev/null
# A standalone mise (dev-1) updates itself; Omarchy's packaged mise updates with
# the system. Per-tool minimum_release_age and deferred pruning need a current mise.
if [[ "$(command -v mise)" == "$HOME/.local/bin/mise" ]]; then
  mise self-update --yes
fi
# Retire all Vite+ launchers, including its runtime and agent shims. Keep the
# installation and a private recovery backup; do not rewrite host shell files.
if [[ -e "$HOME/.vite-plus/bin" || -L "$HOME/.vite-plus/bin" ]]; then
  backup="$HOME/.local/state/vite-plus-launcher-backups/$(date +%Y%m%d-%H%M%S)-$$"
  mkdir -p -m 700 "$backup"
  mv "$HOME/.vite-plus/bin" "$backup/bin"
  printf 'Vite+ launcher recovery backup: %s\n' "$backup"
fi
# Refresh the opted-in runtimes and pnpm. Replaced versions are removed after
# upgrade.prune_after (24h); mise-prune.timer keeps versions still running.
mise cache clear bun dotnet pnpm
mise upgrade --global --yes bun dotnet pnpm
mise install bun dotnet pnpm
# Refresh coding-agent caches, with the same deferred pruning.
agents=(pi codex claude npm:@opencode/cli antigravity-cli github:herdrdev/herdr)
mise cache clear "${agents[@]}" github:backnotprop/plannotator
mise upgrade --global --yes "${agents[@]}"
# Upgrade Plannotator only after its Pi dependency and the other agents are ready.
mise upgrade --global --yes github:backnotprop/plannotator
# Install Plannotator last: its official installer detects the other agents.
mise install "${agents[@]}"
# Browser automation deliberately retains only the current version.
bash "$tools_dir/bootstrap-agent-browser.sh"
mise install github:backnotprop/plannotator
# REA follows latest but is disabled in agents: no MCP registration and no
# generated skills. Retire leftover skill trees into a private recovery backup.
mise cache clear npm:rea-agents
mise upgrade --global --yes npm:rea-agents
mise install npm:rea-agents
for skill in .agents/skills/reverse-engineer-anything .claude/skills/reverse-engineer-anything; do
  if [[ -e "$HOME/$skill" || -L "$HOME/$skill" ]]; then
    backup="${rea_backup:=$HOME/.local/state/rea-skill-install-backups/$(date +%Y%m%d-%H%M%S)-$$-disabled}"
    mkdir -p -m 700 "$backup/$(dirname "$skill")"
    mv "$HOME/$skill" "$backup/$skill"
    printf 'REA skill retired: %s\n' "$backup/$skill"
  fi
done
mise reshim
# T3 Code runs Antigravity through ~/.local/bin/agy (chezmoi pins binaryPath), so
# its own downloaded runtime is a stale duplicate. Retire it when nothing runs it.
if [[ -d "$HOME/.t3/tools/antigravity-acp" ]] && ! pgrep -f '[.]t3/tools/antigravity-acp/' >/dev/null; then
  # T3 marks its release files read-only.
  chmod -R u+w "$HOME/.t3/tools/antigravity-acp"
  rm -rf "$HOME/.t3/tools/antigravity-acp"
  echo 'Removed T3 Code managed Antigravity runtime; T3 uses ~/.local/bin/agy.'
fi
# One timer prunes every unused mise version (it replaced agent-browser-prune).
if systemctl --user is-enabled agent-browser-prune.timer >/dev/null 2>&1 \
  || [[ -L "$HOME/.config/systemd/user/timers.target.wants/agent-browser-prune.timer" ]]; then
  systemctl --user disable --now agent-browser-prune.timer 2>/dev/null \
    || rm -f "$HOME/.config/systemd/user/timers.target.wants/agent-browser-prune.timer"
fi
systemctl --user daemon-reload
systemctl --user enable --now mise-prune.timer
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
    systemctl --user enable --now t3code-nightly-update.timer grok-bot-update.timer
    # Stage packages asynchronously; never ask for root or quit Grok during sync.
    systemctl --user start --no-block grok-bot-update.service
    ;;
esac
