---
name: codex-review
description: "Second opinion from Codex. Use in Claude Code when the user requests Codex review, or another workflow requires an independent cross-harness review."
---

# Codex second opinion

For Claude Code to review its work using Codex. The runner uses **GPT-6.1-Sol with xhigh reasoning**, with approvals and sandbox bypassed.

Before dispatch, read and follow `~/.agents/lib/second-opinion/WORKFLOW.md` in full, expanding `~` to the user's home directory when reading. It owns scope, dispatch completion, and adjudication.

```bash
python3 ~/.agents/lib/second-opinion/run.py codex \
  --repo /absolute/path/to/repository \
  --brief /absolute/path/to/review-brief.md
```
