---
description: Decide direct retirement of the flag-based learning-curve adapter.
scope: backlog item
status: experimental
last_update: 2026-09-11
document_class: work_record
work_id: AB-LEARN-011
work_status: deferred
work_kind: decision
added: 2026-09-11
tags: domain, hygiene
depends_on: AB-LEARN-005
residual_of: none
residual_items: none
---

# AB-LEARN-011 — Retire the curve adapter

## Intent

Decide whether to migrate remaining flag-based learning-curve callers to Recipe
and remove the adapter. [experiment.py](../../../src/qi/learning/experiment.py)
calls the configured runner, while [runs.py](../../../src/qi/learning/runs.py)
imports LearningPlan and the curve summary back from that adapter. Optional legacy
arguments select different manifest and result shapes inside the execution loop.

## Acceptance Criteria

- Inventory the live `qi learn experiment` command, Python callers, tests and guides;
  distinguish executable entry points from readers of retained evidence.
- Choose the replacement command/Recipe workflow and whether the flag entry point
  can be removed directly. Do not silently remove a documented command as hygiene.
- Define parity for nested input ordering, seed matrices, deadlines, partial runs,
  and summaries; preserve recorded evidence and its original identities.
- If retirement is accepted, specify a bounded build slice with one execution
  path and no aliases or compatibility wrappers. Place shared ordering, provenance
  and summary logic outside the retired adapter.

## Context and Trade-offs

This is an executable-API decision, separate from
[snapshot training](AB-LEARN-010-snapshot-training-protocol.md). Existing JSON readers
and historical migration checks remain supported; the word legacy alone does not
make them removable. No training run or evidence rewrite is authorized by this item.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-11 | Codex | — | deferred | Survey identified reverse adapter dependencies; migration needs a command/format decision before implementation. |

## Implementation Ledger

No implementation events yet.
