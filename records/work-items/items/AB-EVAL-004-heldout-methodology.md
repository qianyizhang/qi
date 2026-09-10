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

### 2026-09-10 — decision: next comparison should use full-game results

- Evidence: the user intends full-game Elo evaluation in the next day or two and
  requested longer generation trajectories for more interesting full-game work.
- Consequence: use paired starts/color assignments as the game-level unit; keep
  reserved evaluation openings separate from the training generation now being
  calibrated in [AB-DATA-008](AB-DATA-008-generation-scaling-pilot.md). Generation
  reaching 300 plies is not itself playing-strength evaluation: report checkmate,
  stalemate, repetition and referee ply-limit draws separately.
- Follow-up: freeze participating checkpoints/opponents, opening pool, per-player
  budgets and seeds, paired-game count, draw/failure handling and a reference
  rating scale. Existing paired win/draw/loss scoring is available; the rating and
  uncertainty layer is not implemented yet. Begin with results against several
  fixed opponents, rather than relying on a random opponent alone. These are
  protocol dimensions to settle before the rating implementation/run.
- Review: ratified for the user's full-game evaluation direction; exact protocol
  remains open. This records the next comparison and does not dispatch evaluation.
