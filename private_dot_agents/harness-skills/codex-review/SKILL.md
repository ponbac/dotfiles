---
name: codex-review
description: "Second opinion from Codex. Use in Claude Code when the user requests Codex review, or another workflow requires an independent cross-harness review."
---

# Codex second opinion

Ask Codex to independently review your work using **GPT-6.1-Sol with xhigh reasoning**.

Read `~/.agents/lib/second-opinion/WORKFLOW.md` for shared review guidance, expanding `~` to the user's home directory.

Launch Codex noninteractively with `codex exec`, selecting `--model gpt-6.1-sol`, `-c 'model_reasoning_effort="xhigh"'`, and **`--dangerously-bypass-approvals-and-sandbox`**. Use a fresh session in the relevant repository. Choose how to pass the review prompt and collect its response using the CLI's available options.

Prefer the installed CLI binary if PATH resolves to a mise shim or launcher that delays startup. Keep the requested model and reasoning level when adjusting the invocation.
