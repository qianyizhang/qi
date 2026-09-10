---
description: Lock optimizer semantics before integrating bounded Parquet reads into production training.
scope: backlog item
status: experimental
last_update: 2026-09-10
document_class: work_record
work_id: AB-LEARN-010
work_status: deferred
work_kind: build
added: 2026-09-10
tags: domain
depends_on: AB-DATA-007
residual_of: none
residual_items: none
---

# AB-LEARN-010 — Snapshot training protocol

## Intent

Integrate frozen Parquet snapshots into production training only after explicitly
choosing optimizer update, epoch, ordering and reporting semantics. This follow-up
was separated from [AB-DATA-007](AB-DATA-007-sqlite-training-data-store.md)'s accepted
completion boundary; it is not an authorized optimizer change.

## Acceptance Criteria

- Lock full-batch accumulation versus minibatch updates, batch/order/seed policy,
  epoch/step accounting, time budgets and interruption/checkpoint semantics.
- Consume the bounded snapshot reader without whole-dataset tensors or Pydantic
  materialization, including validation and diagnostics.
- Preserve checkpoint dataset/selection provenance and report the new protocol
  explicitly; do not imply numerical equivalence to existing full-batch training.
- Verify correctness under the chosen protocol and measure representative memory
  and compute cost before scale claims.

## Context and Trade-offs

The current trainer uses full-batch Adam updates. AB-DATA-007 supplies verified
snapshots and bounded tensor-preparation parity. Storage format alone does not
settle the statistical or optimization protocol. The [trainer guide](../../../src/qi/learning/README.md)
owns executable training semantics.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | User accepted separate production optimizer integration when locking AB-DATA-007 completion. |

## Implementation Ledger

No implementation events yet.
