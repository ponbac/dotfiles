---
name: grilling
description: Grill the user relentlessly about a plan, decision, or idea until every branch is settled, keeping the project's CONTEXT.md glossary current when one exists or the session pins down domain terms.
disable-model-invocation: true
---

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), spawn a background subagent with a self-contained prompt to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the subagent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.

## Domain language (optional CONTEXT.md)

If the repo has a `CONTEXT.md` (or a `CONTEXT-MAP.md` pointing to several), read it before the first round and hold the user to it:

- When the user uses a term that conflicts with the glossary, call it out in the next round: "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"
- When a term is vague or overloaded, make choosing the canonical term a frontier question.
- When the user states how something works, check the code; surface contradictions as questions.

Write to `CONTEXT.md` only when a round actually settles a project-specific term. Update it right then instead of batching, using [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md). If no `CONTEXT.md` exists, create one only once a settled term is worth keeping and the user agrees. It is a glossary and nothing else: no implementation details, decisions, or spec content.
