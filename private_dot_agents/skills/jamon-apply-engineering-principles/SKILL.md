---
name: jamon-apply-engineering-principles
description: "Apply engineering principles to software design, implementation, and review"
---

# Apply Engineering Principles

Build the smallest complete solution that satisfies the actual requirement. Minimize unnecessary concepts, competing owners, remembered facts, and maintenance obligations—not line count. A justified new domain or real history remains legitimate. Judge the whole affected behavior: callers, owners, lifecycles, and interactions.

Each rule is a strong default. Depart only for a concrete, present reason the simpler design cannot satisfy (a supported caller, an invariant, an external contract, or a measurement) and keep the exception narrow. A tell shows where to look; it is neither proof of a violation nor permission to ignore the rule. Idioms change how a rule is expressed, not whether it applies.

Never simplify away security, trust-boundary validation, data integrity, data-loss prevention, accessibility, or an explicit requirement. These are design criteria, not a workflow.

## 1. Solve the requested problem

Start from observable behavior: trigger, result, meaningful failure and cancellation, constraints. Illustrative examples are not requirements.

- Do not solve a stronger, broader, or different problem than the one asked.
- Tie fallbacks, recovery paths, and defensive defaults to a supported contract or concrete failure mode, never merely "just in case".
- Do not answer complexity with more code, guards, abstractions, tests, or process.
- For unspecified details within the request, choose a simple, reversible interpretation. State material assumptions or omitted scope.

Before writing new code, ask in order: Is it already satisfied? Can existing data, configuration, registration, or tuning express it? Does an existing owner or extension point fit? Does the platform, standard library, or an installed dependency do it? Take the first option whose contract and lifecycle fit, not merely the first that runs. Fix bugs at the shared root cause in the real owner. Use an API the request names where it lives unless that breaks a contract. Do not relocate or wrap a fitting change for theoretical layering.

To make behavior faster, stronger, or more selective, tune the rules that already govern it. One behavior with tuned parameters beats two selected by a flag; a `force_*` or `aggressive_*` path beside the normal one usually signals a bolted-on knob.

Do not pack distinct concepts onto one line, hide logic in clever expressions, or scatter one behavior across tiny files. Between equally simple options, prefer stronger standard guarantees.

## 2. Reuse what fits; create what is justified

Trace the live path first: where facts originate, who decides, who applies and presents effects, what owns completion and teardown, and which trust, persistence, concurrency, and scheduling boundaries apply. The first plausible file is often not the owner.

Reuse contracts, not resemblance. Extend an owner only when its responsibility, invariants, lifecycle, authority, persistence, and threading fit; prefer composition or a shared pure function to inheritance across incompatible lifecycles. Create a new owner when the requirement brings distinct facts, invariants, identity, or lifetime, rather than pushing it into a neighbor. Gather focused evidence first when the design hinges on an unknown.

New content rarely needs new infrastructure; it usually fits an existing registration pattern. A cross-system feature does not need a feature-wide manager; add a coordinator only when the workflow itself has state and lifetime its participants cannot supply.

Each addition answers a concrete question: what fact cannot be derived (state), what distinct responsibility (class), which supported caller (public API), what must outlive the process (persisted field), what measured cost (cache), what work proceeds meanwhile (worker). "It makes the other new abstraction work" is not an answer. Tell: a class that exists only because another new class needs it. A one-implementation interface, one-product factory, or unused configuration is speculative unless a present caller needs that seam, it isolates an existing external dependency, or the framework requires it.

## 3. Keep ownership clear

Each authoritative fact, decision, and mutation has one owner. That is not one physical copy: records, snapshots, replicas, caches, and helpers are fine when it is clear which is authoritative and none becomes a second policy owner.

Put behavior with its responsibility. A predicate over one domain object's state belongs with that domain behavior, as a method, module function, or other idiomatic construct. Access to data does not confer policy ownership. Extend the home that sibling operations already use.

Keep boundary adapters thin: network, HTTP, file, command, and UI handlers authenticate, authorize, decode, validate, resolve identifiers, and convert, then delegate. If the remaining logic would make sense without the network, file, or event, it belongs in the domain.

A helper earns its place by naming a domain operation, enforcing an invariant, hiding real detail, removing real duplication, or isolating a boundary. Keep the public surface and high-level flow easy to find without a mandatory helper layer. Avoid pass-throughs that only rename a clear call (a handler with validation, branching, or feedback is not one), extraction that only adds file-hopping, and flow that bounces from a helper into an owner wrapper and straight back.

If every caller must run `prepare_x()` before `do_x()` for `do_x()` to work, the preparation belongs inside `do_x()`, unless it is independently useful, a real lifecycle stage, or a deliberate batching contract.

Subtype checks applying different policy in shared code signal a missing polymorphic operation: adding a subtype should not require editing unrelated shared functions. In a closed data model, exhaustive pattern matching is correct, and boundary decoders may enumerate kinds once.

## 4. Derive state by default

Before storing a value, ask whether it can be derived when needed. Before synchronizing two stores, ask why there are two.

Store irreducible facts: user intent, preferences, past events, retry counts, rate-limit timestamps, committed decisions, and deliberately retained observations. Derived storage requires a measured benefit and freshness contract (section 10). Do not store copies merely to avoid passing data.

Inputs update the canonical model; outputs follow it. Tell: a mode writes output directly, then copies it back into the model on exit (`if was_x and not x: model = output`). Keep the normal output path driven by canonical state. Explicit drafts or previews with commit/cancel semantics may legitimately have separate state.

Detect change where it happens: compare before and after in the mutating code instead of keeping a "last seen" copy. Dirty markers for deferred work are fine. Do not treat a hash as exact identity unless collisions are handled or harmless.

Keep transient state on the owner whose lifetime resets it. Tell: a flag cleared at a growing number of reset sites. A one-time latch is fine when completion cannot be reconstructed from current state.

Fix ordering instead of latching around it; flags like `has_seen_initial_state` often hide a sequencing gap. A latch remains justified for irreducible history or ordering the responsible boundary cannot guarantee.

Booleans that phase one process are one enum or tagged state; `pending` plus `restored` permits "restored but never pending". Independent options stay booleans.

Derive effective behavior from preference plus current capability; runtime conditions should not rewrite a user's preference. Persistent randomness should be intentional, with appropriate lifetime and observability, not unexplained hidden fate.

## 5. Let lifecycle design remove cleanup machinery

Completion, cancellation, replacement, shutdown, and ownership transfer are part of the design. When the same cleanup must be remembered at every transition, or reviews keep finding "another missed transition", make the thing shorter-lived, atomic, or scoped with automatic cleanup, or give it an owning lifecycle hook. Keep the cancellation and transactions the requirement needs.

Remove objects from registries and subscriptions at the event that makes them ineligible; reads should not sweep stale entries. Use a bounded sweep only when no reliable end event exists, knowing its cost and delay.

Trust maintained indexes only for guarantees they actually provide. Do not assume those guarantees for arbitrary collections, retained references, concurrent mutations, or external data. A subset index can replace broad scans; excessive narrow indexes can cost more than they save.

## 6. Put behavior in the natural decision model

If the requirement is another answer to an existing decision, change that decision (suitability in selection, availability in capability, priority in the priority model). Do not add a side policy that overrides the selector's result, or clear valid intent to force an outcome. Do not invalidate an otherwise valid goal merely because execution is temporarily blocked. Safety, physical limits, and authorization stay at the boundaries that enforce them.

For reversible behavior set by current facts, derive what should be true, compare with what is, and apply one transition, instead of start and stop paths that drift apart. One-time events, irreversible actions, and real history stay event-driven.

A decision should change the state that caused it. Tell: an `*_announced` flag muting a repeated "unable" message while the system keeps retrying. Transition to a failed, deferred, or alternative state and emit the message from that transition. Rate-limiting a warning about a condition that is still correctly ongoing is different.

Executors carry out chosen intent and report facts; a control loop chooses actuator values, not new goals, preferences, or unrelated commands.

A correct branch is useless if an outer gate, early return, stale state, missing authority, or schedule keeps it from running. Check ordinary cases, meaningful absences, competing priorities, the change itself, the next eligible run, and steady state. Learn why the normal path cannot reach a rule before forcing a path around it.

Behavior also emerges from interactions: fairness, starvation relief, backpressure, timing gaps, retry pacing, ordering, and neighbors relying on side effects. Before replacing a mechanism, decide which must survive; a rewrite that keeps every return value can still lose them.

## 7. Validate and version at real boundaries

Decode external data once, at the boundary, into well-formed domain values; never decode once to validate and again to apply.

Structure, authentication, authorization, and domain invariants are distinct checks that may sit at different boundaries. A sender check gives quick feedback; the authoritative receiver still enforces. Internal calls need no speculative re-parsing, but trust needs a real contract, not just a shared build. Assertions are for programmer invariants; recoverable input errors need production handling, not silent no-ops or invented defaults.

Find the real version boundaries: storage, queues, caches, APIs, plugins, and independently deployed peers may or may not cross versions. Use native types in memory, compact forms with a shared schema, and stable names, codes, or versioned schemas where values must survive change. Names survive reordering and insertion, but renames need an explicit compatibility mapping. Do not persist incidental enum positions. Preserve integer IDs through the complete serialization path; use strings or an exact representation where numeric decoding would lose precision. Stable representations are cheap insurance even without migration code.

Compatibility must be required, not imagined. Build no migrations, shims, or fallbacks for hypothetical consumers; keep them when users, deployed peers, stored data, or published contracts depend on them, translating only at the boundary into one internal model. Otherwise delete superseded vocabulary instead of bridging it (tell: code mapping old fields onto new derivations). Defaulting missing optional fields and cleanly rejecting incompatible records are deliberate; crashes, silent corruption, and data loss are not.

## 8. Keep distributed actions and identity proportional

Prefer one named action reaching the authoritative owner over intent objects, result enums, reply protocols, and reconciliation loops. Each extra layer must own something real: a pending approval, an operation whose status matters, retry-safe execution, required ordering, compensation for partial failure, or a result the caller cannot otherwise see. Ask whether the race is external or created by unnecessary competing writers, and whether existing state propagation already reports the outcome. Keep acknowledgment, idempotency, and transactions where requirements need them.

Entry points share domain rules where their contracts match; each enforces its own trust-boundary checks. Use unified dispatch when it fits, without forcing local calls through an unsuitable network abstraction.

A replica may need to track changes it cannot make: an early "not the owner" return must not skip bookkeeping needed after a later handoff, unless the handoff reestablishes the required tracking state from an authoritative snapshot before the new owner acts.

Absence means deletion only within the scope of a complete, authoritative view, never from a partial update, page, or dropped message. Reliable delivery is neither completeness nor exactly-once execution.

Durable IDs, runtime handles, indexes, session IDs, and permissions are different domains even when all are integers; a valid ID never proves permission. Follow an existing domain's allocator, resolver, width, sentinel, lifetime, and reuse rules instead of adding a parallel lookup or generic identity framework. Do not persist transient handles as durable identity unless durability is part of their contract. Do not round-trip through unrelated identity domains to suit a misplaced API. Establish a mapping before consumers use it. Guard reused handles against delayed work with the established protocol or a generation check, only where reuse can occur. Let the owning tool generate its identifiers; plausible fabricated ones may resolve to nothing.

## 9. Choose timing semantics before mechanisms

Distinguish cooldown (eligibility after an action), cadence (recurring work), stagger (spreading it across participants), timeout (cutoff for an operation), deadline (absolute expiry), and completion (an event to observe). Never use a delay to guess that work finished.

Use monotonic time for durations within a process, wall-clock time for calendar meaning, and simulation or logical time when pause, replay, or scaling matter. Account for restart, persistence, pause, and clock adjustment. Compare timestamps only within a shared clock domain or explicit conversion contract; machines need not share a monotonic origin.

Prefer an owned deadline to flags and countdowns. Start a cooldown after success unless reserving the window first is the requirement; a cadence gate is not a cooldown, because it spends its interval before the work succeeds. Reuse platform timers, schedulers, or event loops. Avoid custom timing infrastructure or a scheduler per item when an existing shared mechanism fits. Keep control loops at the rate correctness needs. Retries need a failure policy, boundedness appropriate to the operation, and duplicate-execution semantics.

## 10. Optimize demonstrated costs

Measure the path: call volume, collection size, allocation, tail latency, throughput, memory, and behavioral tradeoffs. Small repeatable savings can count; complexity must still pay for itself.

Prefer, roughly in order: remove repeated work; improve the algorithm or data layout; narrow and hoist; reuse buffers or batch calls; cache costly results; spread work when latency and fairness allow; then concurrency or lower-level code. Remove redundant work before reducing cadence. Watch multiplicative costs: a scan called by several getters inside another loop, N+1 queries, re-scanning unchanged data, allocation in hot paths.

A cache needs an owner, source, memory bound, teardown, and freshness policy: a reliable update boundary covering its real dependencies, or a cadence whose staleness the behavior accepts. A growing invalidation check warrants comparing maintenance with recomputation. Prefer recomputation when simpler at acceptable cost; preserve required freshness either way.

Use bounded batches when order and small delays do not matter; use fair scheduling when every participant must be served. Add queues or priority only when required. Measure completion latency as well as peak reduction; starvation is not simplification.

Remove or disable development-only instrumentation and associated state using supported build/runtime mechanisms. Do not assume assertion stripping is universal or place required behavior inside assertions. Preserve needed production observability.

## 11. Use concurrency only when the whole path benefits

Concurrency adds ownership, ordering, shutdown, and stale-result duties. Use it when useful work continues while a result is pending, or the environment requires it; async syntax is not parallelism. Count dispatch, copying, synchronization, and result application. When the result is needed now, a faster synchronous path usually wins.

Default shape: capture bounded input; give one worker ownership or an immutable view; compute without touching live state; hand back one result or batch; check relevance where concurrent changes can make it stale; apply on the appropriate owner/thread; join or release as required. Do not start with a worker manager, watchdog, or cancellation protocol. Discarding a finished stale result beats interrupting work unless resources or side effects require cancellation.

Reading a live object is not automatically thread-safe: prefer ownership transfer, immutable snapshots, or channels, never an unsynchronized flag the runtime does not guarantee. Keep UI, rendering, and other thread-affine work on its required thread. Remove concurrency that provides neither demonstrated benefit nor required execution behavior.

## 12. Make contracts visible in code

Follow the language's idioms and the codebase's style; make invalid states hard to express without unnecessary type machinery. Give a fixed set of named fields an explicit shape (struct, record, typed object or literal, schema, tagged union) and keep genuine dynamic data as a map. Contain loose types at boundaries instead of hiding contracts behind casts, string round-trips, or warning suppressions.

Name the domain action (`expire_session`); keep broad verbs like `manage` for code that owns that mechanism. Prefer clear guards and one level of abstraction per function, without forcing one-liners or extracting every expression. Represent absence with an idiomatic option, nullable, or equivalent form; use a sentinel only when its meaning is unambiguous. Prefer the framework's declarative structure and lifecycle over runtime surgery that compensates for misplaced ownership.

## 13. Make tests prove supported behavior

A permanent test protects a realistic regression or supported contract, and costs upkeep. Extend existing coverage when it stays coherent; add a separate test for a distinct contract rather than growing an unrelated omnibus test. Avoid tests that merely lock implementation shape, incidental wording, or deleted-code absence, unless a supported contract or concrete risk makes that evidence valuable. Preserve meaningful boundary coverage, not every test bearing a boundary-related name.

A test naming an operation must exercise it, through the intended surface at the layer where failure occurs. Reading internal state is fine; writing it is suspect when that bypasses the behavior under test. A setup shortcut is wrong only when it skips a precondition the test claims to verify: setting `selected_item` directly cannot test whether selection is allowed, but can test a display rule after selection. Fresh fixtures and seeded data are not false confidence.

False confidence includes:

- Asserting assigned values, reproducing the implementation as the oracle, or mocking away the subject.
- Assertions that cannot fail, check the wrong outcome, or merely log it; accidental passes through degenerate paths.
- Testing below the failure's layer, stale fixtures or assumptions, or effects the environment cannot produce.
- Counting skipped or rerun-until-green tests as evidence.
- Faking a network, process, thread, or queue while claiming to prove its delivery, authority, or ordering.

Unit tests suit boundary-independent logic; their evidence does not automatically extend across the real boundary.

Do not add test-only production APIs, forwarders, flags, or alternate paths. A change to production ownership or a dependency boundary should remain justified independently of test convenience.

## 14. Keep comments and docs about the present

State current behavior, invariants, units, ownership, and surprising constraints. A short reason for a surprising present constraint helps ("read the committed value; the preview may be canceled"); the history of earlier attempts belongs in version history. Do not restate obvious code or copy one contract into many documents. Follow the project's comment conventions.

When a rule must bend, contain the exception in the smallest scope and note its concrete constraint where the next reader will see it.
