---
description: Bind separate checkpoint identities to local evaluation participants.
scope: backlog item
status: stable
last_update: 2026-09-10
document_class: work_record
work_id: AB-ENGINE-005
work_status: done
work_kind: build
added: 2026-09-10
tags: domain
depends_on: none
residual_of: none
residual_items: none
---

# AB-ENGINE-005 — Independent checkpoint participants

## Intent

Allow two learned checkpoints to coexist in local play and paired evaluation,
with each participant pinned to its own content identity. Implement the shared
checkpoint binding portion of
[ADR-0006](../../../docs/adr/0006-independent-player-bindings.md); the
[consolidated frontend](AB-UI-002-consolidated-lab.md) consumes this boundary.
The user locked independent named player entries in that decision interview.

## Acceptance Criteria

- Resolve and pin a checkpoint separately for each participant before execution;
  retain that participant's digest on every recorded decision.
- Separate implementation IDs/versions from named server-configured player
  bindings. Two bindings can use the same policy implementation and different
  checkpoints without separate algorithm registrations.
- Keep `QI_POLICY_CHECKPOINT` as a convenience default and keep checkpoint paths
  outside the HTTP request contract. Expose binding IDs, readable labels,
  availability, supported settings and pinned identity through the catalog.
- Reject explicit content mismatches; summarize saved evidence without loading
  checkpoints or executing players.
- Use this one construction/binding boundary from CLI, HTTP, arena and
  evaluation. Cache loaded checkpoints by verified identity without sharing one
  mutable default between participants; each decision must use its pinned model.
- Verify a two-checkpoint paired evaluation, existing default behavior and
  identity failures. Include same-implementation/different-checkpoint selection,
  missing or changed resource rejection, and evidence validation with model
  loading disabled; run `make check` when implemented.

## Context and Trade-offs

Before this change, the [policy player](../../../src/qi/players/policy/__init__.py)
resolved both participants from one environment setting. An expected digest
verified the configured model but could not select a second one. Named bindings
now resolve independently; [the player guide](../../../src/qi/players/README.md#named-player-bindings)
owns their implemented configuration and identity contract.
Preserve [evaluation](../../../docs/evaluation.md) and player ownership. A
binding name resolves local configuration; recorded content identity verifies
the actual selected model. Browser selection uses exposed IDs, never raw paths.
Changing an entry or replacing its file cannot silently replace an already
pinned participant. Missing or changed identities produce an explicit error.

This item owns shared binding construction, checkpoint resolution and its
CLI/HTTP/arena/evaluation contract, not the frontend controls or Pikafish adapter.
AB-UI-002 owns those consumers and must reuse this implementation. Coordinate
common evidence checks with
[AB-EVAL-003](AB-EVAL-003-shared-decision-validation.md); keep checkpoint loading
outside pure validation. Preserve existing valid artifact meanings and version
changed serialization contracts explicitly.

This remains independent of the position-only LLM baseline. The later refactor
authorization covered implementation; the completion ledger records its proof.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | Captured from the repository reviews as part of the requested general backlog plan. |
| 2026-09-10 | Codex | deferred | ready | User selected independent named player entries, including two distinct checkpoints, during AB-UI-002; ADR-0006 locks the shared boundary. |
| 2026-09-10 | Codex | ready | wip | User authorized the refactor; implementation and verification underway. |
| 2026-09-10 | Codex | wip | done | Independent identities passed paired evaluation, pure saved-evidence validation, legacy-default checks and integrated frontend verification. |

## Implementation Ledger

### 2026-09-10 — verification: independent participants complete

- Evidence: shared binding construction resolves server-configured IDs to one
  implementation and verified resources, rejecting changed or missing bytes.
  Named policy models cache by verified identity; the legacy environment default
  retains its pinned process behavior. Match/evaluation schema version two
  records binding identities; valid version-one evidence remains readable.
- Evidence: the learning integration tests select two different checkpoints of
  the same implementation, preserve each decision's digest, reject mismatches,
  and reload/summarize saved evidence with resource configuration removed and
  model execution disabled. `make check` passed 421 Python tests (one opt-in MPS
  skip) and the separate CPU learning lane passed 31 tests.
- Evidence: the local paired evaluation (`artifacts/ui-002-verification/two-checkpoint-evaluation.json`)
  used checkpoints size-96-seed-7.pt and size-96-seed-17.pt, with distinct digests
  `7edd6b9e351ae0ee07967904ffc64097f29975439932112d7c0c944954f75a39`
  and `5c716df2c840738e45014324e9004fe2706a1b028fcaa0c262e573dc3b90cd65`.
  Both initial-position color assignments completed, with repetition draws
  after 52 and 34 plies. The summary (`artifacts/ui-002-verification/two-checkpoint-summary.json`)
  was derived from validated saved evidence. This verifies construction and
  replay; it provides no estimate of general playing strength.
- Consequence: CLI, HTTP, arena and evaluation share the same binding boundary;
  AB-UI-002 consumes it for independent Red/Black selection and recorded changes.
  Player, learning, evaluation and interface guides now own current usage.
- Follow-up: none within this item. Optional MPS training is outside this CPU
  inference and independent-participant change.
- Review: not-required.

### 2026-09-10 — decision: implementation authorized

- Evidence: user authorized the consolidated frontend refactor and its shared
  prerequisites.
- Consequence: implement independent bindings here and reuse the shared
  decision validator already present in the live tree.
- Follow-up: verify separate checkpoint identity across selection and paired
  evaluation without loading models during saved-evidence validation.
- Review: ratified.

### 2026-09-10 — decision

- Evidence: user accepted independently named server-configured players for
  Play, with each checkpoint or engine identity bound per participant.
- Consequence: this existing item owns the reusable checkpoint portion; the
  frontend item links to it instead of implementing a second model selector.
- Follow-up: implement binding/resolution and paired proof, then expose the
  shared contract to the frontend stages. No product code changed in this
  decision interview.
- Review: ratified.
