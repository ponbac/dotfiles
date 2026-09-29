---
name: test-audit
description: "Use whenever writing, changing, reviewing, or auditing tests. Applies a lightweight authoring gate and an evidence-first audit workflow for low-value, implementation-coupled, or duplicative tests and unnecessary test-support seams. Discovers each repository's testing policy rather than assuming a runner or language."
---

# Test Audit

Optimize for confidence per maintenance cost. Test repo-owned behavior through
stable module interfaces, keep independent proof of important contracts, and
remove tests or support code only when their protection is demonstrably
redundant or unnecessary. Deletion count, coverage percentage, and net-negative
production LOC are not success criteria.

## Choose the mode

- **Authoring:** apply the gate below whenever adding or changing tests. Keep
  reasoning brief; no audit inventory or report is required for ordinary work.
- **Focused audit:** inspect the requested module, changed area, or named tests.
  Begin with read-only discovery and report candidate evidence before editing.
  A review-only request remains read-only; an authorized cleanup may proceed
  after presenting the evidence without a separate approval ceremony.
- **Campaign:** for an explicitly requested whole-subsystem or whole-repository
  audit, including requests such as "all tests in this repo." Before discovery,
  read `~/.agents/skills/test-audit/CAMPAIGN.md` (expand `~` to the home directory
  if the tool requires an absolute path).

Supporting files live beside this `SKILL.md`, not in the working directory or
`~/.agents/`. If this skill is installed elsewhere, resolve `CAMPAIGN.md` against
that skill directory. Do not try `~/.agents/CAMPAIGN.md`.

Do not turn a small test change into a repository-wide audit. Do not commit,
push, open a PR, or merge unless authorized.

## Discover repository policy

Before choosing commands or test locations:

1. Read root and applicable scoped `AGENTS.md` files and linked testing docs.
2. Inspect relevant package scripts, runner configuration, and CI routing as
   needed to identify focused commands and the required final verification.
3. Identify infrastructure, isolation, credentials, cleanup wrappers, and
   restrictions on where tests may be added.
4. Check working-copy state using the repository's Git or Jujutsu workflow.
   Preserve unrelated changes.

Repository instructions govern execution. Do not assume Bun, Vitest, Cargo,
.NET, a particular package manager, or a shared completion command. Do not copy
project-specific rules into this skill or invent commands when docs are absent;
inspect the actual scripts and configuration. Ask if a consequential ambiguity
cannot be resolved locally.

Keep discovery read-only. Do not run tests that may provision services or write
data until their isolation and cleanup behavior are understood. Never use a
production or developer database as a disposable test database.

## Authoring gate

Before adding or substantially changing a test, answer:

1. **Contract:** what observable behavior, invariant, or independently meaningful
   contract owned by this repository does it protect?
2. **Regression:** what credible wrong implementation would make it fail?
3. **Distinct value:** why does existing coverage not already catch that failure?
   Prefer extending an existing case table or fixture when it covers the same
   contract. Another layer needs a distinct risk, not a replay of the scenario.
4. **Interface:** can it exercise the smallest stable module interface that
   exposes the failure without exporting internals just for assertions?

A missing answer means investigate before adding the test. Check the suspicion
patterns and retention guidance below. Do not add a matched pattern unless its
independent contract justifies it.

Prefer the cheapest sufficient proof, not automatically an end-to-end test.
Pure business-rule tests can own edge cases; integration tests can independently
own persistence, transport, configuration, or lifecycle risks. Tests crossing
different interfaces are not duplicates merely because their inputs resemble
one another.

Behavior-preserving changes to private identifiers, helper organization, or
call shapes should generally not require test changes. When they do, identify
whether the asserted detail is actually part of the contract; otherwise rewrite
at the owning module's interface.

### Regression proof

For bug fixes, demonstrate the test failing before the fix for the intended
reason and passing after it. Prefer doing this before the repair; otherwise use
an isolated worktree or another safe, repository-supported method. Never rewind
or overwrite unrelated working-copy changes.

Check that a negative case reaches the intended guard and that a positive
control rules out unrelated rejection. If reproducing the original failure is
unsafe or unavailable, state the limitation explicitly. A test observed only
passing is not a demonstrated regression test. Do not reproduce the same bug
at every layer unless each test protects a distinct failure mode.

## Suspicion patterns

These trigger investigation, not automatic deletion:

- Assertion-free execution probes with no meaningful no-throw contract.
- Self-comparisons, identity copiers, or expected values generated by the code
  being tested.
- Copied fixture inventories, manifests, exports, or declared capability flags
  that do not exercise the contract they claim to protect.
- Exact source/import/string greps coupled to private implementation details.
- Private predicate, helper, or call-shape assertions already covered through
  the owning module's interface.
- Repeated cases or provider-local replays with no distinct risk.
- Tests mostly reproving framework behavior, schema mechanics, logging shape,
  config plumbing, or simple passthrough behavior rather than repo-owned policy.
- Mocks that implement the behavior being asserted; identical mocks masking
  materially different external interfaces.
- Fixtures supplying receipts, state transitions, or callback ordering that
  production code should produce; persistence checked in a store never written
  by the exercised path.
- Negative cases passing because of an unrelated guard, invalid setup, or an
  error the real path cannot reach.
- Names claiming more than their inputs and assertions exercise.
- Tests keeping obsolete exports, globals, wrappers, or production paths alive.

## Retention and seam discipline

Retain independent proof of important business rules, public interfaces,
protocols, storage and migration semantics, authorization, security, rollback,
error classification, lifecycle behavior, platform compatibility, defaults,
generated cross-language contracts, release behavior, or architecture policy.

Also retain:

- Ordering assertions when order is observable behavior.
- Static inspection when it is the cheapest independent guard of a meaningful
  key, byte, path, or architectural rule and survives private identifier changes.
- Dependency integration tests that protect the repository's use of a
  dependency, rather than merely verifying the dependency's documented behavior.
- Fast tests with meaningful edge-case coverage or diagnostic value not
  adequately supplied by an overlapping broader test.

Slowness, static inspection, duplication of setup, or low coverage contribution
alone does not justify deleting a test. A retained baseline failure may be a
product bug: reproduce and diagnose it; do not delete or weaken the test to get
green. Repair the owner if in scope, otherwise report the blocker.

Reject production exports, flags, or wrappers whose only purpose is exposing
internals for assertions. But legitimate dependency seams—clocks, external I/O,
service adapters, deterministic randomness—are not automatically wrong because
tests supply the only alternative implementation. Ask whether the seam models
a real dependency and hides implementation, or exposes implementation details.
Keep any necessary production change small and justified; do not redesign a
module merely to accommodate a mock.

Before declaring code dead, check indirect callers, public consumers, generated
entry points, reflection/registration, and other language-specific uses. No
local non-test callers is evidence, not proof of dead code.

## Focused audit workflow

### 1. Inspect and record evidence

Read the complete candidate test and its production owner, relevant entry point,
and overlapping tests. Inspect callers, callees, sibling implementations,
history, and CI routing to the extent needed to establish the removal claim.
When the claim depends on dependency behavior, inspect the installed source,
types, or matching-version primary documentation directly.

Record each proposed removal or consolidation before editing:

```text
Candidate: exact test name and path
Actual protection: the failure it can detect
Ownership: production interface, relevant non-test callers, support seams
Remaining proof: exact retained tests and distinct risks, or why none is needed
Origin: relevant history and rationale, or explicitly unavailable/unknown
Change: remove, consolidate, rewrite, or keep; support/production cleanup unlocked
Risk and validation: focused commands and required final gate
```

Unknown history is not automatically disqualifying, but unresolved uncertainty
about the contract or remaining proof is. Retain uncertain candidates and name
the investigation needed. Prefer a few high-confidence candidates over a large
speculative inventory. Present evidence in the conversation unless a durable
artifact is requested or repository policy requires one.

### 2. Establish a baseline

Run the smallest relevant owner and sibling tests using supported runners.
Record existing failures before editing. A green suite that silently excludes
the candidate is not a baseline: confirm runner selection and any skip behavior.

### 3. Make one coherent change

Remove proven redundant tests and obsolete support code together. Keep retained
regressions at their canonical owning interfaces. Consolidate repeated setup
when useful, without constructing a new generic test framework.

Do not replace deleted tests with new tests that assert the same private
implementation. Do not remove distinct edge cases while consolidating. Do not
turn uncertain candidates into unrelated cleanup to increase deletion counts.

### 4. Validate and review

- Finish relevant test runs before editing files they exercise. Coordinate
  shared-checkout work; do not terminate unrelated user processes.
- Run focused owner and sibling tests through documented runners and cleanup
  wrappers. For removed static guards, exercise the real contract through a
  safe executable check or dry-run where available.
- Run targeted formatting and diff/whitespace checks using supported tooling.
- Run the repository's required final verification, including broader checks
  for shared helpers, fixtures, runner configuration, or test discovery changes.
- Report commands and outcomes accurately, including cache hits, skipped tests,
  infrastructure blockers, unavailable credentials, and pre-existing failures.
  Never weaken isolation or silently skip required checks to report success.
- Review the final diff for lost contracts, unjustified production changes,
  accidentally exposed internals, unrelated edits, and leftover test-only code.
  Follow any additional review gate required by the repository.

If reporting LOC, separate production/tooling from tests/test support. Treat
counts as descriptive, not a target.

## Handoff

Keep ordinary authoring handoffs brief. For an audit, report:

- Removed or consolidated categories and why they added no independent proof.
- Production/support simplifications, if any.
- Important retained candidates and their independent contracts.
- Focused and final verification actually run, with limitations.
- Production versus test LOC when useful or requested.
- Named follow-ups and any commit/PR state if publication was authorized.

Do not claim a subsystem was fully audited when only selected candidates were
inspected. Do not continue into another batch or publish work beyond the user's
authorized scope.
