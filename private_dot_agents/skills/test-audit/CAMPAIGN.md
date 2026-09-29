# Whole-subsystem test audit

Read and follow the sibling `~/.agents/skills/test-audit/SKILL.md`; this guide
adds scope and progress management, not a lower retention bar. If installed
elsewhere, resolve `SKILL.md` against this guide's directory. Campaign mode
requires an explicit whole-subsystem or whole-repository audit request. It is not permission to publish changes or expand into adjacent areas.

## Define the surface

1. Name the subsystem and its production ownership. Resolve ambiguous scope
   before deleting anything.
2. Inventory every owned test file, including integration tests outside the
   source directory, embedded language tests, fixtures, snapshots, and shared
   support code. Exclude generated or vendored code unless explicitly in scope.
3. Inspect test discovery and CI selection. Distinguish files that exist from
   tests that actually run, and document opt-in or environment-gated suites.
4. Map important contracts to their current primary proof. Use this to identify
   both overlap and gaps; the inventory is not a deletion list.

Maintain a compact ledger in the conversation or a repository-appropriate
scratch document. Do not add a permanent report file without a reason.

```text
Area/file | Contract | Status | Decision/evidence | Validation | Follow-up
```

Statuses should distinguish uninspected, inspected/retained, candidate,
changed, and validated. Mark partial inspection explicitly. For mixed files,
track cases or describe the inspected subset rather than declaring the whole
file complete.

## Discover in parallel, edit coherently

When useful and available, delegate independent read-only lanes by ownership:
core business modules, adapters/integration, applications, and tooling. Give each
lane the same evidence template, repository instructions, and scope limits.

Have a coordinator reconcile cross-cutting helpers and overlapping contracts.
Agents must not independently delete tests that each assumes the other retains.
Avoid concurrent writes or test/edit races in the same checkout. Prefer one
writer per coherent batch; use isolated worktrees for independent experimental
changes when repository policy allows them.

## Process batches

For each batch:

1. Present candidate evidence and retained false positives.
2. Select one coherent owning module or contract family.
3. Establish its baseline before changes.
4. Make and validate the changes using `SKILL.md` and repository policy.
5. Recheck the contract map against what actually remains.
6. Update the ledger with outcomes, blockers, and deferred investigations.

Do not trade independent proof for deletion volume. Shared fixture changes may
require tests beyond the selected subsystem. Coverage reports can help locate
unexercised paths, but do not establish whether an assertion is valuable.

If an important uncovered contract is discovered, record it. Add proof only if
within the requested scope and the authoring gate is satisfied; do not silently
turn pruning into a large test-expansion project.

## Stop and resume

Stop when the authorized scope is complete, a consequential uncertainty needs
user input, or required verification is blocked. Report exactly what is and is
not validated. A blocked batch is not complete.

For resumability, record the working-copy revision/base, inspected scope,
remaining candidates, required infrastructure, and last validation results.
After an upstream refresh or another batch changes shared code, recheck affected
evidence and baselines; do not apply a stale deletion plan mechanically.

Commit, push, open PRs, and merge only when authorized, using the repository's
existing workflow. If publication is requested, keep batches independently
reviewable; do not assume campaign authorization permits automatic landing.

## Completion report

Summarize:

- Inventory coverage: inspected, changed, retained, and deferred areas.
- Important contracts and where their independent proof remains.
- Removed low-value categories and production/support simplifications.
- Validation actually executed and any gaps or baseline failures.
- Production/tooling versus test/support LOC if measured.
- Named follow-ups, resume information, and authorized publication state.

A completed campaign means the defined surface was inspected and its changes
validated—not that every test was deleted, rewritten, or forced into one layer.
