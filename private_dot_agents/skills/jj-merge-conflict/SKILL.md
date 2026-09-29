---
name: jj-merge-conflict
description: Resolve Jujutsu (`jj`) merge conflicts by anchoring on the user's current bookmark/branch or working-copy stack, inspecting only relevant conflicted changes, and fixing them bottom-up. Use this when the user wants help cleaning up conflicts in the JJ work they are actively doing.
---

# JJ Merge Conflict

Use this skill for JJ conflict cleanup where resolving a lower conflicted change may automatically clear conflicts higher in the active stack.

The default rule is locality: resolve conflicts related to the user's current working copy, bookmark, branch, or explicitly named stack. Do not sweep every conflicted change in the repository just because `jj log -r 'conflicts()'` shows older unrelated conflicts.

## Workflow

1. Confirm you are in a JJ repo.
   - Run `jj root` or another harmless JJ command first.
   - If the directory is not a JJ repo, stop and tell the user.

2. Anchor the scope before inspecting conflicts.
   - First identify the user's active work:
     - Run `jj status` to see the working-copy commit and current changes.
     - Run `jj log -r '@ | ancestors(@, 50)'` to see the nearby working-copy stack.
     - Run `jj bookmark list` or `jj branch list` when the user mentions a bookmark, branch, or named stack. Some JJ versions use `bookmark`; older setups may still expose `branch`.
   - If the user named a bookmark, branch, change ID, description, or path, use that as the scope anchor.
   - If the user did not name a scope, default to conflicts reachable from the working copy stack, not all repository conflicts.
   - If the current working copy is not on or above the work the user means, ask a short clarifying question before changing anything.

3. Inspect only relevant conflict state.
   - Start broad enough to understand the repository state with `jj log -r 'conflicts()'`, but treat it as an inventory, not a worklist.
   - Then narrow to the anchored scope. Useful revsets include:
     - Working-copy stack: `conflicts() & ancestors(@, 50)`, adjusted to the visible active stack depth.
     - Named bookmark or branch stack: `conflicts() & ancestors(<bookmark-or-branch>, 50)`, adjusted to the visible active stack depth.
     - Explicit stack root to head: `conflicts() & ancestors(<head>) & descendants(<root>)`
   - If the narrow revset is empty but the broad inventory has conflicts, stop and tell the user there are no conflicts in the active scope. Mention that older or unrelated conflicts exist only if useful.
   - If the narrowed revset still includes conflicts below the active branch point or outside the named bookmark/branch, exclude those from the worklist unless the user explicitly asked for them.
   - Use the user's wording to determine scope. Match the conflicts they mentioned by change ID, description, path, bookmark/branch, or visible position in the active stack.
   - If the user named a conflict but it cannot be identified from the active-scope log, ask a short clarifying question before changing anything.

4. Build the worklist from the bottom of the active conflicted stack upward.
   - `jj log` is children-first by default, so use the narrowed revset with `--reversed`, for example `jj log -r 'conflicts() & ancestors(@, 50)' --reversed`.
   - Do not include conflicted changes merely because they are older ancestors of unrelated bookmarks, abandoned work, or other people's stacks.
   - Recompute this narrowed list after every resolution. Do not assume the original list is still correct.

5. Resolve one conflicted change at a time.
   - Pick the lowest remaining in-scope conflicted change.
   - Create a temporary child on top of it with `jj new <target>`.
   - Work in that new change. Use `jj resolve --list` or file inspection to find the conflicted paths, then edit the files until the conflict is fully resolved.
   - Prefer direct file edits unless the repo already has an external merge-tool workflow you need to use.

6. Ask the user whenever the intended merged result is unclear.
   - If the correct result is hard to reason about from surrounding code, tests, comments, or neighboring changes, stop and ask what the merged content should be.
   - Do not guess on ambiguous semantic conflicts.
   - If a conflicted change appears outside the active bookmark/branch scope while resolving, do not fix it unless the user explicitly expands the scope.

7. Squash the resolution back into the conflicted change.
   - After the temporary child is clean, squash it down into the conflicted parent with `jj squash --from @ --into <target> -u`.
   - The goal is for the original conflicted change to absorb the resolution and for the temporary child to disappear.

8. Re-check the active scope after every squash.
   - Run the narrowed conflict revset again, such as `jj log -r 'conflicts() & ancestors(@, 50)'`.
   - You may also run `jj log -r 'conflicts()'` as a separate inventory check, but do not let unrelated results expand the worklist.
   - If the change you just resolved cleared conflicts above it, skip those and move to the next remaining conflicted change.
   - If conflicts remain, repeat the process on the next lowest conflicted change.

9. Finish when the active scope is clean.
   - Stop when no in-scope conflicts remain.
   - Do not continue into older or unrelated conflicts after the active scope is clean.
   - Summarize what was resolved and mention whether any higher conflicts were cleared automatically by earlier fixes.
   - If unrelated conflicts remain elsewhere in the repository, mention that they were left untouched.

## Guardrails

- Keep the workflow iterative. Resolve one conflicted change, squash it down, then inspect the tree again before touching anything else.
- Do not continue upward based on stale assumptions about which conflicts still exist.
- Never use bare `conflicts()` as the default worklist. Always narrow it to the user's current bookmark/branch, working-copy ancestry, or explicitly named stack before editing.
- Do not repair old conflicted changes from unrelated branches/bookmarks unless the user explicitly asks for all repository conflicts.
- Prefer the smallest set of JJ commands needed to keep the stack understandable.
- If the user only wants analysis, you may inspect the conflicted stack without making changes, but the default use of this skill is to resolve the conflicts.
