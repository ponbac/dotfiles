---
name: claude-review
description: "Second opinion from Claude Code. Use in Codex when the user requests Claude review, or another workflow requires an independent cross-harness review."
---

# Claude second opinion

For Codex to review its work using Claude Code. The runner uses **Opus 5.5 with high effort**, with all permission checks bypassed.

Before dispatch, read and follow `~/.agents/lib/second-opinion/WORKFLOW.md` in full, expanding `~` to the user's home directory when reading. It owns scope, dispatch completion, and adjudication.

```bash
python3 ~/.agents/lib/second-opinion/run.py claude \
  --repo /absolute/path/to/repository \
  --brief /absolute/path/to/review-brief.md
```
