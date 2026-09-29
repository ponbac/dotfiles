---
name: commit-and-push
description: Describes the current Jujutsu (`jj`) change or Git worktree branch with a Conventional Commit message, creates a fitting bookmark/branch, pushes it, then finds or creates a draft PR using `gh` for GitHub origins or `az` for Azure DevOps origins. Detects linked Git worktrees and uses `git` rather than `jj` there. Use when the user asks to commit/describe, bookmark/branch, push, or open a PR for the current work.
---

# Commit and Push

Use this skill to prepare the current work for review: describe the current `jj` change (`@`) or commit the current linked Git worktree branch, add a fitting bookmark/branch, push, and ensure a draft PR exists.

## Workflow

1. **Choose VCS mode, then inspect the current change.**
   - Detect a linked Git worktree before choosing `jj`:
     - `git rev-parse --is-inside-work-tree`
     - `git rev-parse --show-toplevel`
     - `git rev-parse --git-dir --git-common-dir`
   - Treat the checkout as **Git worktree mode** when Git says it is inside a work tree and either `git-dir` differs from `git-common-dir` or the checkout root has a `.git` file pointing into a `worktrees/` admin directory.
   - In Git worktree mode, use `git` for all VCS operations. Do not run `jj describe`, `jj bookmark`, or `jj git push`.
   - Otherwise use **JJ mode** when `jj root` succeeds. Stop if neither Git worktree mode nor JJ mode applies.
   - JJ mode inspection: run `jj status`, `jj log -r @ --no-graph`, and inspect `jj diff --stat` / `jj diff`.
   - Git worktree mode inspection: run `git status --short --branch`, inspect `git diff --stat` / `git diff` and `git diff --cached --stat` / `git diff --cached`, and check recent context with `git log --oneline --decorate -n 5`.
   - Identify screenshots/videos intended only as PR review evidence during inspection. They are not source changes: exclude them from the commit and preserve their paths for step 7. In JJ mode, remember that unignored files may already be tracked; place review-only media outside the working copy before describing/pushing, without adding ignore-file noise solely for this workflow.
   - Stop if the repo has conflicts, no meaningful change, or multiple unrelated changes that should be split. Ask the user before proceeding in those cases.

2. **Determine the remote provider.**
   - Get `origin` from `jj git remote list` or `git remote get-url origin`.
   - Determine whether `origin` is a fork of another repository. For GitHub, inspect fork metadata (`gh repo view <owner/repo> --json nameWithOwner,isFork,parent,owner,name,defaultBranchRef`) and optionally compare the origin owner with the authenticated user (`gh api user --jq .login`). For Azure DevOps or other providers, compare the remote URL owner/org/project with the expected user-controlled fork when possible.
   - Do **not** ask merely because `origin` is an upstream/canonical repository or belongs to an org/user other than the authenticated user. If `origin` is not a fork, treat `origin` as the intended push remote and PR repository.
   - If `origin` is a fork, ask before creating the PR so the user can choose whether the draft PR should target the upstream parent or the fork itself. Include the source fork/repo, branch/bookmark, candidate upstream base, and candidate fork base in the question.
   - Use GitHub flow when the origin is GitHub/GitHub Enterprise or `gh repo view` succeeds.
   - Use Azure DevOps flow when the origin contains `dev.azure.com` or `visualstudio.com`.
   - If the provider or CLI auth is unclear, stop and ask. Do not fall back to browser automation unless the user asks.

3. **Describe or commit using Conventional Commits.**
   - Infer a subject from the diff: `type(scope): imperative summary`.
   - Prefer types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
   - Keep the subject concise (aim for <=72 chars), lower-case the type/scope, and use an imperative summary.
   - Add a body only when useful: why, notable implementation details, migration notes, and tests/checks run.
   - JJ mode: apply it with `jj describe -m "$message"` (or `jj describe @ -m "$message"`).
   - Git worktree mode: if there are staged or unstaged changes, stage the intended changes (`git add -A` only when all current changes belong in the commit, including no review-only media) and create a commit with `git commit -m "$subject"` plus additional `-m "$body"` paragraphs as needed. If there are no worktree changes but the branch already has unpushed commits, use the existing commit(s) and do not amend/rewrite history unless the user explicitly asks.

4. **Create or reuse a fitting bookmark/branch.**
   - Derive a short bookmark/branch name from the Conventional Commit subject, e.g. `feat/add-oauth-login`, `fix/handle-empty-cart`, `refactor/simplify-cache-key`.
   - Use lowercase letters, digits, `/`, `-`, and `_`; keep it short and descriptive; avoid spaces and punctuation.
   - JJ mode: check `jj bookmark list` first. If `@` already has a fitting local bookmark, reuse it. If the name exists on another change, choose a clear suffix rather than moving it silently. Create with `jj bookmark create <bookmark> -r @`, or use `jj bookmark set <bookmark> -r @` only when reusing/updating an existing bookmark is clearly intended.
   - Git worktree mode: determine the current branch with `git branch --show-current`. If it is a fitting non-default branch, reuse it. If detached or on the default branch, create a new branch with `git switch -c <branch>`. Do not rename an existing branch or switch away from the worktree branch without explicit approval.

5. **Push the bookmark/branch.**
   - Before pushing, re-check that the selected remote is `origin`. Do not ask merely because `origin` is upstream/canonical; ask before pushing to a remote named `upstream`, a non-`origin` remote, or any remote whose identity is ambiguous.
   - JJ mode: push only the selected bookmark with `jj git push --remote origin --bookmark <bookmark>`. An explicitly selected untracked bookmark is created on the remote and tracked automatically; do not add the unsupported `--allow-new` flag.
   - Git worktree mode: push only the selected branch, normally `git push -u origin <branch>`.
   - If the push requires force/remote overwrite, stop and ask before using any force option.

6. **Find or create a draft PR.**
   - Determine the target base branch from the provider default branch, not by guessing when a CLI can tell you.
   - Use the Conventional Commit subject as the PR title. Use the description body plus a short summary/checks section as the PR body.
   - In the commands below, use the selected JJ bookmark or Git branch as the PR source name.

   **GitHub (`gh`)**
   - Determine the explicit PR target repository:
     - If `origin` is not a fork, use the origin repository and do not ask for confirmation.
     - If `origin` is a fork, ask whether to target the upstream parent repository or the fork repository before creating a PR.
   - Check for an open PR from the source bookmark/branch against the selected target repository:
     - `gh pr list --repo <target-owner/target-repo> --head <source-owner>:<source> --state open --json number,title,isDraft,url --limit 10`
   - If one exists, report it and do not create another.
   - If none exists, create a draft PR using explicit repositories to avoid `gh` fork-target defaults:
     - `base=$(gh repo view <target-owner/target-repo> --json defaultBranchRef --jq '.defaultBranchRef.name')`
     - `gh pr create --repo <target-owner/target-repo> --draft --head <source-owner>:<source> --base "$base" --title "$subject" --body "$body"`

   **Azure DevOps (`az`)**
   - Ensure the Azure DevOps extension and defaults/auth are available (`az repos pr list` should work with `--detect true`, or configured org/project/repository defaults).
   - Determine the repository name when detection is unreliable:
     - In JJ mode, `repo=$(basename "$(jj root)")`; in Git worktree mode, `repo=$(basename "$(git rev-parse --show-toplevel)")`. Use that only if it matches the Azure repo name, or parse the repo name from the remote URL.
     - If the repo name is known, pass `--repository "$repo"` to `az repos show`, `az repos pr list`, and `az repos pr create`. Some Azure DevOps checkouts require it even when org/project defaults are configured.
   - Check for an active PR from the source bookmark/branch:
     - `az repos pr list --repository "$repo" --source-branch <source> --status active --query '[].{id:pullRequestId,title:title,isDraft:isDraft,url:url}' -o json`
   - If one exists, report it and do not create another.
   - If none exists, create a draft PR:
     - `base=$(az repos show --repository "$repo" --query defaultBranch -o tsv | sed 's#^refs/heads/##')`
     - `az repos pr create --repository "$repo" --source-branch <source> --target-branch "$base" --title "$subject" --description "$body" --draft true -o json`
   - The `url` returned by `az repos pr create/show/list` is often an API URL, not the human web URL. For a human Azure DevOps PR link, use the repository web URL plus `/pullrequest/<id>`, e.g. `https://dev.azure.com/<org>/<project>/_git/<repo>/pullrequest/<id>`.
   - If `az` cannot detect org/project/repo from the checkout, ask the user for the missing value rather than guessing.

7. **Attach review media when it adds material value.**
   - After the draft PR exists, consider screenshots or video only when they clarify UI state, visual output, animation, or an interaction that the diff and checks do not communicate well.
   - Consider only media explicitly produced or identified as review evidence for the current task. Do not scan for arbitrary media, attach merely because a file exists, or generate filler evidence.
   - A request to run this skill authorizes publishing relevant review-evidence files already identified during the task. Ask first when relevance, ownership, sensitivity, or intended publication is uncertain. For a public GitHub repository, ask before upload unless the user explicitly requested that those files be attached or published.
   - Read [references/pr-media.md](references/pr-media.md) before publishing. Inspect each file for secrets, customer/personal data, private URLs, browser chrome, notifications, and unrelated content; validate type and size; prefer the smallest non-redundant set.
   - Default to one new PR comment. Do not rewrite the PR description or add media to Git.
   - GitHub: require `gh` v2.99.0 or newer and use `gh pr comment --attach`; never use undocumented upload endpoints.
   - Azure DevOps: use `scripts/attach-azdo.py`, which uploads through the PR Attachments REST API, creates one thread, and attempts rollback if thread publication fails. Embed images and link videos.
   - Capture repository status immediately before publication and compare it afterward. Attachment publication must not change repository state; report any difference rather than cleaning it silently.
   - If no media materially improves review, skip this step without asking and mention that no review media was attached.

8. **Final response.**
   - Report the Conventional Commit description, bookmark/branch name, push result, and PR URL/ID.
   - Report attached media (or that none added value), including any failed Azure rollback cleanup.
   - Mention any checks run or skipped.

## Guardrails

- Never force-push, move an existing bookmark on another change, rename/switch away from a Git worktree branch, push to a non-`origin` or `upstream` remote, create a PR from a local fork without confirming the target repository, or create a non-draft PR without explicit user approval.
- Do not create duplicate PRs for the same source bookmark/branch.
- If the diff is ambiguous, security-sensitive, or contains generated/vendor-only noise, ask before choosing the description/bookmark/branch.
- If the required CLI (`gh` or `az`) is missing or unauthenticated, stop with the exact command/output and ask the user to authenticate or choose another path.
- Never publish media whose relevance, provenance, or sensitivity is uncertain. Do not expose credentials in arguments, logs, comments, filenames, or attachment content.
- Do not claim Azure attachment cleanup succeeded when any rollback deletion failed.
