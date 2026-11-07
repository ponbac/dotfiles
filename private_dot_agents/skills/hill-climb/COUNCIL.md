# Council

Two judges score screenshots. Scores are vibes and drift between runs, so every rule here exists to keep them **blind** and **calibrated**.

## Judges

| Judge | `delegate_task` target |
| --- | --- |
| Sol | `{providerInstanceId:"codex", model:"gpt-6.1-sol", options:{reasoningEffort:"high"}}` |
| Opus | `{providerInstanceId:"claudeAgent", model:"claude-opus-5-5", options:{effort:"high"}}` |

Check the IDs with `orchestrator_capabilities` once per climb. If a judge is unavailable, stop and tell Pontus rather than swapping in another model.

Delegate and wait as in `second-opinion` steps 2 and 3. Use `role: "review"`, `mode: "async"`, the title `Hill climb <slug> r<N>: <judge>` and the clientRequestId `<slug>-hc-r<N>-<judge>`. Every round is a **new** `delegate_task` for every judge. Never send a judge a follow-up in an existing thread.

**Calibration (round 0).** Both judges score the base shots and the references. Their scales differ: in practice, Opus scores well below Sol. So the target is set per judge, from this round.

Run both judges every round. With one judge alone, the other's gap stays hidden until it runs again.

## Shot list

Fix the shot list in step 1 with Pontus. Choose 16–24 key shots: the screens that matter most to him, the states they have (populated, empty, error), light and dark, phone and desktop. A longer **full list** is optional, and it is shot only for calibration and the confirmation round. Shoot every entry with `capture`, in the same order, at the same size, with the same data.

To build `capture`, see the `run` skill for starting the app, and use `agent-browser`, the T3 `preview_*` tools or `rea capture_web_screenshot` to take the shots. Starting the app inside the command means a dev server dying between rounds can't break a capture.

## References

References are fixed images of apps Pontus admires, scored unchanged every round. They give the scores a scale and catch drift. Each one is:

- a real in-app screen from a current version, such as an App Store or vendor capture cropped to the app screen. Not a promo illustration, help-page image or old design;
- full resolution, roughly the size of our shots;
- for a job our app does, such as set logging, a dashboard or a history list.

Log the source and crop of each one in `references/SOURCES.md`. Changing the references needs Pontus's approval and restarts calibration.

## Packet

For each round, build `packets/<round>/` by copying images under neutral names:

- each fixed shot that **changed** since the previous round as two images, the previous round and the current round, labelled `A` and `B` with a fresh coin flip per shot (`S01-A`, `S01-B`). In round 1 the previous round is the base. Comparing with the previous round catches regressions; comparing with the base stops telling you anything after a round or two.
- each **unchanged** shot (pixel-identical to the previous round, checked by comparing the files) as one image (`S02`). A pair of identical images only adds noise.
- each reference under a neutral name such as `R01`.

Keep the key (which label is which) only in `STATE.md`. Calibration packets hold the base shots and the references, with no pairs.

## Judge brief

Send this every round with only the paths filled in, and nothing else:

> You are reviewing the visual design of an app's UI. The images are in `<packet path>`; look only there. Images named `S<nn>-A` and `S<nn>-B` are two versions of the same screen.
> For each such pair, say which of A or B is better designed and why, in one line.
> Score every image, including each `R` image, 1–10 on each category below, with a one-line reason per score. Use exactly these JSON keys: `typography`, `hierarchy`, `spacing_density`, `colour_contrast`, `iconography`, `consistency_polish`, `clarity`, `character` (does it have colour and a personality of its own, rather than generic grey), and `overall`.
> For each `S` screen, give the three changes that would most improve it. For a pair, improve the weaker image.
> Write your answer as JSON to `<score file path>`, exactly in this shape, then reply with only that path:
> `{"pairs":[{"shot":"S01","better":"A","reason":"…"}],"scores":[{"image":"S01-A","typography":{"score":8,"reason":"…"}, …one entry per key…}],"fixes":[{"shot":"S01","changes":["…","…","…"]}]}`
> Change no files other than the score file.

For calibration, which has no pairs, send the same brief without the first sentence about pairs and the pairs line, and with `"pairs":[]` in the shape.

The brief never names the target, the round number, earlier scores, which image is newer, what changed or that this is a climb. Pontus's taste notes guide your changes. They stay out of the brief. If a judge asks a question, answer only about the packet's format.

**Validate** each score file as it arrives:

- it parses;
- every pair has a verdict;
- every image, references included, has all nine keys, spelled exactly as in the brief, each with a whole-number score from 1 to 10.

If a file is missing or incomplete, relaunch that judge once with a fresh `delegate_task` (clientRequestId suffix `-retry`). Never transcribe or repair a judge's answer yourself, and never loosen the validator to accept it. If it fails twice, tell Pontus.

## Scoring

- **Category mean:** for each judge and category, the mean over the current round's images, read off with the key. Keep the minimum as well, to find weak screens, but the target uses means.
- **Reference mean:** the same judge's mean for the references in the same round.
- **Gap:** category mean minus reference mean, per judge and category, in the same round. A judge's mood moves both sides, so the gap is steadier than either mean. The relative target is a gap of at least the margin.
- **Progress:** a judge **backs** a round when it prefers the current image in more than half of the changed pairs. This is the signal the plateau rule uses. A single screen improving barely moves a mean over 20 shots, but it does win its pair.
- **Noise:** for each judge, the median over categories of the round-to-round move in its reference means, averaged over the rounds so far. Use 0.3 until two rounds exist. A mean or gap has moved only when the move is bigger than this.
- **Drift:** a reference mean moving by more than the noise is drift. The relative target is immune to it. In absolute mode, a round whose reference means moved more than 0.5 from calibration doesn't count toward "reached". Report it alongside the round's scores.
- **Round table:** posted after every round, in the step 3 update.

  | Category | Sol: ours (mean / min) | Sol: refs | Opus: ours (mean / min) | Opus: refs |
  |---|---|---|---|---|

  Under the table, list:
  - each judge's picks on the changed pairs, and whether it backs the round;
  - each judge's gap change from the previous round, and the noise;
  - each judge's distance to the target: the largest shortfall and its category;
  - drift.
