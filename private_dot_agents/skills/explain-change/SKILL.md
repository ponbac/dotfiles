---
name: explain-change
description: Turn the current change, a PR, or a commit into a short motion-graphic explanation of what changed and why.
disable-model-invocation: true
metadata:
  opencode/autoinvoke: "false"
---

# Explain change

**Show the mechanism.** Make a polished technical motion explainer, not a launch video or an animated file-by-file diff. You make the story, visuals, render, and supporting explanation with the tools available on the machine.

Invoke explicitly: `/skill:explain-change` in Pi, `$explain-change` in Codex, or `/explain-change` in Claude Code and OpenCode. Optionally append a PR URL, commit, or revision range. Plain-language direction can narrow the focus or ask for a simpler explanation; there is no options interface.

Assume a returning contributor: the viewer knows the project but wants to understand this change. Start at the changed behavior, explain the relevant mechanism, and end at its consequence. Introduce unfamiliar local concepts only as needed.

Default to landscape, 1920×1080, 30fps, roughly 30–45 seconds. Let the mechanism determine runtime and visual treatment; allow more time when compression would obscure causality. Make the video understandable without audio. Narration or music is optional, not a prerequisite.

Write to `explain-output/` in the current directory, or `explain-output-YYYY-MM-DD-HHmmss/` if it exists; choose another suffix if necessary. Keep scripts, assets, previews, frames, downloads, and temporary checkouts inside its `work/` subfolder. Preserve existing outputs.

## 1. Establish the change

Resolve the repository and exact before/after scope before creating output files. Inspect repository instructions and status. Prefer Jujutsu in a JJ-managed workspace; use Git in a linked Git worktree.

| Input | Scope |
|---|---|
| PR URL | Read the PR description and discussion as context; resolve its base and head, then inspect its actual diff and source. |
| Commit or JJ change | Explain that revision relative to its parent. For a merge with no clear mainline, resolve the intended parent before proceeding. |
| Explicit revision range | Use the requested endpoints; state whether the comparison uses a merge base or a direct endpoint diff. |
| No input | In Git, prefer tracked staged and unstaged edits together against HEAD. Inspect relevant untracked source files, excluding generated output. In JJ, prefer the current nonempty working-copy change against its parent. If these are empty, inspect the current branch/bookmark and recent history to identify the active change. |

For a clean Git branch with a clear PR target or default branch, compare against that target's merge base. For an empty JJ working copy, inspect the nearest nonempty ancestor and active bookmark stack; select the active change only when context supports it. An upstream tracking branch alone is not evidence of the intended PR base. Ask one focused question when multiple plausible scopes remain. If no repository or change can be established, ask what to explain.

Record the selected base, head, and local-edit scope. Read the diff, surrounding implementation on both sides, relevant callers, and existing tests. Trace the changed execution or data flow far enough to explain its consequences. Account for every changed area: central to the story, supporting it, or explicitly outside the chosen focus.

Treat PR prose as intent, implementation as behavior, and executed checks as observations. Distinguish these in your notes. A test's existence is not a passing result. Run relevant safe checks when useful; record what actually ran and its outcome. Use isolated copies under `work/` for before/after execution. Preserve the user's working copy, history, and running services; obtain permission for destructive operations, production access, or missing dependencies that require installation.

Write `explanation.md` with:

- The exact scope and a one-sentence behavioral change.
- Before → limitation or failure → changed mechanism → after.
- Changed-area accounting, including supporting edits and exclusions.
- Evidence for each intended claim: revision and file/symbol or line range, test result, reproduction, or PR context.
- Unresolved questions, assumptions, and check status, including checks not run.

**Complete when:** the before/after mechanism is supported by inspected evidence, every changed area is accounted for, and uncertainties that could change the story are resolved or explicitly bounded. If the central claim cannot be established, report the blocker before starting animation work.

## 2. Storyboard the mechanism

Choose one causal thread. A useful starting shape is **before → failure or limitation → change → after**; for a new feature, follow **entry → new action → result**. Supporting edits earn screen time only when they explain that thread.

Choose the visual treatment that exposes the mechanism:

| Treatment | Use for |
|---|---|
| Before/after replay | Bugs, ordering fixes, and behavioral differences. Replay the same relevant input so the contrast is legible. |
| Animated sequence or state diagram | Concurrency, requests, signals, lifecycle, ownership, or data movement. |
| Real UI walkthrough | User-facing changes. Reuse the project's actual components, styles, assets, and interactions where available. |

Write `storyboard.md`: the explanatory takeaway, visual treatment, and a scene table with duration, settled text, action, and evidence references. Durations must sum to the planned runtime. Each scene should answer a question or advance the causal thread.

### Visual rules

- **Motion means something.** Moving tokens represent requests or data; arrows represent actual relationships; state changes represent actual transitions. For concurrency, preserve established ordering and distinguish simultaneous or unordered events from sequential ones.
- **Keep identity stable.** Actors retain their position, name, and color across before/after scenes. Use text or shape as well as color to distinguish important states.
- **Show the relevant detail.** Use real identifiers and small code excerpts where they help. Diagrams may simplify topology, but must preserve the relationships responsible for the change.
- **Label the evidence level.** Mark schematic examples as illustrative, not captured execution. Numerical timing and performance claims need evidence; use qualitative ordering when timing is unknown.
- **Readable holds.** Count reading time from when a whole line is settled, roughly 0.3 seconds per word. Pace comes from meaningful movement and cuts, with enough hold time to inspect important diagrams.
- **Restrained polish.** Use clear typography, generous spacing, strong contrast, and a small consistent palette. Open with the problem or changed behavior; close with the resulting behavior and any material limitation.
- **Safe to share.** Use sanitized example data and inspect reused UI, logs, URLs, and assets for credentials or private content. Keep the technical explanation accurate after sanitization.

**Complete when:** every factual claim maps to evidence in `explanation.md`, every scene has a causal purpose, illustrative material is identified, and the settled text and diagrams fit their allocated reading time.

## 3. Build and inspect

Inspect available rendering tools and choose the simplest reproducible pipeline. Use existing runtimes, browser automation, SVG/canvas, video tooling, or the project's components as appropriate. A schematic internal flow is appropriate where there is no reusable UI. Keep all generated sources in `work/` and record the render command there.

For browser-rendered video, make each frame a pure function of time: fixed seeds, explicit animation progress, and no dependence on wall-clock timing. Wait for fonts, images, and layout readiness before capture. Lock the viewport and use a consistent frame count and frame rate.

First render a short preview to establish that the pipeline works. Then inspect a settled still from every scene and samples during every transition. Fix overflow, clipped arrows, overlapping labels, poor contrast, unreadable code, and misleading actor movement. Transition busy scenes by taking old content out before bringing new content in, or dip through the background, rather than crossfading dense diagrams.

If adding sound, keep labels sufficient for silent viewing. Align effects with meaningful events, keep music below narration, and check for clipping. Use locally available synthesis or licensed assets; obtain permission before sending private code or text to an external service.

**Complete when:** the preview renders reproducibly, every scene and transition has been visually inspected, and the animation's ordering and state changes agree with the evidence. Record the inspection outcome and any remaining limitation in `explanation.md`.

## 4. Render and deliver

Render `explain.mp4` using broadly compatible MP4 encoding (H.264, yuv420p, AAC if audio is present). Extract the strongest settled explanatory frame as `poster.jpg`. Replace frame 0 with that poster rather than inserting a frame, preserving duration and audio synchronization.

Check the final file's dimensions, frame rate, duration, and audio presence against the plan. Inspect decoded final frames at the beginning, each scene, transitions, and the end; watch the complete video with available playback tools to check pacing and comprehension. If continuous playback is unavailable, inspect sufficiently dense frame samples and report that limitation. Recheck technical claims against `explanation.md`, including caveats visible in the video.

Deliver:

- `explain.mp4` — the motion explainer.
- `poster.jpg` — a settled explanatory frame.
- `explanation.md` — the readable explanation, scope, evidence, and verification record.
- `storyboard.md` — scene timings and evidence mapping.
- `work/` — reproducible sources and intermediates.

**Complete when:** all deliverables exist, the encoded video passes the final visual and technical checks, and the verification record accurately states what was inspected or not verified. If rendering is blocked, preserve the sources and report the blocker rather than claiming a completed video.

Tell the user the video and explanation paths, give one sentence on the mechanism shown, and offer to rework a scene or clarify a part. Keep delivery concise. Creating these files does not authorize uploading them or posting to a PR.
