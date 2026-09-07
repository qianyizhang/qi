---
description: Add deterministic baseline players and replayable local matches.
scope: backlog item
status: stable
last_update: 2026-09-07
document_class: work_record
work_id: AB-ENGINE-001
work_status: done
work_kind: build
added: 2026-09-07
tags: domain
depends_on: AB-GAME-001
residual_of: none
residual_items: none
---

# AB-ENGINE-001 — Baseline players and arena

## Intent

Begin milestone 2 with random and alpha-beta players and a reproducible CLI match.

## Acceptance Criteria

- Seeded random and budgeted alpha-beta players return legal moves without mutation.
- Search respects a hard node budget and reports completed depth; unfinished
  iterations cannot replace the last completed result.
- Terminal values preserve player perspective and training-ruleset adjudication.
- CLI choice and match output include player settings, versions, seeds, node counts,
  and measured latency. Match snapshots replay to their recorded outcome.
- A saved opening can seed a match. Default matches finish under the existing ruleset.
- Tests and `make check` pass. Usage and baseline limitations are documented.

## Context and Trade-offs

The user authorized the next slice and commits. The referee/player separation is
preserved. External teacher integration and browser opponent controls are separate
follow-ups; this slice does not fix LLM evaluation choices or claim playing strength.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-07 | Codex | — | wip | Next-slice survey found baseline players and CLI matches ready |

| 2026-09-07 | Codex | wip | done | Baselines, match replay, and verification complete |

## Implementation Ledger

### 2026-09-07 — verification

- Evidence: seeded random matches repeat their moves and outcomes; player tests
  cover hard budgets, incomplete iterations, terminal perspective, and mate.
  A CLI alpha-beta/random smoke match ended after 90 plies in repetition with
  maximum 128 nodes per move; its snapshot replayed to the same result.
- Consequence: the player/arena path works without moving adjudication out of
  the referee. This sample is not a playing-strength estimate.
- Follow-up: none required for this bounded slice. External teacher integration
  and a fixed evaluation corpus remain in milestone 2.
- Review: not-required.


### 2026-09-07 — verification: closeout

- Evidence: the full `make check` gate passed. A subsequent opening-history guard
  passed the final 48-test suite and Ruff checks. Documentation validation also
  passed after this closeout update. Two existing dependency deprecation warnings
  remain visible. Completed depth-two search matches an exhaustive oracle.
- Consequence: the documented choice and match commands are ready for local use.
  Large match outputs stay in ignored artifacts; versioned contracts and tests
  are committed. No learning strength or cross-model fairness conclusion is made.
- Follow-up: none required for acceptance. Browser opponent controls and teacher
  integration remain outside this slice.
- Review: not-required.
