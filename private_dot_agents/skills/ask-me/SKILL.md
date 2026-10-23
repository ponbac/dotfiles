---
name: ask-me
description: Build a dark HTML decision page that puts open questions to the user, each with options, realistic examples, visuals and a recommended answer, and takes their answers back as JSON.
disable-model-invocation: true
---

# Ask me

Build a **decision page**: one HTML page that puts the open questions of the current work to the user. Each question shows what we already know, a visual where it beats prose, options with realistic examples, and a recommendation with its reason. The user ticks answers or writes their own, adds notes, and pastes the copied JSON back into the thread.

The page succeeds when the user can answer every question from the page alone, without opening the code, the issue or the thread.

## 1. Collect the questions

- Take the questions from the request and the conversation. When the user points at a source (issue, PR, plan, thread, mock), read all of it, including comments and images.
- Facts are your job; decisions are the user's. If reading code, issues, data or logs can answer a question, then it isn't a question for the user. Answer it yourself and put the finding in a question's context.
- A question whose answer depends on another open question waits for the next round.
- Split a question that holds several independent choices into **parts**, each answered separately.
- Give every part a **kind**:
  - `one`: pick one option.
  - `many`: pick any options.
  - `buckets`: sort each item into a named bucket, such as Evaluate / Decide later / Not interested.
  - `rank`: put items in order.
  - For keep-or-change on a screenshot, use `one` with Keep and Change options.
- Give every part a **recommendation**, the reason for it, and what would change it.

Keep a scratch **ledger**: each question with its parts, kinds, options and recommendation, and a source for every factual claim (issue or PR link, `path:line`, query result).

**Complete when:** every part has a kind, options and a recommendation with its reason, and every claim has a source.

## 2. Plan each question

- **Context:** what we already know, in one or two sentences, with evidence links inline.
- **Visual,** where it beats prose. Choose it by what the user must see, using the same views as `show-me`:

  | To show | Use |
  | --- | --- |
  | A decision point or branching | Mermaid `flowchart`, the open branch tagged `risk` |
  | A flow between actors | Mermaid `sequenceDiagram` |
  | A status lifecycle | Mermaid `stateDiagram-v2` |
  | What the code does today, or what an option changes | A code excerpt or diff, at most 20 lines |
  | How the UI looks or would look | A screenshot, or an HTML mock in a `.panel` |
  | Rules across roles or cases | An HTML table |

  Diagrams fit about 1100 × 700 px. A question without a useful visual gets none.
- **Options:** two to five per part. Labels are short, because they go into the JSON.
- **An example per option:** what choosing it looks like, with realistic values. Quote product strings verbatim and in the product's language, as in “Nya AI-svar 13 okt: Vibration”.
- **Copy:** ask in plain product terms. Use active voice and sentence case. Keep reasons to two sentences or fewer.

**Complete when:** every question has context, every option and bucket item has an example, and every question either has a chosen visual or deliberately has none.

## 3. Build

Copy [TEMPLATE.html](TEMPLATE.html) to `~/.agent/diagrams/ask-me-<slug>-r<round>.html` and replace its sample questions. The header comment shows the markup for each part kind and visual. The template supplies everything else: numbering, inputs, Recommended badges, own-answer rows, notes, progress, "Accept remaining recommendations", saving answers in the browser, and the JSON copy. Keep its styles and scripts as they are.

- Set `PAGE`: title, round, date, and `then`, which is what you will do with the answers, such as “Update #793 and #809 with these decisions.” `then` heads the copied JSON, and the user can edit it before copying.
- Each section `id` is a stable slug, unique across the page.
- Mark recommendations with `data-rec`, and select nothing. The badge and the reason show the recommendation, and the accept button applies it.
- Put screenshots in `SHOTS` as WebP data URIs.
- When the page invents any example values, the footer says so once.
- Escape `<`, `>` and `&` inside code excerpts and Mermaid labels.
- Build for desktop, 1280 px and wider.

## 4. Verify

Open the page in a headless browser at about 1500 px wide with the `agent-browser` skill, and run the template's check:

```sh
agent-browser eval 'askMeCheck().then(JSON.stringify)'
```

It reports questions without context, parts without a reason or recommendation, options without an example or label, parts that "Accept remaining recommendations" leaves unanswered, broken or too-tall diagrams, unhighlighted code, broken media, duplicate ids, leftover `{{placeholders}}` and horizontal overflow. Fix the page until `ready` is true and every list is empty.

Then click "Accept remaining recommendations" and read `#json`: every part should carry its recommended answer. Screenshot each question and look at it. Nothing should overlap or clip, the recommended option should be the one the reason describes, and the console should show no errors.

**Complete when:** `askMeCheck()` comes back clean, the accepted JSON holds every recommendation, every question has been seen in a screenshot, and the headless browser is closed.

## 5. Deliver

- Serve the page on the tailnet, following [TAILNET.md](TAILNET.md).
- When a desktop session is present (`$WAYLAND_DISPLAY` or `$DISPLAY` is set), also open the file with `xdg-open` (`open` on macOS).
- Reply with the link, the number of questions, the `then` line, and anything you could not verify. The page carries the questions, so don't restate them.

## 6. When the answers come back

The user pastes JSON shaped like this:

```json
{ "page": "…", "round": 1, "date": "…", "then": "…",
  "answers": [{ "q": "Q1", "id": "slug", "question": "…", "note": "… or null",
    "parts": [{ "id": "…", "label": "…", "answer": … }] }],
  "unanswered": ["Q4"] }
```

What `answer` holds depends on the part's kind:

- `one`: `{option, label, recommended}`, or `{own}` for a written answer.
- `many`: a list of those.
- `buckets`: `{item: {bucket, recommended}}`.
- `rank`: `{order, recommended}`.
- An unanswered part is `null`.

- Do what `then` says, using the answers. Written answers and notes are the user's own words. When one is ambiguous or contradicts another answer, ask about it rather than guess.
- Unanswered questions stay open. List them when you report back.
- When follow-up questions come up, either asked for or raised by the answers, build the next round as `ask-me-<slug>-r<n+1>.html` with `PAGE.round` set to n+1. Add a `#settled` section listing the earlier answers. Point the served `index.html` at the new file so the same link shows it.
