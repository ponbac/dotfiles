---
name: spinoff
description: Launch work into a new top-level T3 thread with its own worktree and a self-contained brief. Use when the user asks for a new T3 thread, wants something investigated or built in parallel, or wants findings fanned out into several threads.
---

# Spinoff

A **spinoff** is a new T3 thread with its own worktree, model and **brief**. The brief is the only context the new agent gets.

1. **Workspace.** Pick one:
   - **fresh** (independent work): `{type:"worktree", baseRef:"<default branch>", branch:"<prefix>/<slug>", startFromOrigin:true}`.
   - **stacked** ("on top of this PR"): `{type:"worktree", baseRef:"<parent branch>", branch:"<prefix>/<slug>", startFromOrigin:false}`. Uncommitted edits are not copied, so commit the parent first.
   - **existing_worktree**: only to continue work that already has a checkout.

   Use the prefix `feat/`, `fix/`, `perf/`, `research/` or `chore/`.
2. **Model.** The user's choice wins. Otherwise use Opus 5.5 high: `{instanceId:"claudeAgent", model:"claude-opus-5-5", options:{effort:"high"}}`. When the user asks for Sol, use `{instanceId:"codex", model:"gpt-6.1-sol", options:{reasoningEffort:"xhigh"}}`.

   If the user names another machine, launch in that environment's project. Ask if it is ambiguous.
3. **Brief.** Write the message with these parts:
   - **Goal**: one sentence that names the kind of deliverable:
     - **investigate**: a recommendation with evidence; no commits, push or PR unless asked later;
     - **build** or **fix**: a PR.
   - **What is known**: measured facts with dates, numbers, file paths, evidence locations, and PR and issue numbers. Separate what was verified from what is suspected.
   - **Scope**: what is in, what is out, and what sibling threads cover.
   - **Constraints**: product decisions that are not to be reopened. Production, deploys and paid APIs are off-limits unless the user allowed them.
   - **Way of working**: for build and fix work, "Use the `crossbuild` skill, finish: <babysit|push>". Add `gh-stack` when the work is stacked. Spell out any customisation the user asked for.
   - **Report**: what to report when done.

   Done when a fresh agent with none of this conversation could start without asking anything. If the user asked for an issue, create it first and reference it in the brief.
4. **Launch.** Call `t3_thread_launch` with `title`, `workspaceStrategy`, `modelSelection` and `message`. To fan out, make one call per thread and have each brief name the other threads' scopes. Launches have no retry key: after an error or a lost response, check `t3_thread_list` before you launch again.
5. **Report.** List each thread as `[title](t3-thread://v1/<threadId>)` with its branch and model.
