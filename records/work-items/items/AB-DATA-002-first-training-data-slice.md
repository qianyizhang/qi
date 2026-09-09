---
description: Prove the accepted Training Data boundary with random and teacher-guided sources and frozen composition.
scope: backlog item
status: stable
last_update: 2026-09-09
document_class: work_record
work_id: AB-DATA-002
work_status: ready
work_kind: build
added: 2026-09-09
tags: domain
depends_on: AB-DATA-001
residual_of: none
residual_items: none
---

# AB-DATA-002 — First Training Data slice

## Intent

Prove [ADR-0004](../../../docs/adr/0004-training-data-bounded-context.md) and the
[core model](../../../docs/models.md) with executable composition rather than
empty interfaces. This work is identified and ready; implementation has not begun.

## Acceptance Criteria

- Extract existing random generation without changing its seeded selection,
  teacher labels, split/exclusion behavior or existing artifact interpretation.
- Add teacher-guided continuations from named replay-backed starting positions;
  keep actor choice independent of supervision and validate any analysis reuse.
- Make phase, theme, optional objective and sampling window addressable under
  versioned policies. Document the initial phase classifier and example fixtures;
  do not treat ply ranges as semantic phases or claim general forced-win proofs.
- Retain reusable examples and materialize a reproducible two-mode mixture with
  state/observation/example/manifest fingerprints, exact quota accounting,
  source-family isolation and explicit incomplete status.
- Preserve one target contract and teacher recipe per dataset. Reject ambiguous
  supervision and source/observation leakage; retain contributing provenance.
- Demonstrate trainer consumption and required slice coverage/results using
  a fixed held-out recipe, with core contract tests and a bounded local pilot.

## Context and Trade-offs

Package layout, canonical serialization details, concrete classifier thresholds
and pilot mixture counts must be documented during implementation. Existing
fields and dataset artifacts need an explicit compatibility/migration path.
Learner-driven generation, recorded-game ingestion, diagram-only states,
heterogeneous supervision, dynamic epoch mixtures and persistent teacher sessions
are later extensions, not required to prove this slice.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-09 | Codex | — | ready | First implementation slice identified at design closeout; no execution started. |

## Implementation Ledger

No implementation events yet.
