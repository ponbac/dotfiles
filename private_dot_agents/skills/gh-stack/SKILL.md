---
name: gh-stack
description: Stack changes into dependent GitHub pull requests with `gh stack`, selecting native local tracking for Git and link-only publishing for Jujutsu. Use when the user wants to create, publish, update, inspect, or merge stacked PRs, or mentions `gh stack`, stacked diffs, dependent PRs, or branch chains.
---

# GitHub PR Stacks

Maintain one dependency ladder: trunk, then branches from bottom to top. Each branch maps to one PR whose base is the branch immediately below it.

## 1. Establish scope and mode

1. Inspect before changing history:

   ```bash
   git rev-parse --is-inside-work-tree
   git rev-parse --show-toplevel
   git rev-parse --git-dir
   git rev-parse --git-common-dir
   jj root
   gh auth status
   gh stack --help
   ```

2. Select the history owner:
   - Use **Git mode** for a linked Git worktree.
   - Otherwise use **Jujutsu mode** when `jj root` succeeds, including a colocated JJ/Git repository.
   - Otherwise use **Git mode** when Git reports a work tree.
   - Require `git rev-parse --is-inside-work-tree` to succeed in Jujutsu mode. `gh stack link` needs a colocated Git work tree; pause on a JJ-only checkout.
3. Inspect status, conflicts, diffs, recent history, remotes, and existing PRs. Derive the trunk from GitHub rather than guessing:

   ```bash
   gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'
   ```

4. Distinguish local stack preparation from remote publication. Treat publishing, marking PRs ready, and merging as separate scopes.
5. If `gh stack --help` says the extension is unavailable, report `gh extension install github/gh-stack` and pause. If a command exits with code 9, report that GitHub Stacked PRs is not enabled for the repository.

Complete this step when the history owner, repository root, `origin`, trunk, requested remote scope, and current conflicts are known.

## 2. Design the dependency ladder

Plan branches bottom to top. Put foundations below their consumers, keep each layer independently reviewable, and keep one stack to one coherent effort. For every layer, record its branch/bookmark, description, parent, intended changes, and checks.

Complete this step when every intended change belongs to exactly one layer and every layer names its immediate parent.

## 3. Build the local stack

### Jujutsu mode

Let JJ own all history creation and rewriting. Use `gh stack link` only for GitHub publication; local-tracking commands such as `gh stack init`, `add`, `rebase`, `modify`, and `sync` let Git rewrite history outside JJ.

For a new stack, create and bookmark each change in dependency order:

```bash
jj new <trunk>
jj describe --message "<first change>"
# implement and verify the first layer
jj bookmark create <branch-1> --revision @

jj new
jj describe --message "<second change>"
# implement and verify the second layer
jj bookmark create <branch-2> --revision @

jj new
jj describe --message "<third change>"
# implement and verify the third layer
jj bookmark create <branch-3> --revision @
```

Reuse an existing bookmark only when it already targets the intended change. Update one with `jj bookmark set <branch> -r <revision>` only when moving that bookmark is part of the requested operation.

Inspect every layer before publication:

```bash
jj status
jj bookmark list
jj log -r '<trunk>..<top-bookmark>'
jj diff -r <bookmark> --stat
jj git export
git show-ref --verify refs/heads/<bookmark>
```

Complete the JJ branch when every layer is non-empty, described, tested as appropriate, bookmarked once, and exported as a Git branch in bottom-to-top order.

### Git mode

Let `gh stack` own the local stack metadata and cascading rebases. Supply all positional arguments so commands remain non-interactive.

For a new stack:

```bash
git switch <trunk>
git config rerere.enabled true
git config remote.pushDefault origin
gh stack init --base <trunk> <branch-1>
# implement, stage deliberately, verify, and commit branch 1

gh stack add <branch-2>
# implement, stage deliberately, verify, and commit branch 2

gh stack add <branch-3>
# implement, stage deliberately, verify, and commit branch 3
```

Adopt an existing linear chain with:

```bash
gh stack init --base <trunk> <branch-1> <branch-2> <branch-3>
```

Before adopting, prove each lower tip is an ancestor of the next with `git merge-base --is-ancestor <lower> <upper>`. Inspect the result with `gh stack view --json` and compare each layer using `git log <lower>..<upper>` and `git diff <lower>..<upper>`.

Complete the Git branch when `gh stack view --json` reports the intended order and every adjacent branch pair has the expected ancestry and focused diff.

## 4. Publish and verify

Publish only when remote publication is in scope. Use drafts by default; add `--open` only when the user requested ready-for-review PRs.

In Jujutsu mode, export first and pass every bookmark bottom to top:

```bash
jj git export
gh stack link --base <trunk> --remote origin <branch-1> <branch-2> <branch-3>
jj git import
```

Add `--open` to `gh stack link` for ready-for-review PRs. `link` pushes the branches, creates or reuses their PRs, fixes their base chain, and creates or updates the GitHub Stack without writing local `gh stack` metadata.

In Git mode, submit the locally tracked stack without opening an interactive editor:

```bash
gh stack submit --auto --remote origin
gh stack view --json
```

Add `--open` to `gh stack submit --auto` for ready-for-review PRs.

After either branch, query the PRs and verify the exact chain:

```bash
gh pr list --state open \
  --json number,title,headRefName,baseRefName,isDraft,url
```

The bottom PR must target the trunk; each higher PR must target the preceding branch. Report the PR URLs in bottom-to-top order and their draft/ready state.

Complete this step only when every requested branch has one PR, every PR base matches the dependency ladder, and GitHub reports the PRs as one Stack.

## 5. Maintain or merge

- **JJ:** edit the correct change with `jj edit <bookmark>`, let JJ rebase descendants, rerun the relevant checks, export, and repeat the full `gh stack link` command.
- **Git:** check out a named layer with `gh stack checkout <branch>`, commit the fix there, run `gh stack rebase --upstack --remote origin`, then `gh stack push --remote origin`. After merges, use `gh stack sync --remote origin`; add `--prune` only when branch deletion is requested.
- **Merge:** use `gh stack merge <stack-or-pr> --yes --merge-method <method>` only when the user explicitly asks to merge. A PR argument merges that PR and every unmerged PR below it.

## Invariants

- Run agent-facing commands non-interactively: `view --json`, `submit --auto`, and explicit arguments for `init`, `add`, and `checkout`.
- Keep JJ and Git history ownership separate.
- Pass branch/bookmark arguments to `link` in bottom-to-top order.
- Preserve unexpected remote updates; investigate lease rejection instead of replacing remote history manually.
- Preserve existing bookmarks, branches, PRs, and stack membership unless their modification is part of the requested scope.
