---
description: Strengthen experiment data isolation at generation and evaluation boundaries.
scope: backlog item
status: experimental
last_update: 2026-09-10
document_class: work_record
work_id: AB-DATA-005
work_status: deferred
work_kind: build
added: 2026-09-10
tags: domain
depends_on: none
residual_of: none
residual_items: none
---

# AB-DATA-005 — Experiment data sanity

## Intent

Keep training and held-out evidence separate from both generation and evaluation
perspectives. These two hardening gaps are grouped and deliberately deferred;
they are not the highest-priority item or an automatic prerequisite for other work.

## Acceptance Criteria

- Generation: reject identical source trajectories assigned across training and
  validation even when sampled observations differ; distinguish unique trajectories
  from generation attempts in coverage reporting.
- Evaluation: check checkpoint training inputs against evaluation openings and
  history prefixes; distinguish held-out measurements from intentional diagnostics.
- Preserve existing evidence, audit affected artifacts, and document any correction
  without inferring that historical experiments were contaminated.
- Add focused counterexample tests and run `make check` when implemented.

## Context and Trade-offs

The September 10 review reproduced two gaps at `47da444`: identical initial-board
teacher-guided trajectories with different sampled plies passed frozen-mixture
validation; an arena run using known training positions completed without an
overlap finding. The seven preparation pilot datasets inspected had no exact
cross-split trajectory duplicates. This is bounded evidence, not a corpus-wide audit.

Owners: [Training Data](../../../src/qi/training_data/README.md),
[evaluation](../../../docs/evaluation.md), and the [core model](../../../docs/models.md).
Resolve diagnostic-mode behavior and compatibility when this item is selected.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | User grouped generation and evaluation sanity checks and explicitly deferred their priority. |

## Implementation Ledger

No implementation events yet.
