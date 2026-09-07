---
description: Add a fixed evaluation corpus and reproducible paired-color batches.
scope: backlog item
status: stable
last_update: 2026-09-08
document_class: work_record
work_id: AB-EVAL-001
work_status: done
work_kind: build
added: 2026-09-08
tags: domain
depends_on: AB-ENGINE-001
residual_of: none
residual_items: none
---

# AB-EVAL-001 — Fixed evaluation batches

## Intent

Measure the existing baseline players with replayable paired-color games.

## Acceptance Criteria

- Versioned evaluation-only corpus preserves full histories and rejects invalid,
  duplicate, or terminal entries before matches begin.
- Both color assignments retain player seeds and budgets in individual records.
- Summary reports player-relative results, termination reasons, nodes, depth,
  and latency; every completed game agrees with replay.
- Repeatability, summary accounting, CLI, and full repository checks pass.

## Context and Trade-offs

User authorized three slices and commits: evaluation, local Pikafish integration,
and browser baseline opponents. Four hand-authored openings provide engineering
coverage, not evidence of representative playing strength. No training begins.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-08 | Codex | — | wip | User authorized implementation |

| 2026-09-08 | Codex | wip | done | Full gate and eight-game corpus smoke passed |

## Implementation Ledger

### 2026-09-08 — decision

- Evidence: user accepted next-slice recommendation and authorized three slices.
- Consequence: ship a small synchronous batch runner around the existing arena.
- Follow-up: verify the committed corpus and full repository gate.
- Review: not-required.

### 2026-09-08 — verification

- Evidence: `make check` passed with 56 Python tests, web type/format checks,
  documentation checks, and production build. The committed four-opening corpus
  completed eight games at depth 1 / 64 nodes with seed 7; all results replayed.
  Focused tests independently recompute summaries and repeat paired games.
- Consequence: fixed evaluation batches are usable; artifacts remain ignored.
- Follow-up: local teacher integration, then browser opponents.
- Review: not-required.
