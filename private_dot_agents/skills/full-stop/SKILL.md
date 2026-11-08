---
name: full-stop
description: 'Build with the other model as gatekeeper, and stop before the merge. Use when the user says "full stop" or "full-stop draft", says "crossbuild" (`finish: push` means `draft`), asks for the Sol/Opus "review and second opinion way of working", or a brief requires it.'
argument-hint: "[draft]"
---

# Full stop

You build. The other model checks your work at the plan and the diff. You own the work until the PR is ready for the user to merge. Never merge, enable auto-merge, or push to the default branch. Repeat steps 1–5 for each PR when the work spans several.

1. **Plan.** Read `AGENTS.md` and the docs relevant to the task. Write the plan: approach, files, contracts, tests and open product decisions. Run `second-opinion` on the plan and adjudicate it. This gate always runs. If a real product decision remains, ask. Proceed on everything else.
2. **Implement.** Run `refactor-pass`, then the repository's full check (for example `bun run check:all`). Report the results exactly as they came out.
3. **Prove.** Prove every change with evidence you saw in this session. For a bug, reproduce the failure, fix it, and watch the same reproduction pass. For UI and runtime behaviour, run the app and look at it, and capture screenshots of UI changes. Green mocked tests don't prove the user experience. If you can't prove a change, ask the user.
4. **Diff gate.** Run `review-loop` with a fresh reviewer. Its brief includes the plan-round findings and your responses. Alongside round 1, start a **Jamon pass**: a `delegate_task` with no `target`, so it uses your model, `role: "review"` and the same scope. It applies `jamon-apply-engineering-principles` to the change and reports findings without editing. Wait for both, then adjudicate their findings together in `review-loop`'s step 3.
5. **Publish.** Run `commit-and-push`. Link every PR with `link_pull_request`. With `draft`, go to step 7.
6. **Babysit.** Run `babysit` up to the point of merging. Tell the user when CI and the Codex PR review are clean, and leave the merge to them.
7. **Report.** Give the PR URLs, the checks that ran, your proof, each review round and what it changed, the decisions you made for the user, and any open decisions. This report goes to the user, not into the PR description.

## Asking the user

Ask only when you can't continue alone: a real product decision remains, you can't prove the change, the merge gate can't pass, or the next step deletes data, touches production or goes outside the repo. Use the question tool. If the user is away, also message Gon. Decide everything else yourself and list those decisions in the report.
