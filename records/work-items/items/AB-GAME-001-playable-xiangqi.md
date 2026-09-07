---
description: Specify and implement the first playable Xiangqi slice.
scope: backlog item
status: stable
last_update: 2026-09-07
document_class: work_record
work_id: AB-GAME-001
work_status: done
work_kind: build
added: 2026-09-07
tags: MVP, domain
depends_on: none
residual_of: none
residual_items: none
---

# AB-GAME-001 — First playable Xiangqi

## Intent

Implement the first milestone in [project direction](../../../docs/project.md).

## Acceptance Criteria

- Define coordinates and serialization before implementing transitions.
- Implement [xiangqi-training-v1](../../../docs/xiangqi-training-v1.md), including
  repetition, the ply ceiling, and ordinary-terminal precedence.
- Two humans can complete a legal game sharing one browser in local pass-and-play.
- Keep referee operations independent of session identity and transport. Remote
  multiplayer is outside this slice.
- Structured CLI operations share the browser referee behavior.
- Legal-move checks cover cannon screens, horse legs, elephant eyes, flying
  generals, self-check, and no-legal-move outcomes.
- Illegal moves cannot mutate state; save/replay reproduces the terminal result.
- Rules tests and `make check` pass.
- Setup documents actual game commands.

## Context and Trade-offs

The decision interview settled session scope and training adjudication. This
slice is implemented. `docs/interface.md` owns the shared coordinate and
replay interface. Training follows a trustworthy referee.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-07 | Codex | — | deferred | Captured during project initialization |
| 2026-09-07 | Codex | deferred | ready | User locked local pass-and-play and simplified adjudication |
| 2026-09-07 | Codex | ready | wip | User authorized the playable slice |
| 2026-09-07 | Codex | wip | done | Shared referee, CLI/API, browser play, replay, and full checks passed |

## Implementation Ledger

### 2026-09-07 — decision

- Evidence: user accepted interview recommendations 1–4; asked to keep LLM
  experiment choices provisional and develop on the local Mac first.
- Consequence: browser play joins the first slice. The accepted educational
  ownership boundary is recorded in [ADR-0001](../../../docs/adr/0001-own-referee-and-search-use-external-teachers.md).
- Follow-up: settle browser session scope and exact simplified adjudication
  before declaring this item ready. No product implementation has begun.
- Review: ratified.

### 2026-09-07 — decision: playable boundary settled

- Evidence: user accepted local pass-and-play, threefold draw, and 300-ply ceiling;
  remote multiplayer is out of scope, with a clean extension boundary preferred.
- Consequence: promote adjudication to the versioned ruleset contract and
  ADR-0002. Mark this item ready; prior session/adjudication follow-up is resolved.
- Follow-up: define coordinates and serialization with the implementation slice.
  LLM experiment details remain deferred in the project plan.
- Review: ratified.

### 2026-09-07 — verification: playable slice complete

- Evidence: `make check` passed with 28 Python tests, Ruff, documentation checks,
  TypeScript/Prettier checks, and a Vite production build. Two upstream test-client
  deprecation warnings remain; neither is suppressed.
- Evidence: pyffish 0.0.90 matched legal-move sets at 966 sampled positions across
  ten seeded trajectories. `scripts/check_reference.py` reproduces this movement
  comparison; it makes no adjudication-equivalence claim.
- Evidence: browser play completed an eight-ply repetition draw. Replay start and
  return-to-live, board flip, validated import, export, and new-game reset were
  exercised. The exported JSON was independently replayed by the CLI. Desktop
  and 390-pixel layouts were inspected. A full 300-ply trajectory also replayed
  from an empty cache in the Python suite.
- Consequence: acceptance criteria are satisfied. Browser and CLI share the
  referee, and invalid/stale requests preserve input state.
- Follow-up: none required for this slice. Browser games require explicit export
  to persist; custom setup positions, remote multiplayer, and learning engines
  remain outside scope. Coordinate/interface authority is `docs/interface.md`.
- Review: not-required.
