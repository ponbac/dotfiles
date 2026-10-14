---
name: pr-walkthrough
description: Build a self-contained HTML walkthrough of a GitHub pull request that gets a reviewer from "what is this" to "where to look in the diff" fast, with verified excerpts, diagrams and interactive models.
disable-model-invocation: true
---

# PR walkthrough

Build a **walkthrough**: one HTML page a reviewer reads before opening the diff. It answers four questions in order:

1. What changes in behaviour?
2. Which files to read, in what order, and what to check in each?
3. What is worth questioning?
4. How does it work?

The page succeeds when the reviewer gets the gist in two minutes and then reviews faster. A page that explains the system but leaves the reviewer to find their own way through the diff has missed the point.

Invoke it with a PR number or URL. With neither, use the current branch's PR (`gh pr view`). It works in any repository the `gh` CLI can read.

## 1. Pin the PR

- Run `gh pr view <n> --json number,title,body,url,baseRefName,baseRefOid,headRefOid,commits,files,additions,deletions` and `gh repo view --json nameWithOwner`.
- Fetch the head into a local ref with `git fetch origin pull/<n>/head:pr-<n>`. Also fetch the base oid if it's missing locally.
- Read PR files with `git show pr-<n>:<path>`. Diff with `git diff <baseOid> pr-<n>`.
- The user's checkout stays exactly as you found it, since it may hold their own work. Read only through refs.
- Diff against the PR's own base. For a stacked PR that's the parent branch, not the default branch.
- Read the repository's agent instructions (AGENTS.md, CLAUDE.md) for domain vocabulary.
- Look for screenshots in two places:
  - the PR: its body, comments and review comments;
  - this conversation: images the user attached, and files that earlier work in the thread saved, such as E2E screenshots.

  When any exist, follow [SCREENSHOTS.md](SCREENSHOTS.md).

**Complete when:**
- you have the base oid, the head oid, the file list and every file's diff;
- every screenshot found is downloaded and viewed, or none exist;
- `git status` shows what it showed before you started.

## 2. Build the evidence ledger

Treat the PR body as intent, the code as behaviour, and test runs as observations. PR bodies go stale as commits land, so the code at the head commit wins every disagreement.

Keep a scratch **ledger** of every claim the page will make, each with its source as `path:line` at the head commit. It covers:

- **Classification.** Sort every changed file into one of three:
  - *behaviour*: it changes what the system does;
  - *moved*: extracted or relocated code; verify by comparing the old and new bodies;
  - *skim*: generated clients, lockfiles, i18n catalogues, snapshots, API specs.
- **Contracts.** New or changed endpoints, error codes, permissions, and the order checks run in.
- **Data.** Tables read and written, with their real columns taken from migrations or ORM configuration. Mark JSON columns as such, and note whether the PR adds migrations.
- **Callers.** Grep for every caller of each changed entry point, so you can say who is affected.
- **Tests.**
  - Count tests from the files themselves, not the PR body.
  - Name what each test protects.
  - Use snapshot files as evidence of real output shapes.
- **Risks.** Concurrency, idempotency, permission bypasses, unbounded or repeated reads, in-memory filtering, ordering assumptions, and behaviour that depends on code outside the diff. Phrase each as a question unless you confirmed it.
- **Anchors.**
  - Link format: `https://github.com/<owner>/<repo>/pull/<n>/files#diff-<sha256 hex of the repo-relative path>R<line>`.
  - `R` is the head side and `L` the base side. Take line numbers from `git show pr-<n>:<path>`.

Take line and file counts from `git diff --stat <baseOid> pr-<n>`.

**Complete when:**
- every changed file is classified;
- every risk has a `path:line`;
- every number the page will show has a source.

## 3. Plan the page

Lay out sections in this order. The first three are always present. A deep dive earns its place only when it shows something the diff makes hard to see.

1. **Summary.**
   - A title that states the behaviour change as a plain sentence.
   - A two- or three-sentence before → after lead.
   - A stats row: lines, files, commits, migrations, endpoints, tests.
   - Three lists: behaviour that changes, code that was mostly moved, and files to skim.

   **What it looks like** follows when screenshots exist: a gallery of the real UI. Each shot also appears beside the deep dive it illustrates.
2. **Review path.** Five to twelve numbered stops. Each stop has:
   - a diff link to `file:line`;
   - one or two sentences on what to check there;
   - a risk tag (high, medium or low) for how much a mistake there would cost.

   Order the stops so each builds on the last, usually domain → application → API → client.
3. **Worth questioning.** Unconfirmed risks and open product questions, each with its evidence.
4. **Deep dives,** as the PR warrants:
   - architecture, showing only touched components marked new, changed or context, with hover to trace edges;
   - a step-through request flow with an excerpt per step;
   - the tables involved and the joins that matter, highlighted per join path, with the write side kept separate;
   - rule tables driven by tests (input → result);
   - check order as a scenario picker;
   - a permission matrix;
   - concurrency timelines;
   - tests, and what is explicitly out of scope.
5. **An optional interactive model** of user-facing behaviour, such as a simulator of a new dialog.

Content rules:

- **Excerpts.** Use real code from the head commit, kept short and wrapped, with the lines that matter highlighted and the path as caption.
- **Example data.** Use realistic domain values, and say once (in the footer) that they are illustrative. Say so wherever a payload is trimmed.
- **Interactive models are faithful or labelled.** When a model touches versions, idempotency, permissions or retries, it behaves as the code does. Where it simplifies, its intro says what it leaves out. A wrong simulation teaches a wrong review.
- **Copy.** Quote product strings verbatim, in the product's language. Write the page's own copy in plain, active, sentence-case sentences.

**Complete when:** every ledger entry is placed or deliberately dropped, and the review path covers every *behaviour* file.

## 4. Design and build

Use the `frontend-design` skill for the visual direction, grounding palette, type and layout in the repository's product domain.

Build for desktop, 1280px and wider; mobile polish is out of scope unless asked for. Make it one self-contained HTML file: inline CSS and vanilla JS, with web fonts allowed. Give it a sticky section nav grouped into *Review* and *Deep dives*. Write it to `~/.agent/diagrams/pr-<n>-<slug>.html`.

Build rules learned the hard way:

- Every `id` is unique across the page. A form control sharing an id with a section silently breaks that section's nav link.
- Compute SVG connectors from element rects, and redraw them on resize and after `document.fonts.ready`.
- Lay out diagram nodes in `rem` and check them at the target width, because percentage positions overlap as the width changes.
- Size SVG text for its rendered scale, and give labels that cross lines a background halo.

## 5. Verify

Open the page in a headless browser at about 1500px wide, using the `agent-browser` skill, or `chromium --headless --screenshot` as a fallback.

- Scroll to every section with an instant scroll (`scrollTo({ behavior: "instant" })`), take a screenshot, and look at it.
- Exercise every interaction and screenshot the resulting state.
- Check for zero console errors, no overlapping or clipped text, and no horizontally scrolling excerpts.
- Make sure every nav link lands on its own section.

Then re-walk the ledger against the rendered page. Every number, name, error code, column and check order should match the head commit.

**Complete when:**
- every section and interaction has been seen in a screenshot;
- the ledger re-walk finds no mismatch;
- the headless browser is closed.

## 6. Deliver

Open the page with `xdg-open <file>` (`open` on macOS). Reply with:

- the path;
- a few lines on what the page covers;
- anything you could not verify.

When the user asks to view the page from another device, over Tailscale, or on the tailnet, follow [TAILNET.md](TAILNET.md).
