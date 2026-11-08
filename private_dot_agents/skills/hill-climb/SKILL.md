---
name: hill-climb
description: Climb a score to a target. A blind council of Sol and Opus scores UI screenshots, or a programmatic eval scores behaviour. Stops at a PR.
disable-model-invocation: true
---

# Hill climb

A **hill climb** gives the work a number and keeps changing the work until the number reaches the top Pontus set. The climber (you) knows the target. The judges never do.

Two branches, picked in step 1:

- **Council:** UI quality, scored by judges from screenshots. Read [COUNCIL.md](COUNCIL.md) before step 1 is finished.
- **Eval:** behaviour that a program can score. Prefer it whenever the problem can be turned into checks. Read [EVAL.md](EVAL.md) before step 1 is finished.

## State

Keep all climb state outside the repo, in `~/.local/state/hill-climb/<slug>/`, so judges reading the checkout never see the target:

- `STATE.md`: the hill (step 1), the target definition (step 2), the scoreboard (one row per round), and judge claims that didn't hold up.
- `capture`: the one command that captures a round (council).
- `references/`: the fixed reference images, plus `SOURCES.md` (council).
- `shots/<round>/`, `packets/<round>/`, `scores/<round>/<judge>.json` (council).
- `runs/<round>/`: raw eval output (eval).

## Steps

1. **Define the hill.** Write the following into `STATE.md`:
   - the branch;
   - the artefact: the fixed shot list and the references (COUNCIL.md), or the eval command;
   - the `capture` command (council): it starts the app, renders test data that looks like production, captures every shot and stops the app. Production-like means real images, clips and map tiles, not empty fallbacks. Run it once and look at every shot before the baseline;
   - the **must-keep list**: content, order and behaviour that Pontus cares about and that judges might trade away, such as "recovery card first on Idag" or "set controls above the fold";
   - the round budget, 6 unless Pontus says otherwise;
   - the regression gate: the tests, typecheck and lint commands that must stay green;
   - Pontus's taste notes and priorities, in his words;
   - the **leak list** (council): words and phrases a judge could only know from the repo, taken from the taste notes and the repo's design docs (COUNCIL.md, Validate);
   - where round updates go: this thread, or Gon through Executor.

   Ask for anything missing. Done when every field is filled in and a test capture looks right.
2. **Baseline and target.**
   1. Score the untouched base branch. For the council, run the calibration round in COUNCIL.md. For an eval, run the noise run in EVAL.md.
   2. Show Pontus the result. For the council, that's each judge's category means for the base and for the references.
   3. Pontus picks the target, and you write its exact definition into `STATE.md`. There are two modes:
      - **Relative** (council default): every judge's average gap (COUNCIL.md) for every category is at least a margin. The margin is 0 unless Pontus picks another: beat the references. Reference drift can't move this target, because both sides are scored in the same round.
      - **Absolute:** every judge's 3-round average mean for every category is at least N. Point out how close the references come to N. If the reference apps don't reach it, it's probably out of reach.

      For each proposed target, show the gain each judge needs in its furthest category. If any judge needs more than about 1 point, say it's unlikely within the budget, and offer a smaller margin, more rounds, or a bigger redesign first.

   Done when row 0 is on the scoreboard and the target definition names the mode, the number and what is averaged.
3. **Climb.** Each round:
   1. Make one coherent batch of changes aimed at the judges' or the eval's top complaints. Make it big enough to show above the noise. When the gap is the app's overall look rather than single defects ("generic grey", "no personality"), change it app-wide (colour, type, icons, shared components), not one screen at a time. Follow the repo's agent instructions (AGENTS.md) as for any other change.

      For the council, act only on complaints that survive the **filter**. A complaint survives when:
      - it holds against the pixels, or against the running app for content below the fold. Log claims that don't hold in `STATE.md`;
      - both judges share it, or it is a defect you can point to in the pixels: clipped or overlapping text, misalignment, low contrast. A taste call from one judge doesn't survive, however many screens it repeats on;
      - it is not a **reversal**: a judge asking to undo something it asked for earlier in this climb. Keep the current version and log the reversal. A reversal removes only that judge's vote; the other judge's view still counts on its own;
      - it is not contradicted by the other judge;
      - it is not about test data. When judges keep flagging the test data, check whether it looks like production. If it doesn't, fixing it is part of step 1 (tell Pontus, since it changes the artefact). If it does, log the complaint once as a known artefact and skip it in later rounds.
   2. Run the regression gate.
   3. Capture the round.
   4. For the council, do a **regression review** yourself: compare the previous round against this one, shot by shot, and check every item on the must-keep list. Then look at every key shot, and each change at every viewport in the shot list, for what judges miss: clipped or overflowing text, controls that crowd or cover each other, elements in odd places, and awkward or unclear copy (judges read the UI's language poorly). Fix what you find, recapture, then score.
   5. Score the round and append the row to the scoreboard.
   6. Post the round update in this thread, and also to Gon if that was chosen: the round table from COUNCIL.md (or the eval score and its spread), what changed, and annotated screenshots of the changes, with arrows and a one-line note per change. Post the images at full resolution, with desktop shots at their full width. Annotated images are for Pontus only. Judges get raw shots.

   Keep one round in judging at a time. You may prepare the next batch, but capture it only after the scores are in. Changes made between rounds, Pontus's requests included, join the next round's batch, so they get judged; the previous round's images stay as they were scored. While only judges are running, post one status line and end the turn; their completion wakes the thread. Don't run a climb under `/goal`: its Stop hook keeps restarting the turn while judges run. Work in a worktree on a PR branch. Done for the round when the gate is green, the row is written and the update is posted.
4. **Stop.** Stop on the first of these, and record the reason:
   - **Reached:**
     - Council: the target as defined in step 2 holds on the 3-round averages, then a confirmation round with fresh judges keeps it holding once that round is included in the averages. If there is a full list, the confirmation round also shows no regression on it (COUNCIL.md).
     - Eval: the target holds for two consecutive rounds, then 3 further runs also pass.
   - **Plateau:** any of these:
     - for two consecutive rounds, no judge backed the round (Progress in COUNCIL.md). Weak-signal rounds don't count;
     - for three consecutive rounds, no judge reached a new best distance to the target (by more than its noise), even if the rounds were backed. Use each judge's current noise for every round, earlier ones included;
     - for two rounds, the eval median didn't beat the previous one by more than its noise (EVAL.md).
   - **Exhausted** (council): no complaint survives the filter (step 3.1) for a batch.
   - **Budget:** the round budget is spent.

   On plateau, exhaustion or budget, tell Pontus how far from the target each judge is, its average progress per round over the climb, how many more rounds the target would take at that rate, and what the references score. Say whether the top remaining complaints contradict the other judge or the same judge's earlier requests. If most do, the judges have run out of shared direction and more rounds will flip back and forth. Pontus decides whether to extend, retarget or end the climb.
5. **Report.** First get the whole climb's diff reviewed with `review-loop`, and fix what it finds: the gate and the screenshots miss behaviour bugs, such as a value that no longer shows or a button that acts on the wrong item. Then open a draft PR with `commit-and-push` and include the scoreboard in its body. Give Pontus:
   - the stop reason;
   - the scoreboard;
   - each judge's open complaints;
   - the judge claims that didn't hold up;
   - the rounds and child threads used.

   For the council, also show a before/after board: an HTML page with each fixed shot side by side, base against final, at full resolution, with arrows and a one-line note per change on the final shot. Show it with `html_preview` and `html_render`.

   The climb ends here. A new target, new references or a new category start a new climb, stacked on this PR, when Pontus asks for one.

## Rules

- Pontus owns the target. You raise it, lower it or reinterpret it only when he says so.
- Pontus's must-keep list, taste notes and priorities beat any judge complaint. When a judge asks for the opposite, keep Pontus's version and note it in the update.
- Keep the artefact fixed for the whole climb: the same shot list, references and data, or the same eval cases. Change it only with Pontus's approval, then restart at step 2. The exception is a capture fix that changes only size or scaling, not content. Recapture the previous round's code with the fixed `capture` as the previous images, and say so in the round table.
- Fix the work, not the meter. A change that only moves the score is a regression. For example: text aimed at the judges in the UI, test data changed to please a judge rather than to look like production, an eval case special-cased in code, or changes added to a batch just to clear the weak-signal line.
