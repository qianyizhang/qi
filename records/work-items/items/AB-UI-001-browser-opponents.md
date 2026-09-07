---
description: Add browser baseline opponents with guarded asynchronous requests.
scope: backlog item
status: stable
last_update: 2026-09-08
document_class: work_record
work_id: AB-UI-001
work_status: done
work_kind: build
added: 2026-09-08
tags: frontend
depends_on: AB-ENGINE-001
residual_of: none
residual_items: none
---

# AB-UI-001 — Browser baseline opponents

## Intent

Let a human play either color against the existing local baseline players.

## Acceptance Criteria

- Pass-and-play remains the default; random and alpha-beta opponents share the
  Python player contract with guarded state hashes and bounded browser budgets.
- Computer turns prevent human actions; errors preserve the game and require
  explicit retry. New game, import, replay, and control changes reject stale results.
- Replay/export/import and terminal behavior remain consistent with the referee.
- API parity and rejection tests, browser request-lifecycle tests, desktop/mobile
  integration tests, and the full repository gate pass.

## Context and Trade-offs

This is the third user-authorized slice. Fixed base seed zero and depth 2 / 128
nodes keep controls compact. Browser-selected executable paths and teacher access
remain outside this UI. Reusable request-generation guards protect late responses.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-08 | Codex | — | wip | User authorized browser opponent slice |

| 2026-09-08 | Codex | wip | done | Full gate and 16 desktop/mobile browser cases passed |

## Implementation Ledger

### 2026-09-08 — decision

- Evidence: shared Python choice/match contracts and stateless replay API.
- Consequence: add a guarded one-turn endpoint and browser opponent controls,
  with explicit failure recovery and cancellation on navigation/state replacement.
- Follow-up: complete real browser race tests and repository checks.
- Review: not-required.

### 2026-09-08 — verification

- Evidence: full `make check` passed with 80 Python tests, three request-lifecycle
  unit tests, docs/type/format checks, and production build. API cases prove direct
  Python parity, pre-search stale guards, terminal rejection, and budget boundaries.
- Evidence: `npm run test:e2e --prefix web` passed all 16 cases at 1200-pixel and
  390-pixel viewports. Cases cover both human colors, pass-and-play, explicit retry,
  terminal import, export/replay, and delayed responses after reset, replay,
  opponent change, and import. The race cases deliberately ignore AbortSignal.
  Screenshots at both widths were visually inspected; no layout clipping found.
- Consequence: all three authorized slices are implemented and verified. The
  browser integration lane is explicit; default checks stay engine/browser-free.
- Follow-up: future training needs its own experiment and data/license decisions.
  The existing two dependency deprecation warnings remain visible.
- Review: not-required.
