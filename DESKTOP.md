# Omarchy desktop configuration

Deployment update: the lead integrated the exclusions below and applied the
profiles to both Omarchy hosts. Desktop file contents and active selections
were preserved. Asset storage was copied to the laptop and verified with
`tools/desktop-assets.py`; both hosts have zero missing mapped files. The source
root is now `private_dot_config`, and the inventories below describe the
initial source capture. No commits or pushes were made.

## Integration contract (lead-owned top-level ignore)

Only `omarchy` and `omarchy-laptop` may manage `.config/{hypr,omarchy,alacritty,kitty,ghostty,foot,uwsm}` and `.config/systemd/user/omarchy-agent-usage-cursor.{service,timer,path}`. Ignore these paths on **every other hostname**, especially Ubuntu `dev-1`. No OS-only fallback.

Additionally, on `omarchy`, ignore `.config/omarchy/plugins/ponbac.toki` and its descendants. This desktop path is an existing symlink to `/home/ponbac/dev/toki2/omarchy-plugin`, whose target exists. It is intentionally unmanaged: do not turn it into a directory or import the checkout. Laptop Toki is actual source files, managed only on `omarchy-laptop`. Fresh desktop provisioning must separately supply the checkout and link, or choose a reviewed packaged plugin.

For exact absence preservation, ignore these laptop-only paths on `omarchy`:
- `.config/omarchy/plugins/ponbac.idle` and descendants
- `.config/omarchy/plugins/ponbac.bar/ScreenSelection.js`
- `.config/omarchy/plugins/ponbac.bar/XpsScreenSelector.qml`

Ignore `.config/uwsm/env.d/99-nvidia-primary` on `omarchy-laptop`.

Host-only file templates also render empty off-host. Top-level ignore remains necessary, particularly for the Toki directory/symlink boundary. No `exact_` directories, removal entries, install scripts, or enablement symlinks are introduced.

## Preservation policy

Both hosts were inspected; laptop access was read-only SSH. Identical files are shared. Differing files include raw host-specific content from `.chezmoitemplates/desktop/<hostname>/<config-relative-path>`; raw content is not recursively rendered. Existing modes are preserved through `executable_` where needed.

Managed: current Hyprland Lua, `hyprsunset.conf` and `xdph.conf`; terminal preferences; UWSM defaults/env; shell layouts and idle behavior; custom bar, keyboard-layout and laptop idle/Toki plugins; branding, menu overrides and default agent; Cursor usage collector and its three unit definitions. The collector is source code only, not credentials or usage state. Units are included because they directly run the managed collector; no daemon reload or enablement is performed.

Excluded: obsolete Hyprland `.conf` files, old monitor-setup script (not referenced by current Lua), backups, sample/package setup hooks, generated theme/current state, auth, plugin documentation, caches, binaries, other theme checkouts, service enablement links and unrelated systemd units. Dependencies such as Omarchy Quattro, Vicinae, Omasnap, fonts, Cursor CLI and Toki credentials remain separately provisioned. Laptop Toki uses its local Python helper; credentials must stay outside this repo.

## Theme policy

See `.chezmoitemplates/desktop/theme-lock.json`. Metadata is informational, not an automatic checkout. Ayaka is pinned to `a2a4aec56fcbd06258464d73eacbe0ede12aa10c` at `https://github.com/ponbac/omarchy-ayaka-theme` on both hosts. Existing desktop deletions and untracked background are intentional and must survive.

Never reset, reclone over, clean, or strip `.git` from the live theme. Omarchy treats cloned themes differently when staging executable configuration. On a fresh host, a separately reviewed installer should clone only into an absent path, check out the pinned revision, retain `.git`, and restore that host's wallpaper mapping before explicitly selecting Ayaka. On an existing checkout it should only verify origin/revision/status and report discrepancies, never repair automatically. Theme activation/generated state are intentionally not managed by chezmoi.

## Validation and asset handoff

No live configuration apply, Hyprland reload, service change, Git commit, push, or remote creation was performed.

### Assets

Created a new local Git repository at `/home/ponbac/dev/omarchy-wallpapers` (previously absent), with no commits and no remote. `manifest.json` contains 28 desktop and 18 laptop home-relative paths, deduplicated into 26 image objects totaling 96,000,816 bytes. Includes user backgrounds, all four installed desktop themes' backgrounds, and laptop Ayaka backgrounds. Original live files/checkouts remain untouched. Each object hash, byte count and source-path content was verified. Desktop Ayaka deletions are informational `absent` entries, not executable removal instructions. Its untracked `wallhaven-lyje9y.png` is retained as an object and path mapping. A future reviewed restore/install flow is still needed; do not publish third-party images without reviewing rights.

### Validation

- Actual `chezmoi execute-template` confirmed absolute `include (joinPath .chezmoi.sourceDir ...)` returns raw bytes, with no recursive interpretation or extra newline.
- 120 host/file comparisons passed (55 desktop, 65 laptop), including private/executable target modes. JSON, Alacritty TOML, Python AST, Lua `luac -p`, and UWSM `bash -n` validation passed. No collector/plugin was executed.
- Isolated source archive validation with the required ignore contract passed for `omarchy` (55 files), `omarchy-laptop` (65), `dev-1` (zero) and an unknown host (zero). No archive was applied.
- The lead's current hostname gating already excludes desktop paths from `dev-1`. **The additional per-host exclusions above must still be integrated before apply.** Without them, desktop status would replace the Toki link/directory and remove its rendered-empty children. The isolated archive validation includes these exclusions; it is not a claim that the lead-owned ignore already includes them.
- A source-only capture does not warrant a live Hyprland reload, so runtime/QML integration was deliberately not tested. Rendering reproduces each host's current configuration, including existing differences; this is not a behavioral cleanup.

### Exact owned paths

`.chezmoitemplates/desktop/source-inventory.json` lists every imported source file (104 paths), including the three systemd units and every raw host variant. Additional owned files are `DESKTOP.md`, `.chezmoitemplates/desktop/theme-lock.json`, and `.chezmoitemplates/desktop/source-inventory.json` itself. All imported files are under `dot_config/{hypr,omarchy,alacritty,kitty,ghostty,foot,uwsm}`, the three `dot_config/systemd/user/omarchy-agent-usage-cursor.*` unit paths, or `.chezmoitemplates/desktop/`. No other systemd files were changed.

The separately approved asset-repo exception owns only `/home/ponbac/dev/omarchy-wallpapers/{.git,README.md,manifest.json,objects/}`; exact object filenames appear in that manifest. Pre-existing tracked deletions in the chezmoi worktree were not restored or modified. Top-level `.chezmoiignore`, `README.md` and deployment scripts remain lead-owned and were not edited.
