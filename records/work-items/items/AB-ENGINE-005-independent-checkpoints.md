---
description: Bind separate checkpoint identities to local evaluation participants.
scope: backlog item
status: experimental
last_update: 2026-09-10
document_class: work_record
work_id: AB-ENGINE-005
work_status: deferred
work_kind: build
added: 2026-09-10
tags: domain
depends_on: none
residual_of: none
residual_items: none
---

# AB-ENGINE-005 — Independent checkpoint participants

## Intent

Allow two learned checkpoints to coexist in one local paired evaluation, with
each participant pinned to its own content identity. Capture as an unscheduled
candidate; settle the construction/configuration boundary when selected.

## Acceptance Criteria

- Resolve and pin a checkpoint separately for each participant before execution;
  retain that participant's digest on every recorded decision.
- Keep `QI_POLICY_CHECKPOINT` as a convenience default and keep checkpoint paths
  outside the HTTP request contract.
- Reject explicit content mismatches; summarize saved evidence without loading
  checkpoints or executing players.
- Verify a two-checkpoint paired evaluation, existing default behavior and
  identity failures; run `make check` when implemented.

## Context and Trade-offs

The current [policy player](../../../src/qi/players/policy/__init__.py) resolves
both participants from one environment setting. An expected digest verifies the
configured model but cannot select a second one.
Preserve [evaluation](../../../docs/evaluation.md) and player ownership; exact
configuration shape and compatibility remain open. This enables later paired
model comparisons and is not a prerequisite for a position-only LLM baseline.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | Captured from the repository reviews as part of the requested general backlog plan. |

## Implementation Ledger

No implementation events yet.
