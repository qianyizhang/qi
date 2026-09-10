---
description: Clarify observation identity and representation boundaries when a second consumer needs them.
scope: backlog item
status: experimental
last_update: 2026-09-10
document_class: work_record
work_id: AB-DATA-006
work_status: deferred
work_kind: build
added: 2026-09-10
tags: domain
depends_on: none
residual_of: none
residual_items: none
---

# AB-DATA-006 — Observation and representation contracts

## Intent

Separate representation-independent observation identity from tensor/text
rendering when a second consumer makes the boundary concrete.

## Acceptance Criteria

- Inventory existing consumers and distinguish visible board/turn observation,
  full referee state with history, and supervision provenance.
- Establish the smallest shared contract needed by real consumers; keep tensor
  encoding and LLM rendering with their respective adapters.
- Preserve existing dataset/checkpoint fingerprint meanings or require an
  explicit versioned migration; never silently replace full-history identity
  with board-only identity.
- Verify existing training/inference parity and the new consumer's contract.

## Context and Trade-offs

[Core model](../../../docs/models.md) owns relationships and
[Training Data](../../../src/qi/training_data/README.md) owns frozen evidence.
This is a future boundary refinement, not a request for speculative packages.
It is separate from [experiment-data sanity](AB-DATA-005-experiment-data-sanity.md)
and is not an automatic prerequisite for an LLM feasibility run.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | Preserve the review proposal until a concrete second representation needs it. |

## Implementation Ledger

No implementation events yet.
