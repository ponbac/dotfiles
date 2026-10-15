---
name: crossbuild
description: Build with the other model as gatekeeper (plan cross-check, implement, diff cross-check, then ship). Use when the user asks for the Sol/Opus "review and second opinion way of working", or a brief requires it.
argument-hint: "[finish: push | babysit (default) | merge]"
---

# Crossbuild

You build. The other model checks your work at two gates with `cross-check`. Repeat steps 1–3 for each PR when the work spans several.

1. **Plan.** Read `AGENTS.md` and the docs relevant to the task. Write the plan: approach, files, contracts, tests and open product decisions. Run a `cross-check` at the **plan** gate and adjudicate it. If a real product decision remains, ask the user and give a recommendation. Proceed on everything else.
2. **Implement.** Run `refactor-pass`, then the repository's full check (for example `bun run check:all`). Report the results exactly as they came out. For UI changes, verify them in the running app and capture screenshots.
3. **Gate.** Run a `cross-check` at the **diff** gate with a fresh reviewer. Its brief includes the plan-round findings and your responses. The cross-check decides whether a second round runs.
4. **Finish line.** Use the argument; default to babysit.
   - **push**: `commit-and-push`.
   - **babysit**: `commit-and-push`, then `babysit` up to the point of merging. Tell the user when CI and the Codex PR review are clean. The user merges.
   - **merge**: `commit-and-push`, then `babysit` through to the merge.

   If the branch sits on another PR, publish it with `gh-stack`. Link every PR with `link_pull_request`.
5. **Report.** Give the PR URLs, the checks that ran, each cross-check round and what it changed, and any open decisions.
