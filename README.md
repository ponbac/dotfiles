# Shared agent and development setup

Chezmoi source for exactly three hosts:

| Host | Profile |
|---|---|
| `omarchy` | Shared development + personal Omarchy desktop |
| `omarchy-laptop` | Shared development + personal Omarchy laptop |
| `dev-1` | Shared development only; Ubuntu |

Unknown hosts are denied by `.chezmoiignore`. No implicit OS-based fallback.

## Everyday workflow

Three commands are installed in `~/.local/bin/` on all three machines:

```sh
dotsync                           # fetch origin/master, fast-forward, preview and apply here
dotpush -m "chore(dotfiles): ..."   # review, commit source changes and push origin/master
dotdeploy --preview               # show the publish + remote-sync plan without changes
dotdeploy                         # publish to GitHub, then dotsync on the other machines
dotdeploy dev-1                   # optionally select one or more target hosts
```

`dotdeploy` defaults to the other known machines, excluding the current host.
After confirmation, it runs the `dotpush` workflow, then invokes `dotsync --yes`
over SSH on each target. Publication must succeed before any remote sync starts.
Use `-m` for a commit message, or `--yes` for an unattended run. Each remote sync
keeps its normal conflict checks, backups and Pi package reconciliation. Failed
hosts are reported while the remaining selected hosts are still attempted;
successful syncs and the GitHub publication are not rolled back. `--preview`
shows the local publication/target plan, not an ahead-of-time remote file diff.
Wallpaper assets remain separate. Specify the current hostname explicitly if
you also want to apply locally.

Git commands ask before applying/publishing. Pass `--yes` for an intentional unattended
run. `dotsync` also upgrades the four coding agents to latest and reconciles
pinned Pi packages on the current machine; it does not fan out over SSH. Run it on whichever machine should receive your changes.
`dotpush` does not apply the source locally; run `dotsync` there too if needed.

Edit files in the chezmoi source (`chezmoi cd`), or use `chezmoi edit <target>`.
For merge-managed settings, edit the policy files in `.chezmoitemplates/agents/`.
**Neither command automatically imports live home files.** In particular, never
bulk `chezmoi re-add`: live files can contain credentials and generated state.
New files must be deliberately selected/reviewed before `chezmoi add`.

The first publication of this rebuilt setup must be from the workstation:

```sh
dotpush -m "chore(dotfiles): rebuild shared agent and desktop setup"
# Then run dotsync on dev-1 and omarchy-laptop.
```

Their initial SSH-installed sources are uncommitted. `dotsync` can adopt the
published Git tree only if their source contents match it exactly and any local
history is an ancestor. It backs up original Git/index metadata first. Different
unpublished edits, divergent histories and remote-ahead pushes are refused;
there is no automatic stash, rebase, force-push, or destructive worktree reset.
Resolve real conflicts manually, then retry. Unknown hosts still have no managed
configuration. The wallpaper repository is separate and currently has no remote,
so these commands do not publish or pull wallpaper assets.

The old direct source-copy deployment is still available explicitly for
bootstrapping/recovery. Unlike `dotdeploy`, it bypasses GitHub and replaces remote
source edits after backing them up:

```sh
cd ~/.local/share/chezmoi
python3 tools/deploy.py                     # preview all three; paths, not secrets
python3 tools/deploy.py --apply --bootstrap  # config + pinned Pi packages on all three
python3 tools/deploy.py dev-1 --apply        # or config only on one host
```

Deployment stages the source over SSH, validates rendering, preserves each
remote's old source/Git history, backs up managed live files and chezmoi state,
and applies the declared files. `--bootstrap` additionally ensures the four
mise-managed coding agents are upgraded to latest and reconciles pinned Pi packages. It does not commit, push, enable services,
reload the desktop, or synchronize credentials. Requires Python 3.11+, Git,
rsync, chezmoi and SSH access. Backups are private under
`~/.local/state/chezmoi-deploy-backups/` on each host. The backup manifest records
which targets previously existed; restore existing targets from `targets/` and
remove newly created targets only after reviewing that manifest. Previous
directory permissions are recorded in `directory-modes.json`.

Prefer Git (`dotpush`/`dotsync`) for everyday multi-machine changes. The fallback
SSH deployment backs up, but does not merge, edits to a remote chezmoi source.
Bring those edits back and review them before using SSH deployment.

## What is managed

- Shared skill library and Claude-specific links/variants. Manual invocation
  flags and Codex invocation policies travel with the skills.
- Pi extensions, selected settings/model overrides, built-in MCP and pinned packages.
  The retired `pi-mcp-adapter` is not installed. Executor uses native HTTP bearer
  headers with `${EXECUTOR_MCP_TOKEN}` and direct tool exposure; the token stays local.
- Shared mise manifests and nonmutating launchers for Pi, Codex, Claude, OpenCode v2
  and Herdr. Herdr is pinned to stable **0.9.3**; the user-level mise install takes
  precedence over Omarchy's older system package without modifying it.
- Plannotator is pinned to **0.27.25** in `97-plannotator.toml`. Its mise tool-level
  postinstall runs the official installer from that exact release tag, with
  noninteractive mode and provenance verification. The installer owns its skills,
  slash commands and integrations; generated skill copies are excluded from
  chezmoi. Existing installer preferences (extras/model invocation) stay local.
  Before installing, local skills/configs are backed up under
  `~/.local/state/plannotator-install-backups/`. The installer also writes its
  matching `~/.local/bin/plannotator` copy; the hook verifies both binary versions.
  The Pi extension pin is kept at the same release and restored after installation.
- Selected Claude and Codex preferences and an entry-scoped Codex Plannotator hook.
  Herdr owns its generated agent scripts/plugins and its entries in shared hook
  configs. These files are not copied between hosts or overwritten by chezmoi.
  Explicit bootstrap backs up local integration files/configs, then reconciles
  Pi, Codex, Claude and OpenCode integrations using the installed Herdr release.
  Recovery manifests record existing and missing targets under
  `~/.local/state/herdr-integration-backups/`.
- Executor-only global MCP configuration for Pi, Claude, Codex and OpenCode v2.
  OpenCode's `opencode.json` owns MCP configuration; `opencode.jsonc` has its MCP
  section removed so it cannot reintroduce servers. Both preserve unrelated settings.
  All clients reference the host-local `EXECUTOR_MCP_TOKEN`; no token is synced.
- Clean shared Bash fragment, Git preferences, JJ, Herdr, tmux and Starship.
- Omarchy-only user configuration, custom plugins, terminal preferences and
  selected service definitions. Hardware/layout differences use host templates.

Agent `modify_` sources merge selected keys with current settings. They preserve
host-local tokens, project trust, desktop-generated Codex plugins/marketplaces,
and unrelated state. Global MCP server maps are replaced with executor only,
including removal of stale executor credentials/options. Project-local MCP
configuration is outside this policy and remains unmanaged.
Security/permission relaxations are not
promoted into shared defaults. Machine-specific runtime state therefore need
not be byte-identical for shared preferences to be consistent.

Bash startup and Git authentication are **not copied into this repo**. Two small
`modify_` scripts preserve their live contents and manage only a source line and
Git include. Some existing local startup files contain credentials: keep them
local, and do not paste complete diffs/rendered targets into issue trackers.
Managed top-level config/agent directories are private (0700).

## Packages and mise

```sh
bash ~/.local/share/chezmoi/tools/bootstrap-agents.sh
```

Run this on each host after changing Pi package pins, or pass `--bootstrap` to
the deployment command. It refreshes the four agents' release caches and upgrades
them to latest without pruning old installs, ensures the shared mise tools are
installed, reshims, installs current bundled Herdr integrations, and
reconciles the exact versions declared in Pi settings. It also retires the stale desktop-only Pi
extension on `dev-1` into a recovery backup. This is explicit, not an automatic
network/install hook on every chezmoi apply.

All three machines now use mise as the sole active installer for these agents:

- `~/.config/mise/conf.d/95-coding-agents.toml` declares Pi, Codex and Claude via
  mise's binary backends, and OpenCode **v2** via `npm:@opencode/cli`.
- `90-agent-release-policy.toml` exempts these tools from release-age delays.
- Agent versions remain `latest`, not fixed pins. Each sync/bootstrap checks for
  current releases; versions can drift between syncs or if a release appears
  during deployment. Plain `dotpush` publishes only source configuration.
- Bootstrap retires the entire `~/.vite-plus/bin` launcher directory into a
  private backup under `~/.local/state/vite-plus-launcher-backups/`. Vite+ runtime
  and agent launchers must not shadow mise. The rest of Vite+ stays untouched.
- Claude/OpenCode background auto-updaters are disabled so mise remains the
  update owner. Explicit manual update commands are not blocked.
- `~/.local/bin/{pi,codex,claude,opencode}` delegates to `mise exec` without
  writing globals, triggering `mise use`, or overriding age policy on launch.

Omarchy still owns shell/PATH activation. Unrelated global tool declarations,
Node/.NET/system runtimes, project overrides and trust paths remain host-local.
The old agent entries were removed from host globals/legacy conf.d files after
verification. Duplicate Node-global/npm-global installs, old OpenCode v1
binaries and the active native Claude install on dev-1 were removed. Recovery
backups live under `~/.local/state/agent-install-migration/`; credentials and
conversation/project data were not removed. Old mise versions of the retained
agent backends may remain as rollback versions.

Verified on all three (2026-09-29): Pi **0.99.1**, Codex **0.159.1**, Claude
**2.1.285**, OpenCode **2.0.19**. Codex's npm 0.159.1 Linux tarball was initially
unavailable; the binary release became available during migration and is now
installed through mise on all three machines.

Upgrade only these agents with:

```sh
mise cache clear pi codex claude npm:@opencode/cli
mise upgrade --yes --no-prune pi codex claude npm:@opencode/cli
```

Herdr upgrades are coordinated separately: update the stable pin in
`~/.config/mise/conf.d/96-herdr.toml` through its chezmoi source, then sync/bootstrap
all hosts. Do not run `herdr update` on this mise-managed installation. Existing
Herdr servers and pane processes are not stopped during installation; reconnect
clients and restart servers later only when their work can safely be interrupted.
Restart agent processes to load updated integrations.

For Plannotator, change the mise pin in `97-plannotator.toml` and the matching Pi
extension pin in `.chezmoitemplates/agents/pi-settings.json`, then sync/bootstrap.
A real `mise install` or upgrade invokes the official installer automatically;
an already-installed version is a no-op. To repair its generated skills and
integrations, use `mise install --force github:backnotprop/plannotator`.
Do not import or overwrite installer-owned skills with `chezmoi re-add`.

Do not use `mise upgrade opencode`: that registry name is the old v1 backend.
Do not install these agents globally with npm or the native Claude installer.
Pi extension packages remain separately pinned. `DEV.md` retains the original
runtime audit; this targeted agent consolidation supersedes its initial deferral.

## Ayaka and wallpapers

Ayaka revision is recorded in `.chezmoitemplates/desktop/theme-lock.json`.
Existing Git checkout state is preserved, including the desktop's local
wallpaper changes. Do not strip `.git`: Omarchy uses it when deciding theme trust.

Image content is outside this repository at `~/dev/omarchy-wallpapers`, in a
separate local Git repository: a SHA-256 object store plus host/path mappings.
Keep this repository private if published until image redistribution rights have
been reviewed. It has no remote or initial commit yet.

```sh
python3 tools/desktop-assets.py          # verify this Omarchy host
python3 tools/desktop-assets.py --apply  # restore missing files only
```

The asset helper refuses existing differing files and unsupported hosts. It can
clone the pinned Ayaka revision into an absent path, never reset a live checkout.
It never changes the active theme/wallpaper. Theme selection stays local.

To transport asset updates without deletions or Git-state replacement:

```sh
rsync -a --exclude=.git ~/dev/omarchy-wallpapers/ ponbac@omarchy-laptop:dev/omarchy-wallpapers/
ssh ponbac@omarchy-laptop 'python3 ~/.local/share/chezmoi/tools/desktop-assets.py'
```

Review/update asset manifest mappings deliberately before restoring new images.
No image assets or desktop configuration belong on `dev-1`.

## Deliberately excluded

OAuth/API secrets, authentication stores, histories, session databases, caches,
logs, project trust, Herdr workspaces, installed binaries/plugin caches, backups,
generated Omarchy state, old Hyprland configuration and package-owned defaults.
Desktop Toki's development-checkout symlink remains unmanaged; laptop plugin
source is managed. Service activation and missing application dependencies are
not silently provisioned.

See `DEV.md` and `DESKTOP.md` for inventory and preserved host differences. Their
original source-path inventories predate the private top-level directory prefixes.
