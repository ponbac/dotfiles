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
run. `dotsync` also reconciles pinned Pi packages on the current machine; it does
not fan out over SSH. Run it on whichever machine should receive your changes.
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
mise-managed coding agents are installed and reconciles pinned Pi packages. It does not commit, push, enable services,
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
- Pi extensions, selected settings/model overrides, MCP and pinned packages.
- A shared mise manifest and nonmutating launchers for Pi, Codex, Claude and OpenCode v2.
- Selected Claude and Codex preferences, MCP entries, and Codex hooks.
- Clean shared Bash fragment, Git preferences, JJ, Herdr, tmux and Starship.
- Omarchy-only user configuration, custom plugins, terminal preferences and
  selected service definitions. Hardware/layout differences use host templates.

Agent `modify_` sources merge selected keys with current settings. They preserve
host-local tokens, project trust, desktop-generated Codex plugins/marketplaces,
other MCP servers and unrelated state. Security/permission relaxations are not
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
the deployment command. It installs the four agents selected by the shared
mise manifest, reshims, and reconciles the exact versions declared in Pi settings. It also retires the stale desktop-only Pi
extension on `dev-1` into a recovery backup. This is explicit, not an automatic
network/install hook on every chezmoi apply.

All three machines now use mise as the sole active installer for these agents:

- `~/.config/mise/conf.d/95-coding-agents.toml` declares Pi, Codex and Claude via
  mise's binary backends, and OpenCode **v2** via `npm:@opencode/cli`.
- `90-agent-release-policy.toml` exempts these tools from release-age delays.
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

Verified on all three (2026-09-29): Pi **0.99.1**, Codex **0.159.0**, Claude
**2.1.285**, OpenCode **2.0.19**. Codex's npm 0.159.1 Linux tarball was unavailable;
the binary backend currently supplies working 0.159.0.

Upgrade only these agents with:

```sh
mise upgrade pi codex claude npm:@opencode/cli
```

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
