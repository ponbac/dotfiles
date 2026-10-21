---
name: pr-walkthrough
description: Build a dark, diagram-led HTML walkthrough of a GitHub pull request that gets a reviewer from "what is this" to "how it works" fast, with real screenshots, highlighted code and verified claims.
disable-model-invocation: true
---

# PR walkthrough

Build a **walkthrough**: one HTML page a reviewer reads before opening the diff. It answers three questions in order:

1. What changes in behaviour, and what does it look like?
2. How does it work?
3. What is worth questioning?

The page succeeds when the reviewer gets the gist in two minutes, mostly from pictures. Show, then tell: every section leads with a diagram, a screenshot or a code excerpt, and prose captions it. The page is ready quickly, so pick the fewest views that make the change clear.

Invoke it with a PR number or URL. With neither, use the current branch's PR (`gh pr view`). It works in any repository the `gh` CLI can read.

## 1. Pin the PR

- Run `gh pr view <n> --json number,title,body,url,baseRefName,baseRefOid,headRefOid,commits,files,additions,deletions` and `gh repo view --json nameWithOwner`.
- Fetch the head into a ref outside the branch namespace, overwriting any earlier one: `git fetch --force origin pull/<n>/head:refs/walkthrough/pr-<n>`. Also fetch the base oid if it's missing locally.
- Read PR files with `git show refs/walkthrough/pr-<n>:<path>`. Diff with `git diff <baseOid> refs/walkthrough/pr-<n>`.
- The user's checkout stays exactly as you found it, since it may hold their own work. Read only through refs.
- Diff against the PR's own base. For a stacked PR that's the parent branch, not the default branch.
- Read the repository's agent instructions (AGENTS.md, CLAUDE.md) for domain vocabulary.
- Look for screenshots and videos in the PR (body, comments, review comments) and in this conversation (attachments, E2E captures saved to disk). When any exist, follow [MEDIA.md](MEDIA.md).

**Complete when:**
- you have the base oid, the head oid, the file list and every file's diff;
- every screenshot and video found is downloaded and viewed, or none exist;
- `git status` shows what it showed before you started.

## 2. Build the evidence ledger

Treat the PR body as intent and the code as behaviour. PR bodies go stale as commits land, so the code at the head commit wins every disagreement.

Keep a scratch **ledger** of every claim the page will make, each with its source as `path:line` at the head commit:

- **Classification.** Sort every changed file into *behaviour* (changes what the system does), *moved* (extracted or relocated; verify by comparing old and new bodies) or *skim* (generated clients, lockfiles, i18n catalogues, snapshots, API specs, docs). Test files are *skim*: the page reports behaviour, not test coverage.
- **Shape.** The components, calls, states and data the change touches, each marked new, changed or context. This is the raw material for the diagrams.
- **Contracts.** New or changed endpoints, error codes, permissions, and the order checks run in.
- **Data.** Tables read and written, with their real columns taken from migrations or ORM configuration.
- **Risks.** Concurrency, idempotency, permission bypasses, unbounded or repeated reads, ordering assumptions, and behaviour that depends on code outside the diff. Phrase each as a question unless you confirmed it.
- **Anchors.** For a line inside a diff hunk, `https://github.com/<owner>/<repo>/pull/<n>/files#diff-<sha256 hex of the repo-relative path>R<line>`, where `R` is the head side and `L` the base side. For a line outside every hunk, or a file the PR doesn't touch, `https://github.com/<owner>/<repo>/blob/<headOid>/<path>#L<line>`. Take line numbers from `git show refs/walkthrough/pr-<n>:<path>`.

Take line and file counts from `git diff --numstat <baseOid> refs/walkthrough/pr-<n>`.

**Complete when:** every changed file is classified, every risk has a `path:line`, and every number the page will show has a source.

## 3. Plan the page

Pick the views before writing any HTML. Sections, in order:

1. **Summary.**
   - A title stating the behaviour change as a plain sentence.
   - A before → after lead of at most three sentences.
   - Stat chips: lines, files, commits; migrations and endpoints only when non-zero.
   - The **change map**: one diagram of the touched components, coloured new, changed and context. Always present. One node may stand for several files.
   - The file list: *behaviour* and *moved* files with a few words each and their diff links; *skim* files collapsed.
2. **What it looks like**, when screenshots or videos exist: large, real UI, per [MEDIA.md](MEDIA.md).
3. **How it works.** Two to five deep dives. Each is one diagram, a one- or two-sentence caption, and the one or two excerpts that prove it.
4. **Worth questioning.** At most six items: a headline, one or two sentences, and evidence links.

Choose each deep dive's diagram by what the reader must see:

| To show | Use |
| --- | --- |
| Request or message flow across components | Mermaid `sequenceDiagram` |
| Decisions and branching | Mermaid `flowchart`, with nodes tagged `new`, `changed` or `risk` |
| A pipeline whose steps each hold several rules or checks | The template's `.stages`: one box per step with its rules as a list, ending in the outcomes |
| Lifecycle or status changes | Mermaid `stateDiagram-v2` |
| Tables and the joins that matter | Mermaid `erDiagram`, new columns called out in the caption |
| Concurrency between two actors | Mermaid `sequenceDiagram` with both actors and the interleaving |
| How code structure changes: call tree, component tree, file layout | A diff excerpt (`data-diff`) of the tree, as in the `show-me` skill |
| How a function changes | A diff excerpt of the function |
| A permission or rule matrix | An HTML table |
| User-facing behaviour with many combinations | An interactive model, only when a diagram can't carry it |

Content rules:

- **Diagrams fit one screen:** about 1100px wide and at most 700px tall. That means at most ten nodes, and left-to-right for chains of three to five steps, top-down for anything longer. Split a diagram that won't fit, and put detail in the caption.
- **A Mermaid node is a name, not a sentence:** a few words on one line, plus a file name at most. When a node needs a list, use `.stages` or put the list in the caption.
- **Excerpts.** Real code from the head commit, verbatim, syntax-highlighted, the path linked to the diff. At most 20 lines: elide the rest with `@@`. Mark only the one to three lines the caption talks about. When the change is the point, show it as a diff against the base.
- **Interactive models are faithful or labelled.** When one touches versions, idempotency, permissions or retries, it behaves as the code does; where it simplifies, its intro says what it leaves out.
- **Example data.** Realistic domain values. When the page invents any, the footer says so once.
- **Copy.** Quote product strings verbatim, in the product's language. The page's own copy is plain, active and sentence case. Captions are at most two sentences; anything longer wants a diagram instead.

**Complete when:** every ledger entry is placed or deliberately dropped, every *behaviour* file is covered by a change-map node or a deep dive, and every deep dive has its diagram chosen.

## 4. Build

Copy [TEMPLATE.html](TEMPLATE.html) to `~/.agent/diagrams/pr-<n>-<slug>.html` and fill it in. The template fixes the look (dark, wide, top nav) and wires up Mermaid diagrams, Shiki highlighting, diff excerpts, media and the lightbox; its header comment shows how to use each. Keep its styles and scripts; add page-specific CSS or JS only for an interactive model.

- Build for desktop, 1280px and wider.
- Every `id` is unique across the page, since a control sharing an id with a section breaks that section's nav link.
- Escape `<`, `>` and `&` inside code excerpts and Mermaid labels; a line break in a Mermaid label is `&lt;br/&gt;`.

## 5. Verify

Open the page in a headless browser at about 1500px wide with the `agent-browser` skill, and run the template's own check:

```sh
agent-browser eval 'walkthroughCheck().then(JSON.stringify)'
```

It waits for Mermaid and Shiki, then reports broken or too-tall diagrams, unhighlighted or too-long excerpts, media that didn't load, duplicate ids, leftover placeholders and horizontal overflow. Fix the page until `ready` is true and every list is empty.

Then screenshot each section with an instant scroll and look at it: nothing overlaps or clips, the marked lines are the ones the caption names, and the console has no errors.
- Re-walk the ledger against the rendered page: every number, name, error code, column and check order matches the head commit.

**Complete when:** `walkthroughCheck()` comes back clean, every section has been seen in a screenshot, the ledger re-walk finds no mismatch, and the headless browser is closed.

## 6. Deliver

Open the page with `xdg-open <file>` (`open` on macOS). Reply with the path, a few lines on what the page covers, and anything you could not verify.

When the user asks to view the page from another device, over Tailscale, or on the tailnet, follow [TAILNET.md](TAILNET.md).
