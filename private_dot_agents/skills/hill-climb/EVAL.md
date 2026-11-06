# Eval

A program scores the work. This branch is stronger than the council whenever the failure can be checked by code.

## Build the eval

Skip this when an eval already exists.

1. **Collect.** Gather real failures, either from past T3 threads with `session-review` or from the logs and issues Pontus points to. Done when every failure is listed with its source.
2. **Group.** Sort the failures into named categories. Before writing any code, show Pontus the categories and ask about anything unclear.
3. **Encode.** Turn each failure into a case with a programmatic pass/fail check. The eval prints a total, such as `passed/total`. Put it on its own PR branch so the climb can stack on it.

Done when the eval runs with one command and every collected failure is a case.

## Noise

Before climbing, run the eval 3 times on the base branch and record the spread in `STATE.md`. Score each round as the median of 3 runs. A change counts as better only when it beats the previous median by more than the spread.

## Order

1. **Climb** to the target. A perfect score is the default.
2. **Lock.** Commit, then check the score holds across every model Pontus names.
3. **Squeeze**, but only if Pontus names a secondary metric (context size, latency, payload). Shrink that metric while the score stays at the target. Any round below the target is reverted.
