# Shared development configuration

**Later decision:** the user approved consolidating the four coding agents under
mise on all three hosts. `95-coding-agents.toml` and nonmutating launchers now
manage only those agents, including OpenCode v2. Background self-updaters are
disabled. Old global declarations and duplicate installers were removed after
verification. Non-agent runtimes and trust remain host-owned. The original audit
and initial deferral below are retained as historical context; README describes
the current setup.

Initial source capture and integration notes. The lead subsequently deployed this
configuration to all three hosts. No commits or pushes were made. Top-level
source directories now use the `private_` prefix (see README).
Inspected `omarchy`, Ubuntu `dev-1`, and `omarchy-laptop`; remote inspection used
`ssh -o BatchMode=yes -o ConnectTimeout=10 ponbac@<host>` and read-only commands.

## Managed paths

| Source | Destination / decision |
| --- | --- |
| `dot_config/git/shared.conf` | `~/.config/git/shared.conf`: opt-in, non-auth settings only |
| `dot_config/git/ignore` | `~/.config/git/ignore`: identical desktop ignore rule |
| `dot_config/jj/config.toml.tmpl` | `~/.config/jj/config.toml`: preserve each host's parsed configuration |
| `dot_config/herdr/config.toml.tmpl` | `~/.config/herdr/config.toml`: preserve each host's bindings |
| `dot_config/tmux/tmux.conf` | `~/.config/tmux/tmux.conf`: identical desktop configuration, new on server |
| `dot_config/starship.toml` | `~/.config/starship.toml`: identical desktop configuration, new on server |
| `dot_config/starship-jj/starship-jj.toml` | `~/.config/starship-jj/starship-jj.toml`: identical desktop configuration |
| `dot_config/shell/dev.bash` | `~/.config/shell/dev.bash`: clean interactive-only, source-once fragment |

No raw startup copies were created. The lead added `modify_private_dot_bashrc`
and `modify_private_dot_gitconfig`: they preserve live content and manage only
the shared fragment source line and Git include. Desktop `.bashrc`
files contain a literal database credential (local line 133, laptop line 66).
Those contents were not copied into the repository. Keep all startup files
host-local; do not run `chezmoi add` on them. Mise tool declarations remain
host-local. A later user-approved exception manages only
`~/.config/mise/conf.d/90-agent-release-policy.toml`, exempting the four coding
agents from release-age delays without replacing globals or activating runtimes.
Herdr logs, sessions, plugin state and lockfiles are not configuration to sync.
Editors and plugin installation remain out of scope.

## Deployment integration (implemented by the lead)

The lead owns `.chezmoiignore`, README and deploy scripts. Deny unknown hosts and
allow these dev paths only on the three named hosts; do not inadvertently gate
shared dev configuration as desktop-only. Ignore `DEV.md` as a home target.

After deploying the shared fragment, an idempotent hook may append exactly this
line to the end of the existing `~/.bashrc`, **after** host/package initialization:

```bash
[[ ! -r "$HOME/.config/shell/dev.bash" ]] || source "$HOME/.config/shell/dev.bash"
```

Check for that exact line before appending (`grep -Fqx -- "$line" "$HOME/.bashrc"`).
Do not rewrite, capture, print, or import the startup file. Review equivalent
existing source lines to avoid duplication; preserve file permissions. The
fragment itself returns in noninteractive shells and guards repeated sourcing.
Existing `.bash_profile`/`.profile` already reference `.bashrc`; preserve them.
Do not add mise activation: Omarchy already owns it. Starship initialization is
conditional on the executable, a non-dumb terminal, and `STARSHIP_SHELL != bash`.
Server Starship is absent, so no installation or initialization is attempted.
The retained Starship custom module depends on `starship-jj`; install/verify that
separately before enabling Starship on the server. No helper wrappers are shipped.

Git: keep existing `~/.gitconfig` and `~/.config/git/config` content host-local.
The lead's modify script adds only an include to `~/.gitconfig`.
They contain different host authentication and laptop diff-tool configuration.
The hook can add an include to the existing global file using a selected-key edit:

```bash
include="$HOME/.config/git/shared.conf"
if ! git config --global --get-all include.path | grep -Fqx -- "$include"; then
  git config --global --add include.path "$include"
fi
```

Review equivalent tilde/relative includes first. This changes only `include.path`,
not credential helpers, URLs, tokens, auth stores or host-specific diff tools.
No Git config migration/overwrite is needed. Shared aliases, identity,
`pull.rebase=false` and `init.defaultBranch=master` match both desktops; they are
new defaults on the server. Existing later host settings can override an include.
Git's default XDG ignore path picks up `git/ignore` unless a host has explicitly
set `core.excludesFile`; do not replace such a host override automatically.

## Host differences deliberately retained

- JJ: local and server match. Laptop has neither the `bdiff` alias nor the
  2,621,440-byte (2.5 MiB) snapshot override, and has a different `init` alias.
  `bdiff` is a JJ alias, not an external program dependency. Preserve these
  differences rather than silently standardizing initialization semantics.
- Herdr: local has Annotate bindings and JJ workspace creation on prefix+j/J;
  laptop and server use prefix+a/A for JJ workspaces. Templates retain those
  exact choices. Plugins and sidebar-context remain host-owned prerequisites.
- tmux: desktops are 3.7c; server is 3.6 and has neither inspected XDG config nor
  `~/.tmux.conf`. The server's installed 3.6 manual documents `csi-u`,
  `extended-keys-format`, `terminal-features`, `allow-passthrough`,
  `detach-on-destroy`, and `set-clipboard`. No 3.7-only construct was identified.
  This is a static compatibility review, not a live reload/runtime test.

## Mise decision: defer management, preserve host globals

Primary evidence was read from installed package sources, not assumptions about
an upstream default. On both desktops these files have matching SHA-256 hashes:

- `/usr/share/omarchy/default/bash/init`: calls `mise activate bash`, guarded
  Starship initialization, zoxide, and completions.
- `/usr/share/omarchy/default/bash/env-bootstrap`: appends mise shims and
  `~/.local/bin` so system binaries retain precedence in bootstrap PATH.
- `/usr/bin/omarchy-mise-install`: writes wrappers that run `mise use -g --quiet`
  and then `mise x`; first execution can install/update and mutate globals.

Additional local package evidence:

- `/usr/share/omarchy/default/bash/shell`: `set +h` for mise command resolution.
- `/usr/share/omarchy/default/uwsm/env.d/10-omarchy`: sources env-bootstrap and
  activates mise with `--shims` for the graphical session.
- `/usr/share/omarchy/install/user/mise.sh`: sets `upgrade.auto_prune=false` to
  protect running processes, then creates wrappers (including gh, ghui, hunk,
  playwright). These wrappers must not be copied as portable shared tools.
- `/usr/share/omarchy/install/user/mise-work.sh`: creates `~/Work/.mise.toml`
  with a per-project bin path, trusts that path locally, and provisions Node.

Desktop `/usr/bin/node`, `/usr/bin/dotnet` and `/usr/bin/jj` exist; server versions
come from different locations. Local `pacman -Q` reports `nodejs 26.8.1-2` and
`mise-bin 2026.9.14-1`. Do not replace package/system runtimes or change PATH
precedence merely because another version is installed under mise.

Read-only `mise ls --installed --json` and host global TOML establish:

| Host | Selected installed globals (not necessarily the effective executable in every shell) |
| --- | --- |
| omarchy | bun 1.4.0; dotnet 10.0.203; claude 2.1.284; codex 0.158.0; copilot 1.0.89; gh 2.101.0; npm:@opencode/cli 2.0.19; npm:playwright 1.63.0; pi 0.87.1 |
| dev-1 | bun 1.4.0; dotnet 10.0.300; node 24.13.1 |
| omarchy-laptop | dotnet 10.0.300; node 24.11.1; gh 2.100.0; claude 2.1.284; codex 0.158.0; copilot 1.0.89; opencode 1.18.33; pi 0.87.1 |

Server `~/.config/mise/conf.d/50-ari-developer-tools.toml` additionally selects
aspire 13.5.2, dotnet:Microsoft.SqlPackage 170.4.83, jj 0.44.0,
lazydocker 0.25.2, npm:@openai/codex 0.153.4, npm:agent-browser 0.35.0,
opencode 1.18.23, powershell 7.6.5, and yq 4.53.6. Server globals also enable
Node corepack. Desktop globals retain `upgrade.auto_prune=false`.

Installed does not mean selected: examples include local dotnet 10.0.300 and
10.0.400 despite a 10.0.203 selection; server Node 26.8.1/26.10.0 despite a
24.13.1 selection; laptop bun 1.4.1 with no global bun selection. No versions
were removed, installed, pinned, promoted, upgraded or pruned by this work.

Local trusted config paths include `~/.local/share/t3code/worktrees`,
`~/.t3/worktrees`, and `~/.herdr/workspaces`. Trust decisions, `~/Work/.mise.toml`,
trust state and all host globals remain host-local, never synchronized.

Future integration should separate an explicitly approved tool-only manifest
from host-owned runtime globals. First audit every backend, package ownership,
wrapper, project override and effective PATH on all three hosts. Decide exact
versions per host without silently resolving `latest`; do not feed a shared
manifest to `mise use -g`, auto-install on shell startup, or auto-trust paths.
The existing server conf.d demonstrates a possible split, not permission to
replace it. Deferring mise management is intentional, not an empty manifest.

## Validation

- Rendered both JJ and Herdr templates with chezmoi for all three hostnames.
  All six rendered TOML documents parse and equal the corresponding existing
  host configurations semantically (including embedded JJ shell alias strings).
- Both Starship TOML files parse; shared desktop files were compared identical.
- `bash -n dot_config/shell/dev.bash` passes.
- `git config --file dot_config/git/shared.conf --list` parses successfully.
- Server tmux 3.6 installed-manual compatibility checks passed for the modern
  options above; no running tmux server was started or reconfigured.
- No full apply/diff of host startup or auth files was performed; no sensitive
  startup content or Git auth values were imported. Lead must validate final
  host allowlisting and full deployment after integrating the separate work.
