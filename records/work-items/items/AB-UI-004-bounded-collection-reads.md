---
description: Bound collection-page work while preserving cohort and snapshot semantics.
scope: backlog item
status: experimental
last_update: 2026-09-11
document_class: work_record
work_id: AB-UI-004
work_status: deferred
work_kind: build
added: 2026-09-11
tags: frontend, training-data
depends_on: AB-UI-003
residual_of: none
residual_items: none
---

# AB-UI-004 — Bound collection reads

## Intent

Make page reads scale with returned games rather than constructing every game
projection for each filter or page change. The [collection reader](../../../src/qi/collection_view.py)
currently loads every game, filters/sorts in Python, and scans the full list again
for each run's statistics. This is a code-level finding, not a measured latency claim.

## Acceptance Criteria

- Keep the [review contract](../../../docs/interface.md#generated-game-review):
  one read-only SQLite snapshot, finite query deadline, explicit denominators,
  continuation ownership, and deterministic ordering.
- Put cohort filtering, pagination and aggregate queries behind one reader owner;
  materialize only the requested game page. Retain existing HTTP shapes.
- Compare all filters, sorts, overall/run/cohort counts, and phase totals against
  fixed fixtures containing rejected, unfinished and continued games.
- Record time and peak memory on a fixed input before/after. Do not introduce
  cached counts without an explicit freshness contract or change training eligibility.

## Context and Trade-offs

Start with collection-page reads. Replay, raw-analysis verification and the separate
whole-collection quality audit have different obligations and need not move together.
Choose the SQL/query decomposition before implementation; a schema migration or new
indexes require a separate decision because this UI does not own collection writes.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-11 | Codex | — | deferred | Survey found full-list materialization beneath a paginated API; propose a separate refactor after branch integration. |

## Implementation Ledger

No implementation events yet.
