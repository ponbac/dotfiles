---
name: claude-review
description: "Second opinion from Claude Code. Use in Codex when the user requests Claude review, or another workflow requires an independent cross-harness review."
---

# Claude second opinion

Ask Claude Code to independently review your work using **Opus 5.5 with high effort**.

Read `~/.agents/lib/second-opinion/WORKFLOW.md` for shared review guidance, expanding `~` to the user's home directory.

Launch Claude noninteractively with `--print`, selecting `--model claude-opus-5-5`, `--effort high`, and **`--dangerously-skip-permissions`**. Use a fresh session in the relevant repository. Choose how to pass the review prompt and collect its response using the CLI's available options.

Prefer the installed CLI binary if PATH resolves to a mise shim or launcher that delays startup. Keep the requested model and effort when adjusting the invocation. If Claude rejects the launch as nested, clear `CLAUDECODE` for the child process only.
