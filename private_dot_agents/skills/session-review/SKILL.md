---
name: session-review
description: Find recurring failures in past agent sessions with a sampled first-failure read of T3 threads. Use when the user wants to review past sessions, learn what keeps going wrong, or improve skills, AGENTS.md or model choice from real traces.
---

This is error analysis: read real sessions, name what went wrong, then count. Don't start from a list of expected failures.

It covers T3 threads on the hosts you index. Sessions started outside T3 aren't included.

The steps are read-only. Transcripts hold private data, so keep everything in a scratch directory and never commit it. Change no skill, AGENTS.md or setting: the output is findings for the user.

## Steps

Set `X=~/.agents/skills/session-review/scripts/session_export.py`; the script needs only Python.

1. **Index** each host where the user works. The local host needs no `--host`; for a remote one, pipe the script over ssh:

   ```bash
   python3 -I $X index --since 2026-01-01 > out/index-$(hostname).jsonl
   ssh dev-1 "python3 -I - index --host dev-1 --since 2026-01-01" < $X > out/index-dev-1.jsonl
   ```

2. **Sample.** The defaults take 28 random threads, stratified by host and provider, plus the 12 highest-signal ones. Use a new seed for each run, and record the pool size.

   ```bash
   python3 -I $X sample out/index-*.jsonl --seed 20261101 --exclude "$T3CODE_THREAD_ID" > out/sample.jsonl
   python3 -I $X pack --sample out/sample.jsonl --out out/pack
   ```

   Done when `out/pack/INDEX.tsv` lists every sampled thread and no transcript says `MISSING`.

3. **Read.** Give about 8 transcripts to each native subagent, and forbid further delegation. For each session the reader records:
   - the user's goal;
   - the *first* failure, as a specific observation with quotes, because later failures often follow from it;
   - or "none", when the session went well.

   Readers describe what happened. They use no category names yet. Done when every transcript has an entry.

4. **Group.** Sort the first failures into categories that emerge from the notes, then count them. Note secondary signals separately.

5. **Verify.** Give independent subagents about a third of the sample, including sessions marked "none", with the transcript and the claim to check. Correct the labels and report how many changed. First passes overstate.

6. **Report.** Give the counts, the corrected labels, and for each category the smallest change that would have prevented it. Stop there.

## Reading limits

- Reasoning isn't exported, and the middle of a transcript over 90k characters is cut. Mark a first failure as unverifiable when it may sit in the cut.
- T3 stores full tool outputs. The model may have seen a truncated version, so a large stored output doesn't prove the context was flooded.
- For aggregate numbers, such as polling calls per thread, query the database and report them alongside the sample.
