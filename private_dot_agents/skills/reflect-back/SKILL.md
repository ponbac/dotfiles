---
name: reflect-back
description: Manually invoked understanding checkpoint. Restate the user's problem, goals, constraints, and material uncertainties from the conversation without proposing solutions or taking action. Only use when the user explicitly invokes this skill.
disable-model-invocation: true
---

# Reflect back

Be a mirror, not a brainstorming assistant. Help the user check whether you understand the right problem before more work happens.

Manual invocation only:
- Pi: `/skill:reflect-back`
- Claude Code: `/reflect-back`
- Codex: `$reflect-back` (or select it from `/skills`)

Treat any invocation arguments as the focus or additional context. Otherwise use the current conversation, giving the user's latest corrections precedence. Do not apply this workflow automatically to ordinary requests.

## Respond

Restate your understanding in your own words, not as a chronological summary or a repetition of the user's phrasing:

- **The problem:** What the user is trying to solve. Separate the underlying problem from any proposed implementation; do not assume an implementation is itself the goal.
- **Your goals:** The outcomes the user wants and what success would look like.
- **Constraints and priorities:** What matters most, what must be preserved, tradeoffs, and explicit non-goals. Omit anything not supported by the conversation.
- **Uncertainties:** Only assumptions, gaps, or competing interpretations that could materially change your understanding. Clearly label inferences rather than presenting them as things the user said.

Use these headings only where helpful. Usually aim for 150–250 words; use less for simple topics. Do not pad to meet a word count. If there is not enough context, say so and ask for the missing problem or goals instead of inventing them.

End with: **“What have I misunderstood or missed?”** Then stop and wait for the user.

## Guardrails

- Do not invent deeper motivations, unstated requirements, or a more ambitious goal.
- Surface meaningful contradictions neutrally instead of silently resolving them.
- Do not propose solutions, make a plan, research, delegate, run commands, or edit files. Work from the conversation and supplied context only.
- Do not resume implementation merely because you have finished reflecting back.
- If the user corrects you, briefly update your understanding instead of defending the original interpretation. Continue reflecting until they ask to move on.
