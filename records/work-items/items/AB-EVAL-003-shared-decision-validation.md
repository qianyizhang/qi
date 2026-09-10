---
description: Share existing decision-evidence invariants across live play and saved evaluation paths.
scope: backlog item
status: experimental
last_update: 2026-09-10
document_class: work_record
work_id: AB-EVAL-003
work_status: done
work_kind: build
added: 2026-09-10
tags: domain
depends_on: none
residual_of: none
residual_items: none
---

# AB-EVAL-003 — Shared decision-evidence validation

## Intent

Give live player decisions, arena evidence and search-experiment evidence the same
definition of valid move and diagnostic accounting.

## Acceptance Criteria

- Put pure shared checks for legality, common budgets, MCTS diagnostics and search
  counters in `src/qi/players/validation.py`, beside the player result types.
  Migrate live play, saved arena evaluation and search evidence directly to them.
- Keep replay order, expected identities, protocol restrictions, pair completion
  and outcomes with their existing owners.
- Stop at the first failed invariant with a precise reason. Preserve existing
  CLI/API error codes and boundary error types; exact message text may improve.
- Remove duplicated checks without compatibility shims, forwarding aliases,
  legacy wrappers, alternate validation paths or per-player validator callbacks.
- Reject inconsistent saved diagnostics without executing players. Cover valid
  round trips and corrupted simulation/root-visit totals and search counters.
- Perform a bounded read-only compatibility audit of tracked saved artifacts and
  representative available local runs. Record selected paths, coverage and any
  incompatibilities or unavailable evidence; preserve original artifacts.
- Preserve player behavior, charged-node budget semantics and valid artifact
  meanings; run focused tests and `make check` when implemented.

## Context and Trade-offs

At `47da444`, incrementing a saved MCTS simulation count passed
`EvalRun.validate_match` and summarization, while search-experiment verification
rejected it. This establishes an internal-accounting gap, not an incorrect referee
outcome or proof that an engine actually performed the recorded work.

Owners: [Players](../../../src/qi/players/README.md),
[evaluation](../../../docs/evaluation.md), [search evidence](../../../src/qi/experiments/evidence.py).
The shared validator consumes existing typed results and referee context; it does
not execute players, bind/load checkpoints or dispatch through the player catalog.
Callers retain real parsing, replay and protocol responsibilities and translate
validation failures into their existing error boundaries. These responsibilities
are not compatibility shims. Existing valid artifact formats and player behavior
stay unchanged; newly detected inconsistent evidence is rejected without repair.

New event storage, a general validation framework, LLM attempt formats, new
player-specific requirements for optional diagnostics, and an exhaustive historical
audit are outside scope. Test corruption and fresh round trips alongside the
bounded saved-evidence audit; do not infer broader compatibility from that sample.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | User endorsed the refactor direction and requested general backlogs before selecting an item for detailed discussion. |
| 2026-09-10 | Codex | deferred | ready | User accepted all interview recommendations and required no shims; ownership, errors and audit scope are settled. |
| 2026-09-10 | Codex | ready | wip | Direct extraction implemented; corruption tests and bounded artifact audit underway. |
| 2026-09-10 | Codex | wip | done | Shared validation, cross-boundary corruption tests, bounded read-only audit and `make check` passed. |

## Implementation Ledger

### 2026-09-10 — decision: next discussion and bounded scope

- Evidence: user accepted the four-item core backlog and this item as the next discussion.
- Consequence: scope the shared existing invariants while preserving artifact formats
  and player behavior. Implementation remains unscheduled.
- Follow-up: settle extraction ownership and compatibility details in the item-level interview.
- Review: ratified; user confirmed the proposed direction.

### 2026-09-10 — decision: direct shared validation without shims

- Evidence: user answered "all your rec; no shims" to the ownership, failure
  reporting and historical-audit questions.
- Consequence: use one pure player-owned validator, stop at the first failure
  with a precise reason, preserve CLI/API codes, and migrate all three callers
  directly. Perform the bounded compatibility audit without modifying originals.
- Follow-up: implement this bounded slice and run focused tests, the recorded
  artifact audit and `make check`. No material design questions remain; product
  implementation has not started during the interview.
- Review: ratified; no additional confirmation is required for these decisions.

### 2026-09-10 — finding: bounded saved-evidence compatibility audit

- Evidence: read-only audit of 42 tracked JSON/JSONL files found no saved decision
  evidence. The tracked `data/evaluation/{paired-baseline-v1,openings-v1,search-positions-v1}.json`
  and `data/experiments/search-components-v1.json` passed their current typed
  spec/corpus parsers; they contain plans/openings rather than recorded choices.
- Selected local evidence and coverage:

  | Path relative to repository root | Checked coverage | Result |
  | --- | --- | --- |
  | `artifacts/evaluation/paired-protocol-smoke-v1/run.json` | Full `EvalRun` validation and summarization: 8 games, 522 decisions | Accepted, complete |
  | `artifacts/mcts/vs-random.json` | Typed match parsing, replay and shared decision checks: 8 games, 548 decisions (276 MCTS, 272 random) | No inconsistent decisions |
  | `artifacts/components/mcts-leaves.json` | Typed match parsing, replay and shared decision checks: 8 games, 1,139 decisions (570 quiescent MCTS, 569 MCTS) | No inconsistent decisions |
  | `artifacts/experiments/search-v1/units/unit-00000.json` through `unit-00009.json`, and `unit-00240.json` through `unit-00249.json` | 20 initial-position probes: all 10 recipes at 128 and 2,048 nodes | All accepted |
  | `artifacts/experiments/search-v1/units/unit-00360.json` through `unit-00363.json` | Both color pairs for enhanced alpha-beta/quiescence and quiescent MCTS/MCTS, initial position at 128 nodes: 649 decisions | All accepted |

- Method: selected the initial opening, smallest/largest probe budgets, and
  smallest-budget initial color pairs from the saved manifest's planned jobs.
  Checked `manifest.json` plan/corpus digests, unit/job identity, turn replay,
  `check_choice`, and final snapshots. Read `status.json`: the search run is
  `deadline`, so this sample does not establish whole-run completion. Older
  evaluation files were checked as typed matches, not relabeled as `EvalRun`.
  Player dispatch, checkpoint binding and match execution were disabled during
  the audit. SHA-256 before/after checks confirmed all 71 files read were unchanged.
- Consequence: 2,878 saved decisions accepted in this bounded sample. No selected
  files were unavailable. No tracked saved decisions were found. Historical policy
  inference, other openings, the middle search budget, remaining search units and
  optional trace recordings were outside this audit sample.
  No broader historical compatibility or proof of recorded execution is inferred.
- Follow-up: retain originals; repository checks are recorded below.
- Review: not-required.

### 2026-09-10 — verification: shared validation implemented and checked

- Evidence: [`players/validation.py`](../../../src/qi/players/validation.py) now
  owns legality, common budgets, optional MCTS simulation/work/root accounting and
  search counters. Live `choose`, `EvalRun.validate_match` and search
  `check_choice` call it directly; duplicate diagnostic checks were removed.
  No player algorithms, result schemas, versions or charged-node semantics changed.
- Consequence: corrupt saved diagnostics fail without player execution or
  checkpoint binding. Tests cover valid JSON round trips, fresh MCTS/quiescent
  MCTS/enhanced-search evidence, simulation/root-visit and work totals, invalid
  root actions/values, exchange/cache/cutoff/extension counters, first-failure
  ordering, and unchanged `invalid_player_result` and referee transition errors.
  Existing MCTS tests now assert precise failure reasons instead of the old
  generic message. Ownership is documented in the player, evaluation and search
  guides; replay, identities, timing, protocol restrictions and outcomes remain
  with their existing owners.
- Verification: initial focused coverage passed 112 tests; the final focused
  evaluation/search/MCTS run passed 50 tests. `UV_NO_SYNC=1
  UV_CACHE_DIR=/tmp/qi-uv-cache make check` passed: 406 Python tests, one opt-in MPS
  skip, three web lifecycle tests, lint/format/docs/type checks and production
  browser build. Used installed dependencies because sandboxed `uv` sync could
  not access its default cache or fetch the build dependency; dependency/lock
  files were not changed. Final documentation and whitespace checks passed.
- Follow-up: none within this item; the audit limits above remain explicit.
- Review: not-required.
