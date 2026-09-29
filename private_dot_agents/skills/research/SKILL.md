---
name: research
description: Investigate a question against high-trust primary sources and report cited findings, writing them to a Markdown file in the repo only when that is needed. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
---

Spin up a **background agent** to do the research, so you keep working while it reads.

Its job:

1. Investigate the question against **primary sources** — official docs, source code, specs, first-party APIs — not a secondary write-up of them. Follow every claim back to the source that owns it.
2. Report the findings, citing each claim's source.

Decide where the findings go before the agent starts:

- **Answer in chat** when the findings serve the current conversation: a quick fact, an API detail, or a question whose answer you act on right away.
- **Write a Markdown file** when the findings must outlive the session: the user asked for notes or a doc, another agent or ticket will pick them up, or the result is long enough to reference later. Save it where the repo already keeps such notes; match the existing convention, and if there is none, put it somewhere sensible and say where.
- **Ask the user** when it is unclear whether a file is wanted.
