---
name: cross-check
description: Second opinion from the other model through T3 `delegate_task` (Opus asks GPT-6.1-Sol, Codex asks Opus). Use when the user asks for a second opinion or a Sol/Opus subagent review of a plan, diff, commit or PR, or when another skill needs a cross-model gate.
---

# Cross-check

A **cross-check** hands one artifact to the other model and ends with an adjudicated verdict on every finding. Each **round** is a fresh `delegate_task` call.

## The other model

| You are | Reviewer `target` |
| --- | --- |
| Claude | `{providerInstanceId:"codex", model:"gpt-6.1-sol", options:{reasoningEffort:"xhigh"}}` |
| Codex | `{providerInstanceId:"claudeAgent", model:"claude-opus-5-5", options:{effort:"high"}}` |

A model or effort the user names wins ("sol 6.1 high"). Check unfamiliar IDs with `orchestrator_capabilities`.

## Gates

- **plan**: an idea, design or implementation plan, before code. Ask the reviewer to challenge correctness, edge cases, races, over- or under-engineering, contract design and test value, and to name product decisions that should be asked rather than guessed. `role: "design"`.
- **diff**: finished uncommitted or unpushed work, before `commit-and-push`. `role: "review"`.
- **pr**: a pull request, commit or commit range. `role: "review"`.
- **skills**: the reviewer runs named skills (`refactor-pass`, `test-audit`, `thermo-nuclear-code-quality-review`) over the change. State whether it reports or applies; when it applies, it owns the checkout until it finishes.

## Steps

1. **Brief.** Write a self-contained prompt with:
   - the user's request in their words, and product decisions that are not to be reopened;
   - exact scope: worktree path, branch and base, the changed files including untracked ones, or the commit SHA or PR number;
   - for the plan gate, the plan itself;
   - verification already run, with results;
   - the full text of [REVIEW-CONTRACT.md](REVIEW-CONTRACT.md), pasted in;
   - repository guardrails: name the commands that write into the checkout (builds, codegen, `check` scripts) and tell the reviewer to run those in a temp copy. Production, shared services and paid APIs are off-limits unless the user allowed them.

   Give context, not a defence of your work. Done when a reviewer with none of this conversation could start without asking anything.
2. **Delegate.** Call `delegate_task` with the target above, `mode: "async"`, the gate's `role`, `title: "<Gate> review[ round N]: <topic>"` and `clientRequestId: "<topic-slug>-<gate>-r<N>"`. If a call is interrupted, retry with the same ID. Use the shared checkout for uncommitted work, because worktree isolation copies commits only. Use `isolation: "worktree"` only when the reviewer has to run mutating checks against committed work.
3. **Wait.** Stop editing the shared checkout. The completion notification wakes this thread, so end the turn or do work that doesn't touch the checkout. Read the result from `task_status`. To open the child transcript, pass `maxCharsPerItem` to `t3_thread_read` because full transcripts overflow. A failed, timed-out or partial review is not a clean result: relaunch it.
4. **Adjudicate.** Give every finding one verdict:
   - **accept**: fix it;
   - **reject**: give the evidence;
   - **unresolved**: ask the user and include a recommendation.

   Reject speculative hardening and defensive code that has no realistic failure case. Note any accepted fix that changes behaviour. Done when every finding has a verdict.
5. **Round 2.** Run it when an accepted fix was non-trivial or a blocker turned up. Use a new `delegate_task` with clientRequestId `…-r2`. The brief is the original brief, plus the round-1 findings, plus your verdict and fix for each. Ask the reviewer to read the current diff afresh and say whether each fix holds. Round 2 is the final round. Run a third only for an unresolved blocker.
6. **Report.** Give the gate, the model, the rounds, a findings table with verdicts, what changed, any behaviour changes and any gaps in coverage.

The reviewer returns findings only. It never starts its own cross-check.
