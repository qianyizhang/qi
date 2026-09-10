---
description: Make a tiny reference experiment reproducible in a clean CPU environment and CI.
scope: backlog item
status: experimental
last_update: 2026-09-10
document_class: work_record
work_id: AB-REPRO-001
work_status: deferred
work_kind: build
added: 2026-09-10
tags: hygiene
depends_on: none
residual_of: none
residual_items: none
---

# AB-REPRO-001 — Reference experiment and clean CI

## Intent

Provide one small, self-contained reproduction path that does not depend on local
ignored artifacts, a teacher installation or a GPU.

## Acceptance Criteria

- Check in a tiny frozen fixture dataset, resolved CPU recipe and documented
  command that creates fresh artifacts and verifies their identities and metrics.
- Declare expected outputs and numerical tolerances; avoid unsupported claims of
  identical weights or timings across platforms.
- Run repository checks on clean Linux and add a bounded CPU-learning CI lane,
  requiring no network or external service after dependency installation.
- Exercise the distributed package in a clean environment, with explicit
  unavailable checkout provenance where appropriate.

## Context and Trade-offs

[Experiment method](../../../docs/experiments.md) owns lineage and evidence rules;
the [trainer guide](../../../src/qi/learning/README.md) owns execution semantics.
Existing local checks do not substitute for a clean installation/reproduction
lane. The fixture proves workflow behavior, not playing strength.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | Capture larger reproducibility work from repository reviews. |

## Implementation Ledger

No implementation events yet.
