---
description: Implement a shared local frontend with configured players, extensible reports and bounded trace jobs.
scope: backlog item and implementation specification
status: stable
last_update: 2026-09-10
document_class: work_record
work_id: AB-UI-002
work_status: done
work_kind: build
added: 2026-09-10
tags: frontend, domain
depends_on: AB-ENGINE-005, AB-EVAL-003
residual_of: none
residual_items: none
produced_by: "show-gap@0.11.0 · agent=GPT-6 · effort=unspecified · 2026-09-10"
---

# AB-UI-002 — Consolidated local frontend

## Intent

Give qi one local frontend for Home, Play, Experiments and Reference. Support
independent Red/Black players, including humans, built-in algorithms, distinct
learned checkpoints and configured Pikafish. Bring search reports into native
pages, retain offline HTML, add Markdown narrative authoring and summary export,
and allow bounded on-demand tracing of compatible saved decisions.

The user authorized implementation on 2026-09-10. All six delivery stages are
implemented and verified; the completion ledger records the conditions and
evidence. Current contracts live in the [interface guide](../../../docs/interface.md),
[player guide](../../../src/qi/players/README.md) and
[experiment guide](../../../src/qi/experiments/README.md).

## Acceptance Criteria

1. **Shared application:** Home, Play, Experiments and Reference have consistent
   navigation, working direct links and browser Back/Forward behavior. Visiting
   another page preserves the active game and pauses automatic play.
2. **Experiment discovery:** supported search runs created by the CLI appear
   from configured local artifact folders. Pending, incomplete, invalid and
   unsupported entries are distinguishable. A bad entry cannot hide other runs.
   Discovery metadata is not presented as validated performance evidence.
3. **Independent players:** Human/Human, Human/built-in, Human/checkpoint,
   Human/Pikafish, checkpoint/Pikafish, and two different learned checkpoints
   work with either color assignment. Both sides use independently pinned
   configuration through the shared player boundary.
4. **Applicable settings:** publish server-owned capabilities/defaults/ceilings.
   Show node/depth limits, MCTS rollout length, checkpoint choice, seed and
   Pikafish timeout only where meaningful. Reject invalid settings on the server;
   distinguish requested external work, actual native work and qi charged visits.
5. **Game lifecycle:** Pause, Resume and Step are explicit. Step advances exactly
   one automated move. Leaving Play, restoring, entering replay, changing
   configuration or an execution error pauses play. Cancellation and state-hash
   guards reject stale responses, including responses that ignore abort.
6. **Session persistence:** restore one active game locally, paused, across
   refresh/reopening. Allow player/settings changes while paused and record the
   actual configuration/identity of subsequent moves. A versioned game-session
   export preserves that history; game-only snapshot import/export remains valid.
   Missing or changed resources cannot silently replace saved participants.
7. **Native reports and exports:** preserve current search comparison, outcome,
   replay, decision, tree and provenance features in native views. Native views,
   offline HTML and Markdown summary export use the same validated data and
   metrics. Partial runs, null results and denominators retain their meanings.
8. **Markdown and reference:** render authored Markdown narrative sections and
   generate Markdown summaries. Report files execute no code. The shared
   bilingual glossary comes from its existing authority, with keyboard/touch
   access and contextual explanations.
9. **Trace execution:** one bounded server-owned trace job may run at a time,
   with status and Cancel. It can complete while the browser is elsewhere or
   closed. Only a compatible, parity-validated trace is published to a fresh
   path; failure, cancellation, timeout and server interruption are explicit.
10. **Read/execute boundaries:** browsing and exporting do not run players or
    load checkpoints. Trace generation requires an explicit action. Resource
    paths are configured on the server; HTTP uses scoped IDs, not arbitrary
    filesystem paths. Large decisions/traces load on demand.
11. **Extensibility:** new pages, supported experiment readers and report output
    formats have explicit extension points without duplicating evidence
    derivation. API types are generated from the Python-owned schemas. Game
    execution, query caching and report rendering have distinct state owners.
12. **Verification and promotion:** the stage proofs below, repository checks,
    real browser integration and explicit optional-resource smoke cases pass.
    Promote implemented contracts into their owning guides and update this
    record with exact evidence; intermediate stages do not complete the item.

## Context and Trade-offs

### Evidence at the decision interview

- [Game UI](../../../web/src/main.tsx): one computer opponent and human color;
  fixed catalog-default budgets; replay/import/export and decision diagnostics.
  Current reusable modules include [board](../../../web/src/board.tsx),
  [API types/client](../../../web/src/api.ts) and
  [choice details](../../../web/src/choice-details.tsx).
- [HTTP](../../../src/qi/api.py): stateless referee/player operations and static
  board serving, without a shared frontend home or experiment discovery.
- [Search reports](../../../src/qi/experiments/README.md): standalone HTML
  comparisons, paired outcomes, replay, trees, provenance and bilingual glossary.
  [Report construction](../../../src/qi/experiments/report.py) derives views
  from validated evidence.
- [Policy](../../../src/qi/players/policy/README.md): one process-configured
  checkpoint, one CPU inference pass and no search.
- [Teacher](../../../docs/teacher.md): bounded local Pikafish/UCI analysis,
  already separate from the referee and registered players.
- [Trace inspection](../../../src/qi/experiments/inspect.py): reruns one saved
  decision only with matching source/runtime identity and deterministic parity;
  fresh trace paths and explicit recording completeness are required.
- Training, data preparation and paired evaluation have CLI/artifact workflows;
  their dedicated graphical workflows remain later work.

Concurrent frontend extraction and shared-validation work exists. Survey live
files before each stage and preserve other writers' edits.

### Locked decisions and authorities

| Decision | Lock |
| --- | --- |
| Product scope | Home, Play, Experiments and Reference, with all requested player matchups and applicable settings, delivered in stages. |
| Stack | React + TypeScript + Vite; TanStack Router; TanStack Query; shadcn/ui + Tailwind. FastAPI remains the backend. |
| State ownership | Router owns navigable URL state; Query owns server-read caching; a React reducer/context owns the active game and local restoration. |
| Reports | Native views plus standalone offline HTML, Markdown-authored narrative and Markdown summary export. |
| Discovery | Supported experiments under server-configured local artifact folders, including CLI-created runs. This does not auto-activate models. |
| Players | Named server-configured bindings, independently resolved and pinned per participant, including distinct checkpoints and explicit Pikafish. |
| Play lifecycle | Pause when leaving Play/restoring; explicit Resume and one-move Step. |
| Game changes | Allow paused player/settings changes for future moves and preserve their actual history in a new session record. |
| Persistence | One locally restored active session, with game-only snapshots still supported. |
| Experiment operations | Saved search inspection/export plus explicit trace generation; no experiment/evaluation launchers in this delivery. |
| Trace jobs | One bounded server-owned job, status/cancel, continued execution away from the page, no restart resume or queue. |
| Settings | Capability-specific nodes/depth/rollouts/checkpoint/seed and Pikafish timeout; engine paths, network, threads and hash memory stay server-configured. |

[ADR-0005](../../../docs/adr/0005-shared-local-frontend.md) owns the shared
frontend/report architecture. [ADR-0006](../../../docs/adr/0006-independent-player-bindings.md)
owns independent player bindings and external-engine participation.
[Core model](../../../docs/models.md#player-configuration-and-identity) and
[glossary](../../../docs/glossary/ddd.md) own accepted meaning.
The current [interface guide](../../../docs/interface.md) continues to describe
implemented behavior until these stages land.

## User Flows

| Surface | Flow |
| --- | --- |
| Home | Resume the saved game, see available players, or open recently discovered experiments and trace-job status. |
| Play | Select Red/Black controllers and applicable settings, then Resume or Step. Pause to change future configuration; inspect history without altering it. |
| Experiments | Choose a run, filter by player/budget/position, inspect a game/decision, and open a recorded tree or explicitly generate a compatible trace. |
| Reports | Read Markdown narrative beside measured evidence; export an offline interactive HTML report or static Markdown summary. |
| Reference | Search the canonical bilingual glossary; follow context links from controls, diagnostics and report fields. |

Example target: Red uses checkpoint A and Black uses Pikafish with explicit
limits. After several moves the user pauses, changes Black's future node limit
and resumes. Earlier decisions retain their original configuration. Navigating
to Experiments pauses the game; a separately requested trace job may continue.
Returning to Play restores the board and waits for Resume.

## Frontend and API Architecture

Use route-level feature containers and shared presentation components. Native
and offline report components receive validated data; they do not depend on
route loaders or a running API to render an exported report. Reuse board,
decision, glossary, table and tree components rather than retaining divergent
native and export implementations.

The route shape starts with /, /play, /experiments,
/experiments/:runId and /reference. Selected units, plies, traces and filters
belong in validated URL parameters where useful for navigation. Direct route
loads must reach the app, while unknown API/static requests preserve proper
errors. Future pages enter through explicit route/navigation registration.

TanStack Query owns catalog, run and job-status reads. Player selection remains
an explicitly triggered operation with automatic retry disabled, guarded by the
existing request-generation and full-state hash boundaries. Refocus/refetch must
never advance a game or start a trace. Keep replay view state distinct from live
game state. Deep-freezing or caching a client object is not evidence validation.

Generate TypeScript API declarations from the Python OpenAPI schema and use
typed request/response adapters. Python validates authoritative inputs and
evidence. Client form/URL validation improves feedback without becoming a
second domain implementation. Pin compatible dependency versions in the
lockfile during implementation; use the accepted libraries without unrelated
framework upgrades.

Extend existing Python adapters with separately owned operations for binding
metadata, experiment discovery/detail/exports and trace start/status/cancel.
Return readable errors plus stable codes. Request IDs resolve only within
configured roots; canonical path containment also applies to symlinks and
referenced artifacts. The frontend cannot supply executable, checkpoint,
arbitrary input or output paths.

## Player and Game-Session Contract

Human is a controller choice; automated choices reference a Player binding.
Catalog metadata separates implementation ID/version, binding ID/label, resource
identity, availability and supported settings. Existing algorithm registrations
remain shared; checkpoint files do not become new algorithm implementations.

Resolve and pin the chosen resources per participant. A readable but changed
binding is not the saved identity. Preserve a restored game in paused state
when a resource is unavailable, incompatible or mismatched. The user may select
a replacement explicitly; only subsequent decisions acquire its identity.

Publish applicable defaults, bounds, units and semantics from the server.
Local search has a hard qi work budget. Pikafish has requested UCI limits,
engine-reported diagnostics and a finite deadline; missing native counters stay
unknown and overshoot is reported rather than clamped. Native cp/mate scores
retain perspective and bounds. CPU policy inference exposes no ineffective
search controls. The server rejects out-of-range or inapplicable submitted
settings rather than silently changing the user's selected configuration.

Maintain one active game session per browser origin. Its versioned saved record
contains the existing referee snapshot, current controller bindings/settings,
configuration changes at ply boundaries, and known per-move attribution and
diagnostics. Save authoritative move results only after accepting the guarded
response. Restore through Python snapshot validation, then reconcile resources,
and remain paused. Concurrent tabs must not silently overwrite a newer saved
revision or both auto-run the same active session.

Pause and invalidate an outstanding decision before applying settings changes.
These changes affect future moves; old configuration, identity and diagnostics
remain immutable. Preserve explicit human attribution for newly played human
moves. Snapshot-only imports have unknown player attribution for their existing
prefix; do not invent it. Session import/export is a distinct versioned format,
and users can still export or import a portable game-only snapshot.

Replay and raw snapshots remain referee-owned. A mixed-player exploratory
session is not a fixed-participant evaluation: do not score or import it as such
without the evaluation owner's explicit protocol. Round-trip session tests must
cover mixed configurations, unknown imported prefixes and absent resources.

## Experiment and Report Contract

Initially recognize the existing search-experiment format. Use explicit
format-aware discovery beneath configured roots; exclude source snapshots,
dependency trees, generated reports and trace-job state. Return bounded metadata
for listings and validate selected evidence before exposing derived results.
Keep invalid entries visible with reasons; isolate invalid traces from valid
base-game evidence without presenting the trace as verified.

Display planned/completed counts, pair denominators, null outcomes and
recording completeness from their owning validators/scorers. Reading a legacy
supported run does not require its original runtime; generating a new trace
does. Unsupported formats should be named as unsupported, not guessed into the
search schema. Load large units and paginated trace children on demand.

Provide a versioned presentation-data boundary with Markdown narrative sections,
validated evidence references and registered application views for comparisons,
boards, decisions and trees. Reader adapters and output renderers are separate
extension points. Add new run kinds when their schemas arrive; no executable
plugins are loaded from artifact folders.

Author narrative in an optional Markdown sidecar using an ordinary editor;
an in-app editor is outside this delivery. Treat narrative as authored
interpretation, distinct from measured fields. Support ordinary Markdown and
GFM tables/links, resolve local evidence references within the run, and render
without executable MDX or raw active HTML. Validate unsupported references
explicitly. Record narrative and presentation identity separately from raw-run
identity; editing narrative must not alter evidence fingerprints.

Offline HTML is a self-contained interactive projection with bundled assets,
retaining the existing no-server/no-network operation. Markdown export contains
readable narrative, static summary tables, provenance and references to detailed
evidence. Represent interactive-only sections with clear references; do not
claim that a Markdown file reproduces the full interactive tree. Existing HTML
CLI usage stays valid and gains Markdown export. Derived export files must
never overwrite raw evidence.

## Trace-Job Contract

The UI requests one recorded unit/turn with its run/unit identity and a bounded
event limit. Player settings, seed and starting history come from the saved
decision and cannot be overridden by that request. Preflight verifies supported
format, evidence and exact source/Python/package compatibility before launch;
the worker rechecks before execution. A mismatch explains the unavailable
action and preserves readable reports/existing traces. Do not automatically
checkout historical code or rerun the benchmark.

Run one job at a time in a cancellable child process, with a finite
server-configured wall-time ceiling and the existing event-cap semantics:
100000 default events, with a maximum accepted limit of 1000000. A second start
while occupied returns a clear busy response; duplicate submission must not
start another job. Bound job-state/log output as well as trace memory.

Persist minimal job metadata separately from valid trace files, with explicit
running, succeeded, failed, cancelled, timed-out and interrupted states.
Report status and observed counters when available, without invented percentage
progress. The job can finish after navigation or browser closure. Server shutdown
terminates its worker; a later startup marks unfinished jobs interrupted without
resuming them. These are explicit trace jobs, not a general scheduler.

Cancellation and deadline handling terminate only the owned worker and clean up
its unpublished output. Publish a fresh trace atomically after deterministic
parity and trace validation. A capacity-limited recording may be published only
with its explicit incomplete status and successful decision parity; a failed or
terminated computation must not appear as a valid completed trace. Cancellation
and success races have one terminal result, never contradictory status.

Save successful traces under their run's existing trace area; refresh native
views and allow subsequent export to include them. Do not rewrite benchmark
units or mix traced timing into original untraced metrics.

## Delivery Stages and Ownership

| Stage | Owner and scope | Independent proof |
| --- | --- | --- |
| 1. App foundation | AB-UI-002: React shell, routes, typed API integration, Query reads, shared controls/reference and preserved game state across navigation. | Direct links, Back/Forward, glossary and existing game/replay flows work; navigation cannot advance a paused game. |
| 2. Reports | AB-UI-002: configured experiment discovery, validated detail APIs, native views, Markdown narrative/export and offline HTML reuse. | One valid and one incomplete run agree across views/exports; invalid/unsupported entries and large traces behave correctly. |
| 3. Player boundary | AB-ENGINE-005 owns independent checkpoint bindings and paired proof. AB-UI-002 adds explicit Pikafish player adaptation/capabilities, reusing that boundary and shared validators from AB-EVAL-003. | Different checkpoint digests coexist, changed resources fail, native engine limits stay distinct, and pure evidence readers execute no players. |
| 4. Play sessions | AB-UI-002: Red/Black controllers, applicable settings, paused changes, Resume/Step, local persistence and session import/export. | All accepted matchups, delayed-response races, restoration and mixed-configuration history pass. |
| 5. Trace jobs | AB-UI-002: explicit bounded trace execution, persisted job status/cancel, fresh validated publication and report refresh. | Compatible trace succeeds; mismatch, timeout, cancellation, duplicate start and server interruption are handled honestly. |
| 6. Integrated verification | AB-UI-002: browser parity, optional-resource smoke proof, usage/contracts and exact completion ledger. | All acceptance criteria pass with recorded conditions; remaining optional-resource gaps are named rather than called complete. |

Stages 1 and 2 can proceed while shared player prerequisites are being completed.
Stage 3 must consume the current shared-validation work, not recreate its checks.
Each implementation writer owns its named modules/files and preserves concurrent
changes. No new Campaign is needed for this settled, staged scope.

## Verification and Documentation

Use focused Python tests for readers, binding/identity, settings validation,
session parsing and trace-job lifecycle. Use meaningful component/lifecycle
tests for state transitions and rendering, and Playwright for user-visible
navigation, matchup configuration, restore/export/import, delayed responses,
reports/Markdown and trace controls at desktop/mobile widths.

Run make check and the affected browser E2E lane. Run the learning lane for
checkpoint integration and explicit local smoke cases for two distinct
checkpoints and configured Pikafish. Record actual artifact identities, settings,
outcomes and skip reasons; these functional checks make no strength claim.
Default tests must remain usable without installed engines, GPU or model files.
Use protocol fakes for default failure/timeout tests and actual optional resources
for the explicitly recorded integration proof.

Check native and exported summary parity on the same validated run, preserving
nulls, sample counts, partial status and provenance. Check HTML offline behavior
and Markdown links/content. Retain existing source-compatibility, tree-capacity,
saved-evidence and replay tests. Browser tests must cover focus/refetch,
configuration changes during a delayed request, multiple tabs, cancellation
races, restored missing resources and imported unknown history.

Promote completed behavior into README, docs/interface.md, the player,
experiment and learning guides as applicable. Keep the glossary source shared.
Update API/artifact schema versions where contracts change, describe supported
old formats, and preserve original evidence during migration. ADRs own durable
rationale; this item owns stage progress and implementation evidence.

## Deferred Work and Open Questions

No material product or architecture decisions remain open for this delivery.
Exact package versions, module filenames, renderer internals and configured
resource ceilings are implementation choices to verify against the locked
contracts.

Deferred: experiment/evaluation launchers, data/training controls, additional
experiment-kind views, WYSIWYG narrative editing, a multi-game library, remote
multiplayer/cloud deployment, background game execution, trace queues/restart
resume, graphical Pikafish threads/hash configuration and arbitrary engine or
checkpoint path selection. These require separately scoped work.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | User requested a decision interview followed by a specification/work item and locked ADRs. |
| 2026-09-10 | Codex | deferred | ready | User settled all three rounds, including stack/Markdown, independent bindings, UI trace generation, job lifecycle and recorded paused configuration changes. ADR-0005 and ADR-0006 are accepted. |
| 2026-09-10 | Codex | ready | wip | User authorized the refactor; implementation and verification underway. |
| 2026-09-10 | Codex | wip | done | All six stages passed repository, desktop/mobile browser and real configured-resource verification; contracts promoted to their owning guides. |

## Implementation Ledger

### 2026-09-10 — verification: review, fixes and cleanup before commit

- Evidence: a fresh code and browser review found malformed discovery metadata
  could hide other runs, replay/restore responses could outlive replacement,
  cancellation did not cover stalled response bodies, and typing settings caused
  a save per keystroke. Trace changes also needed their own presentation-cache
  invalidation. Regression cases now cover these paths and damaged-save recovery.
- Evidence: reviewed worker ownership under failed metadata writes and fixed
  resource release. Named policy imports now return the learning-extra error
  consistently. The pure-reader test no longer imports optional PyTorch merely
  to replace its loader; all 23 lab tests also passed with torch imports blocked.
- Evidence: `make check` passed 432 Python tests, with the single opt-in MPS
  skip, and five request-lifecycle tests. The desktop/mobile lane passed 42
  browser cases. OpenAPI still matches the Python contract. The renewed local
  matchup smoke (`artifacts/ui-002-verification/review/matchup-matrix.json`)
  retains two-ply evidence for all 11 color assignments without modifying the
  earlier integration records or the user's active game.
- Consequence: settings now apply together per side; pending edits block moves
  until applied or discarded. Reference has topic filters and clear empty
  results; Home prioritizes configured players; finished games name the winner
  and expose New Game beside the status. Board sizing, keyboard access and
  button contrast were reviewed. Reports load separately from the main bundle,
  and idle trace-status polling is reduced.
- Consequence: removed unused Radix tabs and its orphaned dependencies, the
  unused frontend opponent-result alias, the per-field save/merge path and the
  anchor-color override. The obsolete standalone renderer is removed in this
  refactor. Corrected stale pending-implementation, raw-JSON-help and policy
  loading/timing prose in current model, glossary and module authorities;
  retained supported snapshot/evaluation formats and historical work evidence.
- Follow-up: commit the verified refactor as requested. No unresolved review
  findings remain within this scope; deferred product features remain deferred.
- Review: not-required.

### 2026-09-10 — verification: integrated refactor complete

- Evidence: `make check` passed Ruff, documentation hygiene, TypeScript,
  formatting, both production builds, 421 Python tests and four request-lifecycle
  tests. One opt-in MPS test was skipped; `make test-learning` separately passed
  all 31 CPU learning checks. The desktop/mobile browser lane passed 32/32 cases.
  Generated OpenAPI agrees with the current Python contract. Final title and
  Home copy edits passed the frontend checks and both builds again.
- Evidence: browser cases cover native/offline report parity, incomplete runs,
  Markdown and glossary access, filtered replay and paginated/capacity-limited
  trees, trace publication/refresh, all cancellation races, explicit retry,
  multiple tabs, paused restore, unavailable players and unknown snapshot history.
  Python tests cover identity/settings validation, pure evidence reading and
  trace idempotency, cancellation, timeout, shutdown and restart interruption.
- Evidence: the real-resource matchup matrix (`artifacts/ui-002-verification/matchup-matrix.json`)
  completed two plies for each of 11 distinct color assignments covering
  Human/Human, Human/alpha-beta, Human/checkpoint, Human/Pikafish,
  checkpoint/Pikafish and two checkpoints. The
  mixed-play record (`artifacts/ui-002-verification/mixed-play.json`)
  preserves four successive trained-A/Pikafish/trained-B/Pikafish decisions.
  Local Pikafish 2026-01-02 used one thread, 16 MiB hash, requested 128 nodes,
  depth two and a ten-second timeout; its first response reported 140 native
  nodes and depth two, retained without clamping or converting to qi visits.
- Evidence: the paired checkpoint record (`artifacts/ui-002-verification/two-checkpoint-evaluation.json`)
  completed both color assignments from the initial position, with repetition
  draws after 52 and 34 plies. Named resources and full digests are recorded in
  the catalog (`artifacts/ui-002-verification/catalog.json`).
  Actual browser inspection also stepped trained A, Pikafish and trained B,
  displayed native work/score/resource identities, preserved the game on Home,
  and verified the Home layout. These are functional checks, not strength evidence.
- Evidence: the existing search-v1 run remained readable at 380/384 completed
  units, with five valid saved traces and no validation warnings. Source/runtime
  mismatch correctly disabled new tracing. The
  read observation (`artifacts/ui-002-verification/historical-report-read.json`)
  records this bounded compatibility check; raw historical evidence was unchanged.
- Consequence: all delivery stages and acceptance criteria are satisfied.
  AB-ENGINE-005 supplies the shared binding boundary; the refactor consumes
  AB-EVAL-003's shared validator and extends its typed native-engine evidence.
  CLI, FastAPI and React retain their declared ownership. README, interface,
  player/evaluation/learning/experiment guides, model bindings and glossary now
  describe the implemented contracts. Accepted ADR decisions are unchanged.
- Follow-up: none within this item. The explicitly deferred products above
  remain separately scoped; no GPU-training or playing-strength result is claimed.
- Review: not-required.

### 2026-09-10 — decision: implementation authorized

- Evidence: user asked to proceed with the refactor. AB-EVAL-003 is implemented
  in the live tree with its verification record; independent bindings remain
  to be implemented.
- Consequence: begin the full agreed scope and consume the shared validator.
  Preserve concurrent changes and validate each stage before final completion.
- Follow-up: implement and verify all delivery stages, including optional
  configured-resource smoke cases.
- Review: ratified.

### 2026-09-10 — finding

- Evidence: inspected live frontend, API, report builder, player/teacher
  contracts, existing ADRs and independent-checkpoint work item.
- Consequence: distinguish existing behavior, inherited constraints, proposals
  and accepted decisions.
- Follow-up: complete the requested interview and durable specification.
- Review: not-required.

### 2026-09-10 — decision: scope and persistence

- Evidence: user accepted round 1 scope, native reports/offline HTML, experiment
  discovery and one restored active game; requested Markdown extensibility and
  an explicit modern frontend architecture discussion.
- Consequence: retain those scope locks; discovery concerns experiments and
  does not auto-activate models.
- Follow-up: resolve stack, report formats and runtime boundaries.
- Review: ratified.

### 2026-09-10 — decision: stack, reports and players

- Evidence: user selected the recommended stack, both Markdown authoring/export,
  independent named players and pause/resume behavior. They explicitly selected
  UI trace generation over the read-only recommendation.
- Consequence: accept ADR-0005 and ADR-0006; route shared checkpoint work through
  AB-ENGINE-005 and keep the trace execution boundary explicit.
- Follow-up: settle job lifecycle, mid-game changes and available controls.
- Review: ratified.

### 2026-09-10 — decision: execution and session boundaries

- Evidence: user selected one bounded server-owned trace job with status/cancel,
  paused changes with recorded configuration history, and capability-specific
  controls with engine paths/threads/hash configured on the server.
- Consequence: finalize this specification and stage ownership. No further
  product decision round is required; product implementation has not begun
  as part of this interview.
- Follow-up: begin the independently verifiable stages when implementation is
  requested, preserving active concurrent work.
- Review: ratified.

### 2026-09-10 — verification: specification and authority updates

- Evidence: documentation hygiene checked 92 Markdown files successfully;
  all four glossary tests passed; diff whitespace checks passed. Reviewed
  advisory authoring findings: ambiguous dictionary matches do not justify
  replacing referee/outcome/history terms, and related acceptance actions remain
  grouped deliberately.
- Consequence: the ready specification, two accepted ADRs, model/glossary
  bindings and AB-ENGINE-005 ownership agree. Existing concurrent code changes
  are outside this documentation work.
- Follow-up: implementation stages still require their full behavioral and
  optional-resource verification; those tests were not run for this spec-only
  change.
- Review: not-required.
