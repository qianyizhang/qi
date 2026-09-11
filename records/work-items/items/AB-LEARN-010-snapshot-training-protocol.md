---
description: Lock optimizer semantics before integrating bounded Parquet reads into production training.
scope: backlog item
status: experimental
last_update: 2026-09-11
document_class: work_record
work_id: AB-LEARN-010
work_status: done
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
| 2026-09-11 | Codex | deferred | wip | User accepted bounded full-batch Adam and authorized implementation with the generated-source study. |
| 2026-09-11 | Codex | wip | done | Objective/gradient/update parity, interruption, snapshot/cache and reload checks passed; representative 4000-input pilot completed all 200 updates. |

## Implementation Ledger

### 2026-09-11 — decision: preserve full-batch updates

The user accepted full-batch Adam and authorized the first generated-source
mixture study. [ADR-0010](../../../docs/adr/0010-frozen-selection-and-bounded-full-batch-training.md)
locks bounded gradient accumulation, fixed snapshot ordering, completed-pass
accounting and checkpoint/report semantics. Implement under that decision and
verify with objective/gradient/update parity and a representative resource pilot.
Evidence: user decision and AB-LEARN-012; review not-required.

### 2026-09-11 — verification: bounded training delivered

- Evidence: implementation `b01a564`; `make check` passed 594 Python tests with
  one MPS skip, five browser tests, lint/docs/catalog/type checks and production
  build. The focused tests cover an uneven final chunk across three Adam updates,
  losses/gradients/parameters within tolerance, no update from an incomplete
  pass, cache corruption and exact checkpoint prediction reload.
- Representative evidence:
  [pilot report](../../../artifacts/learning/generated-source-mixing-v1-run3/pilot/report.json)
  and [resolved config](../../../artifacts/learning/generated-source-mixing-v1-run3/pilot/config.json).
  CPU one thread, 4000 training and 373 validation inputs, 256-row chunks:
  200/200 updates in 25.073 seconds including measured setup/finalization;
  optimization 24.313 seconds; process lifetime peak RSS 429457408 bytes.
  Snapshot hash checking precedes this timer; preparation is separate.
- Consequence: `qi learn snapshot` consumes verified, frozen Parquet evidence
  through bounded disk-backed tensor batches and records the explicit protocol,
  consumed data identity, teacher identity and terminal checkpoint. The matrix
  under AB-LEARN-012 owns any scientific conclusion.
- Follow-up: measure memory/compute again at larger sizes before scale claims;
  optimizer-state resume remains outside the accepted terminal-checkpoint contract.
- Review: not-required; accepted behavior and representative verification complete.
