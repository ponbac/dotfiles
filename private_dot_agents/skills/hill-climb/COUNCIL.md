# Council

Three judges score screenshots. Scores are vibes and drift between runs, so every rule here exists to keep them **blind** and **calibrated**.

## Judges

| Judge | `delegate_task` target |
| --- | --- |
| Opus | `{providerInstanceId:"claudeAgent", model:"claude-opus-5-5", options:{effort:"high"}}` |
| Sol | `{providerInstanceId:"codex", model:"gpt-6.1-sol", options:{reasoningEffort:"high"}}` |
| Grok | `{providerInstanceId:"cursor", model:"grok-4.7", options:{reasoning_effort:"high", fastMode:false}}` |

Check the IDs with `orchestrator_capabilities` once per climb. If a judge is unavailable, stop and tell Pontus rather than swapping in another model.

Delegate and wait as in `second-opinion` steps 2 and 3. Use `role: "review"`, `mode: "async"`, the title `Hill climb <slug> r<N>: <judge>` and the clientRequestId `<slug>-hc-r<N>-<judge>`. Every round is a **new** `delegate_task` for every judge. Never send a judge a follow-up in an existing thread.

**Staging.** Run Sol alone until Sol meets the target. From then on, run all three every round. Staging rounds count toward the budget.

## Shot list

Fix the shot list in step 1. It covers every view the climb touches, in light and dark mode, at desktop and narrow width, with each state the views have (empty, populated, error). Shoot every entry every round, in the same order, at the same size, with the same data.

To capture, run the app (`run` skill), then use `agent-browser`, the T3 `preview_*` tools or `rea capture_web_screenshot`.

**Controls.** Pontus may provide reference screenshots, such as competitor apps or a design he likes. They are fixed files, and every round re-scores them unchanged. A control whose score moves more than 0.5 from its round-1 score marks the round **noisy**. On a noisy round, report the climb's scores relative to the controls and do not count the round toward "reached".

## Packet

For each round, build `packets/<round>/` by copying images under neutral names:

- each fixed shot as two images, the base branch and the current branch, labelled `A` and `B` with a fresh coin flip per shot;
- each control under a neutral name such as `R1`.

Keep the key (which label is which) only in `STATE.md`.

## Judge brief

Send this every round with only the paths filled in, and nothing else:

> You are reviewing the visual design of a desktop app's UI. The images are in `<packet path>`; look only there.
> For each shot pair, say which of A or B is better designed and why, in one line.
> Then score every image 1–10 on each category below, with a one-line reason per score: typography, hierarchy, spacing & density, colour & contrast, iconography, consistency & polish, clarity, character (does it have colour and a personality of its own, rather than generic grey), and overall.
> Finish with the three changes that would most improve the weaker image of each pair.
> This is read-only: change no files.

The brief never names the target, the round number, earlier scores, which image is new, what changed or that this is a climb. Pontus's taste notes guide your changes. They stay out of the brief.

## Scoring

- A judge's score for the climb is its score for the current-branch images in each category, read off with the key.
- A row on the scoreboard holds:
  - each judge's per-category scores;
  - each judge's pairwise wins for the current branch;
  - the control scores;
  - a noisy flag.
- "Reached" means every judge scores every category at or above the target, and no round counted toward it was noisy.
