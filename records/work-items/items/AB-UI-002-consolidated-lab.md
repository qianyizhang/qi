---
description: Implement a shared local frontend with configured players, extensible reports and bounded trace jobs.
scope: completed frontend work item and delivery evidence
status: stable
last_update: 2026-09-11
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
12. **Verification and promotion:** the completion proofs below, repository checks,
    real browser integration and explicit optional-resource smoke cases pass.
    Promote implemented contracts into their owning guides and update this
    record with exact evidence; intermediate stages do not complete the item.

## Context and Trade-offs

The decision interview started from separate game, report, checkpoint, teacher,
and trace surfaces. ADR-0005 and ADR-0006 retain why these were consolidated and
why player bindings remain independent. The table below retains the accepted
scope; the promoted owners after it define current behavior.

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
The [interface guide](../../../docs/interface.md) owns the implemented app and
session behavior.

## Promoted Contract Map

| Concern | Current owner |
| --- | --- |
| Routes, API generation, state ownership and shared app behavior | [Interface: Unified local app](../../../docs/interface.md#unified-local-app); rationale in [ADR-0005](../../../docs/adr/0005-shared-local-frontend.md) |
| Independent player bindings, resource identity and native budget semantics | [Player guide](../../../src/qi/players/README.md#named-player-bindings), [Interface: Players and settings](../../../docs/interface.md#players-and-settings); rationale in [ADR-0006](../../../docs/adr/0006-independent-player-bindings.md) |
| Paused play, saved-session history, stale-response rejection and multi-tab writes | [Interface: Play lifecycle and saved sessions](../../../docs/interface.md#play-lifecycle-and-saved-sessions) |
| Experiment discovery, evidence validation, narrative and native/offline/Markdown projections | [Experiment guide](../../../src/qi/experiments/README.md#shared-app-and-report-projections), [Interface: Experiment readers and trace jobs](../../../docs/interface.md#experiment-readers-and-trace-jobs) |
| Explicit bounded trace execution, cancellation, parity publication and incomplete recordings | [Interface: Experiment readers and trace jobs](../../../docs/interface.md#experiment-readers-and-trace-jobs), [Experiment guide](../../../src/qi/experiments/README.md#optional-explored-tree-recording) |

The acceptance criteria above retain the delivery boundary. The implementation
ledger below retains failures, corrections, optional-resource proof and exact
verification conditions; these current guides replace the completed design and
test-plan prose that previously followed here.

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
