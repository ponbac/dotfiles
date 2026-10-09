---
name: babysit
description: Carry a GitHub PR through CI and Codex review, fix relevant feedback, then squash merge and delete its remote branch. Use when asked to babysit a PR or finish it once checks and review pass.
---

# Babysit

Complete the ready-for-review, fix, review, and merge loop. Respect any narrower request, such as monitoring only. Reuse the user's existing authorization without asking again.

1. Inspect the PR, current head, CI, review comments, and unresolved threads. Mark it ready for review when requested. Link it to the current thread when `link_pull_request` is available.
2. Fix CI failures and review findings that identify real bugs, regressions, or worthwhile simplifications. Use judgment: skip irrelevant suggestions, speculative hardening, and defensive code without a realistic failure case. Briefly explain declined findings when useful; address and resolve fixed threads.
3. Run the repository's required checks, commit fixes, and push to the PR branch. Request another Codex review with `@codex review` when meaningful changes need review or the previous review no longer covers the current diff. Avoid duplicating a review already running for that revision. Review requests and replies needed for this workflow are part of the task.
4. Keep watching both CI and review until they finish. In T3 Code, use `watch_pull_request` and end the turn; resume on notifications instead of polling, sleeping, or starting a separate watcher. On each wake, read the actual results and repeat the fix/review loop as needed. Without a native watch tool, use bounded waits and check both CI and review. Pause only for a real blocker requiring user input.
5. Before merging, refresh the PR state: all applicable CI checks must pass, Codex must have completed review of the current diff, relevant findings must be resolved, and the PR must be mergeable. Pending, missing, or stale review is not clearance. Squash merge explicitly with the validated head SHA as a precondition, then verify the merge and delete the remote branch. Leave local branches and worktrees alone. Stop watching with `unwatch_pull_request` when available and report the PR link, merge result, and branch cleanup.
