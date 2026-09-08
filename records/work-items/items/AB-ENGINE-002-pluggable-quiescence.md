---
description: Make players a modular learning surface and add bounded quiescence search.
scope: backlog item
status: stable
last_update: 2026-09-08
document_class: work_record
work_id: AB-ENGINE-002
work_status: done
work_kind: build
added: 2026-09-08
tags: domain
depends_on: AB-EVAL-001
residual_of: none
residual_items: none
---

# AB-ENGINE-002 — Pluggable players and quiescence

## Intent

Give each automated player a readable module and shared extension contract, then
implement quiescence as a separately selectable tactical player.

## Acceptance Criteria

- Consolidate Player/Search/Evaluator/Policy meanings in the glossary.
- Each player has a short README and colocated tests; one catalog drives CLI,
  arena/evaluation dispatch, HTTP validation, and browser choices.
- Preserve original random/alpha-beta decisions and versions.
- Quiescence examines captures and every legal check evasion under a shared node
  budget, preserves referee outcomes/history, and reports continuation work.
- Tactical, budget, extension, API, browser, and full repository checks pass;
  paired-color comparisons are recorded without unsupported strength claims.

## Context and Trade-offs

User authorized modularization, explanatory READMEs, and quiescence implementation.
Player already owns move selection in the governing model. Policy is a distinct
state-to-action preference/distribution concept; no training surface is added.
The interface is a callable plus metadata, with explicit in-repository registration.
No dynamic plugin loader or cross-game abstraction is needed.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-08 | Codex | — | wip | User authorized the module/terminology and search slice |

| 2026-09-08 | Codex | wip | done | Full gate, extension/browser cases, and paired evaluation passed |

## Implementation Ledger

### 2026-09-08 — decision

- Evidence: the old shared entry point dispatched two implementations through an
  if branch; adapters duplicated player allowlists. At 128 nodes, baseline opening
  search stops at depth one and values a cannon-for-horse capture before recapture.
- Consequence: extract a callable player contract and shared catalog; keep the old
  player selectable. Quiescence supplies the alpha-beta leaf callback under the
  same node counter. READMEs teach mechanics; glossary owns terminology.
- Follow-up: validate extension paths, tactical/budget boundaries, and paired games.
- Review: not-required.

### 2026-09-08 — verification

- Evidence: all 24 pre-refactor random/alpha-beta sampled decisions retained move,
  score, seed, completed depth, and node count. Existing baseline versions remain.
  `make check` passed with 99 Python tests and three request-lifecycle tests, plus
  docs/type/format/build gates. The player extension test reaches selection,
  arena, and HTTP; CLI/API catalog metadata agrees.
- Evidence: all 22 desktop/mobile Playwright cases passed, including discovery of
  an added catalog ID without a frontend allowlist, metadata failure/retry, and
  quiescence diagnostics. The mobile quiescence view was visually inspected.
- Evidence: eight paired-color games over `qi-openings-v1`, seed 7, requested depth
  2 and 128 nodes for both players, produced quiescence W/D/L = 2/6/0. All final
  outcomes replayed and both players stayed within budget with zero depth-zero
  fallbacks. Quiescence used 48,512 nodes (41,592 quiescence nodes, maximum extra
  depth 8); original alpha-beta used 37,991 nodes. Mean completed ordinary depth
  was 1.00 versus 1.68. Measured mean move latency was 19.52 versus 13.35 ms in this
  run. Full match records remain in ignored artifacts/quiescence-vs-alphabeta-128.json.
- Consequence: the known recapture horizon is repaired and the player is usable
  through CLI, arena, and browser. The small corpus does not establish general
  strength or a universal speed/quality improvement. READMEs state budget trade-offs.
- Follow-up: none required for this bounded slice. Learned policies/evaluators and
  their data/inference budgets remain separate future work.
- Review: not-required.
