---
description: Define development and locked-test use and uncertainty units for future comparisons.
scope: backlog item
status: experimental
last_update: 2026-09-10
document_class: work_record
work_id: AB-EVAL-004
work_status: deferred
work_kind: decision
added: 2026-09-10
tags: domain
depends_on: none
residual_of: none
residual_items: none
---

# AB-EVAL-004 — Held-out evaluation methodology

## Intent

Make future comparison claims explicit about test reuse and correlated evidence.

## Acceptance Criteria

- Define development versus locked-test lifecycle, reveal/retirement rules and
  exploratory versus confirmatory reporting for a concrete upcoming comparison.
- Choose the independent unit for uncertainty: source family or generation block
  for related positions, and paired starts/color assignments for games.
- Specify denominators, pairing, uncertainty reporting and limits of inference;
  identify the smallest implementation follow-up required by the chosen method.
- Promote accepted decisions to the experiment/evaluation authorities while
  preserving the stated status of historical findings.

## Context and Trade-offs

[Experiment method](../../../docs/experiments.md) and
[evaluation](../../../docs/evaluation.md) already govern bounded claims.
This adds a concrete protocol when needed, not a general statistics framework.
[Data sanity](AB-DATA-005-experiment-data-sanity.md) covers mechanical overlap
checks; it remains a separate deferred item. No historical contamination is
inferred from this methodology proposal.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | Capture review suggestions on test reuse and uncertainty for later discussion. |

## Implementation Ledger

No implementation events yet.
