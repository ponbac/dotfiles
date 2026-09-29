---
name: herdr-subagents
description: Delegate work to Pi subagents in Herdr. Use when the user asks to split a task across multiple agents.
disable-model-invocation: true
---

# Herdr subagents

Act as the **foreman**: own the task graph, boundaries, integration, and final answer. Each subagent owns one bounded assignment.

Before controlling Herdr, read and follow the installed [`herdr` skill](../herdr/SKILL.md) completely. Its environment gate, opaque-ID rules, current CLI discovery, commands, safety rules, and status definitions are authoritative. Check `HERDR_ENV=1` before issuing control commands.

## 1. Cut the assignments

Identify the caller from `$HERDR_WORKSPACE_ID`, `$HERDR_TAB_ID`, and `$HERDR_PANE_ID`; do not infer it from the UI-focused pane. Obtain its current state with explicit IDs or `--current`, determine the cwd, and capture the repository's current status as the integration baseline. Before relying on command syntax, inspect the relevant non-mutating command groups such as `herdr agent`, `herdr tab`, and `herdr pane`; the installed binary is authoritative.

Divide the objective into independently verifiable assignments:

- Give every editing assignment exclusive ownership of paths or domains, including generated files and mutable resources its commands may affect.
- Put overlapping or tightly coupled implementation under the foreman; delegate bounded read-only investigations instead.
- Keep cross-cutting decisions and final integration with the foreman.

This step is complete when every requested outcome is assigned exactly once and every assignment has an objective, ownership boundary, supplied evidence, and verification criterion without concurrent write overlap.

## 2. Write self-contained prompts

Create one prompt file per assignment in a temporary run directory. Use this contract:

```markdown
# Objective
<one concrete result>

# Evidence
<relevant symptoms, files, logs, constraints, and decisions already made>

# Ownership
You own: <paths or domain>.
Other agents own: <their boundaries>.
Work in the shared checkout and edit only your owned area. Preserve existing and concurrent changes outside it.

# Working agreement
Follow repository instructions. Leave commits and pushes to the foreman. Complete the assignment directly in this pane.

# Completion
<commands or observable evidence that prove the result>

# Final report
State the result, root cause or reasoning, exact changed files, verification commands and results, and any blocker. Then stop and wait.
```

For a research assignment, replace the editing agreement with a read-only evidence report. This step is complete when each agent can execute without asking for missing scope and its final report can be checked against the assignment.

## 3. Spawn the crew

Create one labelled tab per assignment in the caller's current workspace with `--cwd "$CWD" --no-focus`. Tabs are the intentional default for this skill: they isolate each subagent's context and preserve a readable workspace even though ordinary one-off Herdr delegation defaults to sibling panes. Parse each opaque tab and root-pane ID directly from the create response; never construct an ID from a display number. Choose a unique agent name for each assignment that matches `[a-z][a-z0-9_-]{0,31}`.

When an assignment intentionally uses a separate Jujutsu workspace, place each new checkout under the `nathanflurry.jj-workspace` plugin's root: honor its configured `JJ_WORKSPACE_ROOT`, otherwise use `~/.herdr/workspaces/<repo>/<workspace-slug>`. Create the Herdr tab with that checkout's absolute path as `--cwd`. Do not create a separate jj workspace for the ordinary shared-checkout flow, and do not forget or delete one unless the user requested cleanup.

Record a run manifest containing:

- label
- tab ID
- pane ID
- agent name
- prompt-file path
- ownership boundary

Keep the foreman tab and pane focused. Use explicit returned IDs or unique agent names for every crew operation.

Start Pi through Herdr's agent facade in each available root pane:

```bash
herdr agent start "$AGENT_NAME" --kind pi --pane "$PANE_ID"
```

`agent start` waits until Herdr detects Pi and it is ready for interactive input. Start the whole crew before assigning work, then submit each assignment without waiting so the agents work concurrently:

```bash
herdr agent prompt "$AGENT_NAME" "Read and execute the assignment in $PROMPT_FILE."
```

After each prompt, verify a bounded transition to activity with `herdr agent wait "$AGENT_NAME" --until working --until done --until blocked --timeout 30000`. Background agents normally reach `working` or, for very short tasks, `done`. On timeout, inspect `herdr agent get` and `herdr agent read`; an `idle` agent is complete only when its required final report is present. Inspect and recover any agent that becomes `blocked`, remains `unknown`, or exits. This step is complete when every manifest agent is recognized as Pi and has accepted its assignment.

## 4. Await semantic completion

After every agent has reached `working` or already settled, wait for each background agent to reach a settled lifecycle state:

```bash
herdr agent wait "$AGENT_NAME" --timeout 600000
herdr agent read "$AGENT_NAME" --source recent-unwrapped --lines 120
```

Without `--until`, `agent wait` accepts `idle`, `done`, or `blocked`. Both `done` and `idle` can mean completion: `done` is idle work whose result is unseen, while `idle` means the result is considered seen. Background tabs normally finish as `done`, but a tab viewed by the user or another client may finish as `idle`. A timeout is a checkpoint: inspect `herdr agent get` and `herdr agent read`, then branch on current status:

- `working` — continue waiting.
- `blocked` — inspect the question or approval UI with `agent get` and `agent read`, then supply only the required decision with `agent send-keys`. Do not use `agent prompt` while the agent is blocked; Herdr rejects it with `agent_blocked`. Verify activity resumes, then await completion again.
- `done` or `idle` — accept completion only when the required final report is present; otherwise request it with `agent prompt` and await the next settled state.
- `unknown` or exited — inspect output and either recover the session or take the assignment back into the foreman scope.

Inspect current state and output before waiting for a future transition. Use agent reads while an agent is working only for checkpoints or blockers. In a shared checkout, keep foreman activity observational until editing agents finish.

This step is complete when every manifest entry has a verified final report from a `done` or `idle` agent, or has an explicitly evidenced failure owned by the foreman.

## 5. Integrate the work

Read every final report and inspect the repository from the captured baseline. Map every changed path to one assignment, inspect the actual diff, and independently run the integration checks needed for the user's objective.

Send a focused correction with `herdr agent prompt "$AGENT_NAME" "<correction>" --wait --timeout 120000` when a criterion is unmet, then inspect the settled result again. Resolve cross-agent conflicts under the foreman rather than asking agents to edit each other's areas.

This step is complete when every assignment criterion has concrete evidence, every changed path has one owner, concurrent changes are compatible, and overall verification passes or every remaining blocker is evidenced.

## 6. Report and preserve

Report each agent's outcome and the integrated result, including changed files, verification, and blockers. Preserve the labelled tabs for inspection; close only tabs created by this run, and only when the user requested cleanup. Never stop the Herdr server or close unrelated panes, tabs, workspaces, or sessions.

This step, and the skill, is complete when the final response accounts for every manifest entry and the overall objective, and the tab lifecycle matches the user's request.
