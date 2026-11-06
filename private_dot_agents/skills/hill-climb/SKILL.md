---
name: hill-climb
description: Climb a score to a target. A blind council of Opus, Sol and Grok scores UI screenshots, or a programmatic eval scores behaviour. Stops at a PR.
disable-model-invocation: true
---

# Hill climb

A **hill climb** gives the work a number and keeps changing the work until the number reaches the top Pontus set. The climber (you) knows the target. The judges never do.

Two branches, picked in step 1:

- **Council:** UI quality, scored by three judges from screenshots. Read [COUNCIL.md](COUNCIL.md) before step 2.
- **Eval:** behaviour that a program can score. Prefer it whenever the problem can be turned into checks. Read [EVAL.md](EVAL.md) before step 2.

## State

Keep all climb state outside the repo, in `~/.local/state/hill-climb/<slug>/`, so judges reading the checkout never see the target:

- `STATE.md`: the hill (step 1), plus the scoreboard, one row per round.
- `shots/<round>/`: the raw screenshots (council).
- `packets/<round>/`: what the judges get (council).
- `runs/<round>/`: raw eval output (eval).

## Steps

1. **Define the hill.** Write the following into `STATE.md`:
   - the branch;
   - the artefact: the fixed shot list, or the eval command;
   - the target, which Pontus sets;
   - the round budget, 6 unless Pontus says otherwise;
   - the regression gate: the tests, typecheck and lint commands that must stay green;
   - Pontus's taste notes in his words, such as "keep colour".

   Ask for anything missing. Done when every field is filled in.
2. **Baseline.** Score the untouched base branch (council round 0, or the eval noise run). Done when row 0 is on the scoreboard.
3. **Climb.** Each round:
   1. Make one coherent batch of changes aimed at the judges' or the eval's top complaints.
   2. Run the regression gate.
   3. Score the round.
   4. Append the row and the top complaints to the scoreboard.

   Work in a worktree on a PR branch. Done for the round when the gate is green and the row is written.
4. **Stop.** Stop on the first of these, and record the reason:
   - **Reached:** every judge scores every category (or the eval scores) at or above the target in two consecutive rounds, then a confirmation round also passes. A council confirmation uses fresh judges. An eval confirmation is 3 further runs.
   - **Plateau:** the median did not improve for two rounds.
   - **Budget:** the round budget is spent.
   - **Drift:** for the council, the control screenshots moved past the threshold in COUNCIL.md for two rounds running.
5. **Report.** Open a draft PR with `commit-and-push` and include the scoreboard in its body. Give Pontus:
   - the stop reason;
   - the scoreboard;
   - each judge's open complaints;
   - the rounds and child threads used.

   For the council, also show a before/after board: an HTML page with each fixed shot side by side, base against final, shown with `html_preview` and `html_render`.

   The climb ends here. A higher target, more competitor references or a new category start a new climb, stacked on this PR, when Pontus asks for one.

## Rules

- Pontus owns the target. You raise it, lower it or reinterpret it only when he says so.
- Keep the artefact fixed for the whole climb: the same shot list, or the same eval cases. Change it only with Pontus's approval, then restart at step 2.
- Fix the work, not the meter. A change that only moves the score is a regression. For example: text aimed at the judges in the UI, or an eval case special-cased in code.
