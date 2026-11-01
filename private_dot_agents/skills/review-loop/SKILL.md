---
name: review-loop
description: Review a code change with the other model in rounds until both agree. Use when the user says "review loop", says "cross-check" about a diff, commit or PR, or when another skill needs a diff gate.
---

# Review loop

You own the code and the other model reviews it. Fix what's right, push back on what's wrong, and stop when you agree or the budget ends. `second-opinion` holds the reviewer, the brief, delegation and [REVIEW-CONTRACT.md](../second-opinion/REVIEW-CONTRACT.md).

## Scope

- **Diff:** finished uncommitted or unpushed work, before `commit-and-push`.
- **PR:** a pull request, commit or commit range.
- **Skills:** the reviewer runs named skills (`refactor-pass`, `test-audit`, `thermo-nuclear-code-quality-review`) over the change. State whether it reports or applies; when it applies, it owns the checkout until it finishes.

Every round uses `role: "review"`.

## Budget

- 3 rounds. Round 1 reads the whole change. Later rounds check only changed code and open findings.
- Extend to 5 for security, permissions, auth, data loss or state and concurrency while a blocker or should stays open with evidence, or when the user asks.
- Stop early if a round returns only nits. Declined nits and comment, doc or format-only fixes need no new round.

## Steps

1. **Brief.** Follow `second-opinion` step 1. Record `git diff --shortstat` for the change.
2. **Delegate and wait.** Follow `second-opinion` steps 2 and 3, with a fresh `delegate_task` each round, `title: "Review round N: <topic>"` and `clientRequestId: "<topic-slug>-review-r<N>"`.
3. **Adjudicate.** Give every finding a verdict, as in `second-opinion` step 4. Accept what improves the code this change touches, and list improvements to unrelated code as follow-ups. If review grew the diff, remove what the goal doesn't need. Improving the structure, readability or architecture of code this change touches counts as part of the goal, even if the diff grows. Done when every finding has a verdict and the checks pass again.
4. **Next round.** Run one when budget remains and a blocker or should is open, or behaviour changed after the last review. The brief is the original brief, plus each finding with your verdict and fix. Ask the reviewer to mark each old finding resolved or still open, and to review the code changed since last round.
5. **Stop.** You're agreed when the reviewer approves the current diff, no blocker or should is open, and you have no concern of your own. If a finding stays disputed after two replies, or the budget ends, show both sides in 2–3 lines each and let the user decide. A budget that ran out is not approval.
6. **Report.** Give the rounds, the model, a findings table with verdicts, what changed, the diff size before and after, and any gaps in coverage. End with this line, which `commit-and-push` carries into the PR:

   `Reviewed with review-loop: <N> rounds with <model>. Verdict: <approved, or what stayed open>.`
