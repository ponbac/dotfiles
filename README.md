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
mise-managed coding agents are upgraded to latest, reconciles pinned Pi packages,
and on Omarchy desktops stages the T3 nightly and enables its update timer.
It does not commit, push, enable unrelated services, reload the desktop, or
synchronize credentials. Requires Python 3.11+, Git,
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
- Global agent instructions: `.chezmoitemplates/agents/global-instructions.md`
  renders to `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.pi/agent/AGENTS.md`
  and `~/.config/opencode/AGENTS.md`.
- Pi extensions, selected settings/model overrides, built-in MCP and pinned packages.
  The retired `pi-mcp-adapter` is not installed. Executor uses native HTTP bearer
  headers with `${EXECUTOR_MCP_TOKEN}` and direct tool exposure; the token stays local.
- Shared mise manifests and nonmutating launchers for Pi, Codex, Claude, OpenCode v2
  and Herdr. These tools, Plannotator, agent-browser and REA follow stable `latest`
  releases with daily mise auto-update checks. Bun and .NET also opt in through a
  selected-key merge of each host's global mise config; other runtimes stay local.
  User-level Herdr takes precedence over Omarchy's package without modifying it.
- Plannotator follows `latest` in `97-plannotator.toml`. Its mise tool-level
  postinstall runs the official installer from that exact release tag, with
  noninteractive mode and provenance verification. The installer owns its skills,
  slash commands and integrations; generated skill copies are excluded from
  chezmoi. Existing installer preferences (extras/model invocation) stay local.
  Before installing, local skills/configs are backed up under
  `~/.local/state/plannotator-install-backups/`. The installer also writes its
  matching `~/.local/bin/plannotator` copy; the hook verifies both binary versions.
  Postinstall strictly installs the matching Pi extension release. Chezmoi
  preserves this host-local pin instead of downgrading it on the next apply.
- Selected Claude and Codex preferences and an entry-scoped Codex Plannotator hook.
  Herdr owns its generated agent scripts/plugins and its entries in shared hook
  configs. These files are not copied between hosts or overwritten by chezmoi.
  Herdr postinstall and explicit bootstrap back up local integration files/configs,
  then reconcile Pi, Codex, Claude and OpenCode integrations using that release.
  Recovery manifests record existing and missing targets under
  `~/.local/state/herdr-integration-backups/`.
- Executor + REA global MCP configuration for Pi, Claude, Codex and OpenCode v2.
  OpenCode's `opencode.json` owns MCP configuration; `opencode.jsonc` has its MCP
  section removed so it cannot reintroduce servers. Both preserve unrelated settings.
  All clients reference the host-local `EXECUTOR_MCP_TOKEN`; no token is synced.
- Clean shared Bash fragment, Git preferences, JJ, Herdr, tmux and Starship.
- Omarchy-only user configuration, custom plugins, terminal preferences and
  selected service definitions. Hardware/layout differences use host templates.
- Vicinae script command `tw <channel>` (Omarchy desktops only): opens a Twitch
  channel in mpv at best quality (up to 1080p60) via yt-dlp. Needs `mpv` and `yt-dlp`.
- Vicinae script commands `kite`, `gon` and `nudge` (Omarchy desktops only): send a free-text
  message to that Grok Bot agent's webhook through `~/.local/bin/bot-hook`. Webhook URL and key
  live per bot in `~/.config/bot-hooks/<bot>.env` (not synced); create them with
  `bot-hook --setup <bot>`. Needs `curl` and `jq`.
- Vicinae file indexing is disabled on Omarchy desktops with the native
  `providers.files.preferences.autoIndexing = false` setting in `~/.config/vicinae/settings.json`.
  The merge preserves each host's themes, extensions and other preferences. Indexing had
  scanned millions of files and written ~10 MB/s. Chezmoi removes the old
  `vicinae.service.d/no-file-indexer.conf` workaround: its `InaccessiblePaths=` directive
  created a user namespace inherited by launched apps, breaking 1Password's browser helper.
  After the first apply, run `systemctl --user daemon-reload` and
  `systemctl --user restart vicinae.service`, then fully quit and reopen Helium (an in-browser
  restart keeps the old namespace). Future applies do not restart running apps automatically.
  Validate the policy with `python3 -B -m unittest discover -s tools -p 'test_vicinae_policy.py' -v`.

Agent `modify_` sources merge selected keys with current settings. They preserve
host-local tokens, project trust, desktop-generated Codex plugins/marketplaces,
and unrelated state. When a merge changes no data, the live file is kept byte for byte
(`.chezmoitemplates/agents/keep-format`), so key order and whitespace never show as drift. Global MCP server maps are replaced with Executor + REA only,
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
the deployment command. It refreshes the shared tools' and Bun/.NET release caches and
upgrades them to latest, ensures the shared mise tools are
installed, reshims, installs current bundled Herdr integrations, and
reconciles the exact versions declared in Pi settings. It also retires the stale desktop-only Pi
extension on `dev-1` into a recovery backup. This is explicit, not an automatic
network/install hook on every chezmoi apply.

All three machines use mise as the active update owner for these tools:

- `~/.config/mise/conf.d/95-coding-agents.toml` declares Pi, Codex and Claude via
  mise's binary backends, and OpenCode **v2** via `npm:@opencode/cli`.
- `90-agent-release-policy.toml` exempts these tools from release-age delays.
- All ten opted-in tools (the seven original tools plus REA, Bun and .NET) use
  `latest`, with `auto_update = "24h"`. Each
  sync/bootstrap also explicitly checks current releases; versions can drift
  between machines until their next check. Plain `dotpush` publishes only source.
  Global/runtime-wide auto-update remains disabled.
- Bootstrap retires the entire `~/.vite-plus/bin` launcher directory into a
  private backup under `~/.local/state/vite-plus-launcher-backups/`. Vite+ runtime
  and agent launchers must not shadow mise. The rest of Vite+ stays untouched.
- Claude/OpenCode background auto-updaters are disabled so mise remains the
  update owner. Explicit manual update commands are not blocked.
- `~/.local/bin/{pi,codex,claude,opencode}` delegates to `mise exec` without
  writing globals, triggering `mise use`, or overriding age policy on launch.

Omarchy still owns shell/PATH activation. Chezmoi merges only Bun and .NET's
`version = "latest"` and `auto_update = "24h"` into `~/.config/mise/config.toml`,
replacing their old exact pins while preserving other tool options and settings.
Unrelated global tools, Node/system runtimes, project overrides and trust paths
remain host-local. Project-specific runtime pins still take precedence. Existing
processes are never restarted and old runtime versions are retained for rollback.
Validate this merge with `python3 -B -m unittest discover -s tools -p 'test_mise_runtime_policy.py' -v`.
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

Upgrade and reconcile all shared tools without touching runtimes with:

```sh
bash ~/.local/share/chezmoi/tools/bootstrap-agents.sh
```

`dotsync` and `dotdeploy` invoke this automatically. Plannotator upgrades after Pi
and the other agents so its official installer sees the refreshed dependencies.

### agent-browser

`~/.config/mise/conf.d/98-agent-browser.toml` declares `npm:agent-browser` at
`latest` on every host, matching dev-1's existing backend. The shared
`~/.local/bin/agent-browser` launcher delegates to this exact mise backend.
Sync/bootstrap runs `tools/bootstrap-agent-browser.sh` to upgrade it and run
`agent-browser install` to provision Chrome for Testing, even when the CLI is
already installed. The tool's `postinstall` also provisions the browser after
direct mise upgrades. After successful provisioning, bootstrap uninstalls legacy
agent-browser packages from `~/.npm-global` and user-owned mise Node global
prefixes, then removes older mise agent-browser versions. Only the current CLI
installation remains; other tools are not pruned. The user-level
`agent-browser-prune.timer` also removes unused browser-tool versions hourly after
future automatic upgrades. Mise retains versions still needed by running processes
or tracked project configurations. Pruning never runs inside an unfinished
postinstall hook. No browser session is started and browser profiles are not removed.

On a Linux host missing browser system libraries, run
`mise exec npm:agent-browser -- agent-browser install --with-deps` separately
and review its privileged package-manager changes. Bootstrap does not use sudo.
Unlike the four coding agents, agent-browser retains mise's default release-age
policy. Avoid `npm install -g agent-browser` outside mise or its own updater.

### Mise automatic updates

Mise **2026.10.4+** supports per-tool `auto_update = true` (default check interval:
24h), or a duration such as `auto_update = "6h"`, in global tool declarations.
**2026.10.7+** also supports `tool_update.global_auto` and background prompt updates.
Shims/`mise exec` check the invoked opted-in tool; an activated shell checks in
the background at prompts. These are activity-driven, not an unconditional timer.
Exact pins and project overrides do not advance. Release-age policy still applies.

Daily checks are enabled individually for Pi, Codex, Claude, OpenCode,
agent-browser, Herdr, Plannotator, REA, Bun and .NET. We do not enable
`tool_update.global_auto`: Node and other unlisted host-owned runtimes remain untouched.
Explicit sync/bootstrap updates still run, regardless of the daily check interval.
Herdr refreshes bundled integrations after an installation; Plannotator runs its
version-matched official installer and installs the matching Pi extension. These
hooks are noninteractive and failures fail the install. The integration hooks,
bootstrap's Pi reconciliation and deployment applies share a host-local file lock
so simultaneous writers cannot restore a stale pin. If manually applying chezmoi
while an update may be running, use
`flock ~/.local/state/agent-integration-update.lock chezmoi apply`.
Check `mise doctor` for background update failures. Existing release-age exemptions remain; agent-browser
keeps the default cooling-off period. Running agents/servers are never restarted.

Updating **mise itself** is separate: `self_update.auto = true` enables periodic
checks (default 7d) in supported standalone installs. Package-managed mise should
be upgraded by its package manager. Omarchy's `/usr/bin/mise` belongs to `mise-bin`
and `mise doctor` reports `self_update_available: no`; do not force self-update
or replace that package-owned binary.

References: [mise automatic tool updates](https://mise.jdx.dev/dev-tools/#automatic-tool-updates),
[mise self-update settings](https://mise.jdx.dev/configuration/settings.html#self_update.auto),
[agent-browser installation](https://agent-browser.dev/installation).

Do not run `herdr update` on this mise-managed installation. Existing Herdr
servers and pane processes are not stopped during upgrades; reconnect clients and
restart servers later when their work can safely be interrupted. Restart agent
processes to load updated integrations and the Plannotator Pi extension.

To repair Plannotator's generated skills/integrations, use
`mise install --force github:backnotprop/plannotator`. To repair Herdr integrations,
run bootstrap. Do not import installer-owned skills with `chezmoi re-add`.

Do not use `mise upgrade opencode`: that registry name is the old v1 backend.
Do not install these agents globally with npm or the native Claude installer.
Other Pi extension packages remain separately pinned. `DEV.md` retains the original
runtime audit; this targeted agent consolidation supersedes its initial deferral.

## Slack and Telegram package migration (Omarchy desktops only)

Chezmoi installs `desktop-package-migrate` on `omarchy` and `omarchy-laptop`,
not `dev-1` or unknown hosts. This explicit migration replaces only installed
legacy variants:

- `slack-desktop-wayland` → `omarchy/slack-desktop`
- `telegram-desktop-bin` → `extra/telegram-desktop`

```sh
desktop-package-migrate           # preview, no privilege prompt or changes
desktop-package-migrate --apply   # quit both apps first; authenticate when prompted
```

The replacements use one dependency-checked pacman transaction; old apps are
never removed ahead of installation. Local Slack/Telegram profiles, credentials
and conversations are neither copied nor removed. Missing apps are not installed.
Repeat runs are no-ops once legacy variants are gone. There is no timer or
privileged hook in `chezmoi apply`, `dotsync` or bootstrap. The helper refuses
running apps and known pending system updates; run the normal full Omarchy
update first when needed. It does not refresh databases or upgrade unrelated
packages (required new dependencies are installed). Authentication uses sudo in
a terminal, or the host's graphical polkit agent otherwise.

Publish with `dotpush`, sync on the laptop, then run the explicit migration on
each desktop. For a targeted rollout without upgrading coding agents, fetch and
fast-forward a **clean** laptop source from `origin/master`, apply only
`~/.local/bin/desktop-package-migrate`, then invoke it there. Never overwrite
unpublished laptop changes. Package updates afterwards belong to the normal
system updater, not this helper; RealVNC is unchanged.

Validation: `python3 -B -m unittest discover -s tools -p 'test_desktop_package_migrate.py' -v`.

## REA: JavaScript and Electron reverse engineering

All three hosts track stable `npm:rea-agents` **latest** through mise's shared
`99-rea.toml`, with daily auto-update checks and explicit sync/bootstrap upgrades.
The initial 6.4.0 rollout pin has been retired. `~/.local/bin/rea` delegates to
mise, and all four agents launch that absolute wrapper as a local
stdio MCP server alongside Executor. No remote analysis service is configured.

Chezmoi owns the MCP registrations. REA owns only its version-matched generated
skills under `~/.agents/skills/reverse-engineer-anything` (Pi, Codex, OpenCode)
and `~/.claude/skills/reverse-engineer-anything` (Claude). Those trees are excluded
from chezmoi. Mise postinstall and explicit bootstrap run
`tools/install-rea-skills.py`, which previews and approves **only** the shared and
Claude skill destinations. It rejects unexpected actions and symlinked skill
paths, serializes writes with the existing integration lock, and backs up changed
skill trees before applying. No-op reconciliation creates no recovery backup.
Backups and existing/missing-path manifests stay local under
`~/.local/state/rea-skill-install-backups/`; managed config backups use the normal
deployment recovery directory. The initial REA-only rollout preserves unrelated
live drift and keeps config recovery manifests under
`~/.local/state/rea-config-rollout-backups/`. No credentials, analysis artifacts or REA cache
are imported into this repository.

```sh
rea --version
rea doctor --skill --json
# Repair generated skills without changing MCP registrations or native providers:
python3 ~/.local/share/chezmoi/tools/install-rea-skills.py "$(mise where npm:rea-agents)"
```

Do not run bare `rea setup`, `rea update`, or an independent global npm install:
setup can replace the managed wrapper registration, while mise owns installation.
REA's client doctor can label a wrapper registration stale because it compares
its path to the npm executable; use a live MCP connection/tool-list check to
verify these deliberately managed registrations. Optional native-provider checks
may fail even while JavaScript/Electron analysis works. Restart agents when idle
to discover the new server and skill; deployment never restarts running sessions.

### First Electron investigation

Hopper, Ghidra, Java, debugging proxies and privileged system packages are **not**
installed by this integration. Start with an app you own or are authorized to
inspect, using its `resources/app.asar` or an extracted application tree:

```sh
rea analyze-javascript-application /absolute/path/to/app.asar --json > evidence.json
```

Keep evidence outside the dotfiles repo. In an agent, ask REA's
`analyze_javascript_application` for a summary, inspect retained module Evidence,
and trace one feature with `trace_application_feature`. Start with main/preload
entry points, BrowserWindow configuration, contextBridge and IPC channels;
static observations alone do not prove runtime reachability or enforcement.
For runtime inspection, explicitly launch an isolated app/profile with a
loopback-only CDP endpoint, then use `list_electron_targets` and
`inspect_electron_page`. Do not expose debugging ports on the LAN/tailnet or
attach to a live authenticated app without reviewing the scope first. Browser
interaction automation remains agent-browser's responsibility. Native `.node`
add-ons may warrant separately installing a native engine later.

Updates run through mise; each installation reconciles only its version-matched
skills via the existing guarded postinstall. Running MCP servers keep their loaded
version until agents are restarted at an idle point. REA retains the default
release-age policy, like agent-browser. To roll back, set an exact version and
remove `auto_update` in `99-rea.toml`, sync, and review the
recovery manifests before restoring old skill trees or removing newly created
ones. An older binary alone does not restore skills or configuration.

Sources: [REA](https://github.com/morluto/rea),
[installation and task readiness](https://github.com/morluto/rea/blob/a56f7bb668ab23fec8d33f7af353ac7ed2fe1895/docs/installation.md).

## T3 Code Nightly (Omarchy desktops only)

`omarchy` and `omarchy-laptop` use upstream **AppImages**, not the lagging
`t3code-nightly-bin` packages. Chezmoi manages the launcher/icon, updater and
user timer, never the downloaded images or T3 runtime data. Everything is
excluded on `dev-1` and unknown hosts; dev-1 retains its independent CLI updater.

- `~/.local/bin/t3code-nightly-update` selects strictly versioned Nightly releases
  from `pingdotgg/t3code`, excluding Stable/Preview/PR builds. It requires the
  exact upstream asset URL, size and GitHub SHA-256 digest, verifies the streamed
  download and publishes it atomically under
  `~/.local/share/t3code-nightly/versions/<version>/`. A lock prevents overlapping
  jobs. Checks/downloads fail closed; existing verified files are never overwritten.
- `current.AppImage` is an atomic symlink. Updating changes **only the next
  managed-launcher launch**, never quits/relaunches T3 or its agents, and never downgrades. If upstream
  withdraws the staged nightly so the newest release is older, plain and `--check`
  runs keep the staged image and succeed; `--release <older>` still fails. Previous
  images are retained; there is no unattended deletion. Check disk periodically
  (about 160 MB per staged release) and review old images before manual cleanup.
- `~/.local/bin/t3code-nightly` launches the image and preserves the package's
  Wayland behavior and optional `~/.config/t3code-nightly-flags.conf` arguments.
  The managed desktop entry starts this absolute launcher through
  `systemd-run --user --collect --quiet`, with the existing custom icon. This
  gives the AppImage a fresh user-service environment: launching directly from
  Vicinae can inherit its filesystem namespace restrictions and fail to mount
  the image through FUSE (`fusermount: mount failed: Operation not permitted`).
  Vicinae's file-indexer restriction remains intact; no sandbox relaxation or
  package launcher is required after migration.
- `t3code-nightly-update.timer` checks daily at **03:00 local time**, with up to
  ten minutes of jitter, and two minutes after the user manager starts (login,
  or boot if linger is enabled). `Persistent=true` catches missed calendar runs;
  it does not wake a sleeping computer. The job works while T3 is closed.
- One update owner: `T3CODE_DISABLE_AUTO_UPDATE=true` is set by the wrapper,
  `environment.d` and UWSM configuration. This also disables T3's native manual
  updater; use the staging command below. Session-wide inheritance matters
  because T3 generates a hidden URL-handler entry that launches the image
  directly. That generated entry is **not** managed or removed by chezmoi.
  **URL-only launch caveat:** T3 pins that handler to the version it last ran
  and can reclaim the MIME default. A URL can therefore start an older image
  instead of the staged one, bypassing wrapper flags. Open T3 from the managed
  application launcher first when activating an update; do not rely on a URL
  alone to activate it. The generated handler is refreshed by that launch.

After applying these targets, provision/activate with:

```sh
t3code-nightly-update                       # download/stage; does not launch T3
t3code-nightly-update --check               # metadata-only check
t3code-nightly-update --status              # installed pointer/version, offline
systemctl --user daemon-reload
systemctl --user enable --now t3code-nightly-update.timer
journalctl --user -u t3code-nightly-update.service -n 30
```

At an idle point, **log out and back in** to activate the UWSM/session environment.
Existing browser/desktop processes do not gain new environment variables from
`daemon-reload`; their direct URL launches can otherwise enable native updates.
The managed wrapper disables native updates immediately, even in an old session.
Verify the fresh session with `printenv T3CODE_DISABLE_AUTO_UPDATE` (`true`) and
`systemctl --user show-environment | grep '^T3CODE_DISABLE_AUTO_UPDATE='`.

Explicit `dotsync`/bootstrap also stages T3 and enables this timer on desktops,
so it updates alongside the mise-managed agents without putting AppImages into
mise or creating a second installer. Plain `chezmoi apply` does not enable it.
The native update channel defaults to Nightly because the selected binary is
Nightly; no runtime settings JSON or credentials are imported into this repo.

For initial migration, snapshot the T3 profile/database and launchers, stage and
verify the image, then close T3 at an idle point before removing its package.
Never remove package files under active agents. Preserve `~/.t3` and
`~/.config/t3code-v2`; the AppImage uses those same directories. Existing threads
must be migrated by T3 itself, not copied between environments. Reopen T3 and
verify its local backend and UI; client/server protocol mismatches can require
updating the other side. URL associations and header artwork remain host-local:

```sh
update-desktop-database ~/.local/share/applications
xdg-mime default t3code-nightly.desktop x-scheme-handler/t3code
xdg-mime default t3code-nightly.desktop x-scheme-handler/t3code-dev
```

Rollback requires the preserved runtime snapshot if a newer release migrated
its database; an older image alone is not a safe database downgrade. Source/live
migration backups live outside this repo under
`~/.local/state/t3code-appimage-migration/`. No automatic backup deletion occurs.
Package removal is explicit; do not remove unrelated packages or dependencies.

Icon provenance: `https://github.com/pingdotgg/t3code`,
`assets/nightly/nightly-universal-1024.png` (MIT project); launcher icon file:
`~/.local/share/icons/t3code-nightly-custom.png`.

## T3 Code thread status in the bar

`ponbac.t3code` is a bar widget on `omarchy` and `omarchy-laptop`: one pill
counting T3 Code threads that need you, are working, or are done, with a hover
card listing them. A click focuses the T3 Code window.

Each machine only knows its own T3 Code server, so every host (including
`dev-1`) can publish its status and each bar merges the others in:

- `~/.local/bin/t3code-status` reads the local server's state DB read-only.
  `--serve` publishes it as JSON on port 37731 of the machine's **Tailscale
  address only**; `--watch --peer <host>` is what the widget runs.
- `~/.config/systemd/user/t3code-status.service` runs `--serve`. Chezmoi installs
  the unit but does not enable it. Once per machine:

  ```sh
  systemctl --user daemon-reload
  systemctl --user enable --now t3code-status.service
  ```

- The widget's `remotes` list in each host's `shell.json` names the other
  machines. An unreachable or sleeping machine simply drops out of the counts.

No ssh, keys or tokens are involved. The tailnet is the access boundary: any
device on it can read thread titles from that port unless a Tailscale ACL
restricts it. Omarchy's firewall must allow the port on `tailscale0` if it
blocks tailnet traffic. The script reads T3 Code's internal projection tables,
so a T3 Code schema change can blank the widget until the queries are updated.

`njpatel.omabot` (third-party) shows the Grok Bot roster on both Omarchy bars.
It is a chezmoi `git-repo` external (`.chezmoiexternal.toml.tmpl`) cloned from the
fork `ponbac/omabot` at `v1.0.1-ponbac.4`: upstream `v1.0.1`, reviewed, plus fixes
for Grok Bot 0.71 (liveness, working state, question cards), 0.75 skipped question
cards and the bar slot width. Working remains conservative: the first bot reply
ends the known-working window; skipped cards no longer count as awaiting or
revive older questions. Chezmoi clones it only when absent and never pulls it,
so changing the URL or tag does not move an existing
checkout; switch that by hand (`git remote set-url`, fetch, checkout the tag).
Keep its `.git` so `omarchy plugin update njpatel.omabot` can review and
fast-forward it from the fork.
It reads Grok Bot's local state under `~/.config/Grok Bot` (no network), so an app
update can blank it until the plugin catches up.

## Grok Bot stable updates (Omarchy desktops only)

Both desktops retain the native **`grok-bot-bin` pacman package**, but no longer
need to wait for AUR version bumps. `grok-bot-update` reads the official stable
Linux manifest at `https://api2.cursor.sh/updates/api/download/stable/linux-x64/sand`,
validates its version/commit/exact official `.deb` URL, and uses `makepkg` as the
normal user. Debian maintainer scripts are never run. The downloaded RPM is not
installed or needed: the feed provides the matching Debian payload directly.

Chezmoi manages `~/.local/bin/grok-bot-update`, the recipe and AUR-derived ISC
helpers under `~/.local/share/grok-bot-packaging/`, and the user service/timer.
They are excluded on `dev-1` and unknown hosts; runtime also permits only the two
x86_64 Omarchy hosts. Packages and receipts stay host-local in
`~/.cache/grok-bot-update/packages/`, never in Git. Requires the existing package,
Arch build tools (`makepkg`, `fakeroot`, `bsdtar`, Python), curl and notify-send.

The recipe retains the fontconfig launcher workaround, `sand` alias, desktop
entry, MIME handlers, AppArmor profile and packed-ASAR StatusNotifier tray with
hide-on-close. It refuses an unexpected upstream main entrypoint instead of
silently generating a broken wrapper. Chromium's sandbox is **not disabled**;
these hosts use unprivileged user namespaces, not a setuid helper. These local
patches are based on the AUR `grok-bot-bin` recipe by falser/rafaeloledo. Future
upstream Electron or state-format changes can still require a packaging/Omabot
review; unchanged entrypoint paths alone are not proof of compatibility.

The timer checks **every eight hours** (00:00, 08:00 and 16:00 local time), with
up to five minutes of jitter. Persistent calendar checks catch missed runs but
do not wake the laptop. There is no additional boot/login check. It stages
packages and notifies once delivery succeeds; it **never installs as root,
quits/restarts the app, or changes profiles**.
Installing remains an explicit authenticated action after quitting via the tray:

```sh
grok-bot-update --check       # metadata-only; no local writes
grok-bot-update --status      # installed and staged versions, offline
grok-bot-update               # download/build/stage; safe while app runs
grok-bot-update --install     # quit app first; sudo in terminal / polkit in GUI
systemctl --user daemon-reload
systemctl --user enable --now grok-bot-update.timer
journalctl --user -u grok-bot-update.service -n 30
```

Normal system/AUR upgrades remain available. Equal/newer installed versions
(including higher Arch pkgrel/epoch) are skipped; installation rechecks after
building. Do not run another package manager concurrently with `--install`,
including during authentication. No passwordless sudo policy is installed.
`dotsync`/bootstrap enables the timer and asynchronously stages Grok; plain
`chezmoi apply` only installs the files. The system-installed desktop launcher
is still the only Grok launch owner; there is no second user-space app copy.

**Trust:** the upstream feed currently supplies no publisher checksum/signature.
Downloads rely on HTTPS from the validated official URL. Local SHA-256 receipts
and makepkg source checks detect subsequent cache/source corruption; they do not
establish independent publisher authentication. Checks/builds fail without
changing the installed app. Previous staged packages are retained, with no
unattended deletion; monitor disk use. A failed notification is retried without
rebuilding. A failed service is visible in `systemctl --user --failed`/the journal.

Before the first 0.75.0 launch, profiles were backed up privately under
`~/.local/state/grok-bot-upgrade-backups/` on each upgraded host. Rollback after
an app migration requires the matching profile snapshot as well as the old
pacman package (the existing AUR cache retains 0.72.1); an older executable alone
is not a safe database downgrade. Never sync Grok profiles, credentials, roster
blobs or Omabot's avatar cache between machines.

Validation: run `python3 -B -m unittest discover -s tools -p 'test_grok_bot_update.py' -v`.
Runtime upgrade checks compare Omabot's aggregate counts/liveness, the reported
app version, the Hyprland app class and tray registration, without exporting bot
names, conversations or tokens. The existing `v1.0.1-ponbac.4` plugin remains
pinned unless runtime evidence requires a fix.

## dev-1 disk cleanup (dev-1 only)

`~/.local/bin/dev1-cleanup` keeps dev-1's disk from filling up. It clears regenerable caches
(bun's install cache is kept, since `node_modules` hardlink into it; only packages nothing links
to any more are removed),
removes finished T3 worktrees, strips build output from idle worktrees, deletes idle
build-output-only directories, review copies (3 days idle, never git checkouts) and old Claude
session directories in `/tmp`, and caps the Docker
build cache at 5 GB. A worktree goes once its threads are settled/archived, or once every thread
has been idle 7 days whatever its state, provided the tree is clean and HEAD is on origin or in a
merged PR. Idle worktrees holding unpushed or uncommitted work are listed under "Needs your
attention" in the report, never removed. Each removal is checked against T3 threads and runs,
open processes and git state, and checked again right before it happens. `--dry-run` is the default; `--help` describes
the rules.

- `dev1-cleanup.timer` runs `--apply --count-settled` nightly at 04:30 (`Persistent=true`).
- `dev1-diskguard.timer` checks hourly. Below 40 GiB free it runs the cleanup early (at most
  every 6 h); below 20 GiB it adds the bounded `--emergency` steps (stop at 50 GiB free).
- Report: `~/.local/state/dev1-cleanup/last-report.md`, log `cleanup.log` next to it. "Freed"
  is the measured change in free space.

Validation: `python3 -B -m unittest discover -s tools -p 'test_dev1_cleanup.py' -v`, then
`dev1-cleanup --dry-run --count-settled` on dev-1 and read the report.

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
source is managed. Unrelated service activation and missing application dependencies
are not silently provisioned. The explicit desktop bootstrap's T3 updater timer
is the documented exception.

See `DEV.md` and `DESKTOP.md` for inventory and preserved host differences. Their
original source-path inventories predate the private top-level directory prefixes.
