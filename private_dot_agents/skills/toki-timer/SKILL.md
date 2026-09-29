---
name: toki-timer
description: Start or update a Toki timer for the current work, linking to its GitHub issue when available or otherwise its pull request.
disable-model-invocation: true
---

# Toki Timer

Run only when the user manually invokes this skill. Use Executor to start or update the user's Toki timer from the current conversation and repository context. Invocation authorizes the requested timer operation; do not ask for redundant confirmation. Honor any actual tool approval gate.

## Find the work reference

- Identify the current task from the conversation, branch, and relevant diff or commits. Do not infer the task from an old timer note alone.
- Use the repository's actual remote and GitHub CLI or available GitHub tools. Inspect the current PR's linked issues (`closingIssuesReferences`) and description first, along with any issue already identified in the conversation.
- Prefer the specific issue being worked on. If no issue is linked, search repository issues by the task's behavior and terminology, including the repository's language. Read likely matches before choosing; do not substitute an unrelated issue or broad parent issue for the current task.
- If no matching issue exists, use the current work's PR URL. Do not create an issue or PR merely to obtain a timer link. If neither exists, use an accurate task note and report the missing reference.
- Resolve ambiguity from context where possible; ask only if multiple plausible issues or projects remain and choosing would misattribute time.

## Discover Toki through Executor

Read Executor's `skills({ name: "execute" })` documentation before calling its execution tool. In Executor, search the `toki` namespace for the active timer and the needed start/update operations. Describe the selected tools to get their current input schemas and exact paths; do not guess connection names or copy IDs from another session.

Read the active timer before any write. When needed, discover available projects and activities and choose the ones matching the current work. Reuse a matching timer's project/activity; ask if a new timer's project or activity cannot be established from context and available records.

## Start or update

- If a matching timer is running, update its note in place. Preserve its start time, project, and activity unless the user asks to change them.
- If no timer is running and the request is to start or track this work, start one now with the appropriate project, activity, and note. If the user asked only to update a running timer, report that none exists instead of silently starting one.
- If a timer is running for a different project or activity, do not silently relabel its elapsed time. Follow an explicit request to switch timers using the discovered tools; otherwise ask whether to switch. Never create overlapping timers or backdate a start without instruction.
- Use a concise plain-text note containing the issue number, a task summary, and the full issue URL. If using a PR, identify it explicitly as a PR and include its full URL. Example: `#739 - Raise PDF limit to 100 MB (https://github.com/owner/repo/issues/739)`.
- Preserve existing unrelated notes by appending the current work on a new line unless the user requests replacement. Update an existing reference to the same task rather than duplicating it. Replace a task's PR reference with its issue reference when the matching issue becomes known.
- Send only fields needed for the requested change. Do not stop a timer as part of a note-only update.

## Approval and verification

If Executor pauses, retain its execution ID and proposed arguments. Explain the concrete pending change and the tool's approval requirement. Resume that execution after approval; do not issue a duplicate write. An empty requested form is still a tool gate, not permission to bypass it.

Check returned success/error values and re-read the active timer to verify the note and intended running state. If a write times out or its outcome is unclear, read state before retrying so a start operation cannot create duplicate time records.

Report whether the timer was started or updated and link the selected issue or PR. Report blockers honestly. This workflow does not authorize edits to GitHub issues or PRs, publishing comments, or changing historical time entries.
