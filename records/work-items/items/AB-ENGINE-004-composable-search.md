---
description: Add six composable search improvements with isolated recipes and auditable work accounting.
scope: backlog item
status: stable
last_update: 2026-09-08
document_class: work_record
work_id: AB-ENGINE-004
work_status: done
work_kind: build
added: 2026-09-08
tags: domain
depends_on: AB-ENGINE-003
residual_of: none
residual_items: none
---

# AB-ENGINE-004 — Composable search improvements

## Intent

Implement the six techniques the user accepted: move ordering, positional
assessment, static exchange evaluation, bounded check extensions, history-safe
transposition tables, and MCTS with quiescent leaf evaluation. Keep mechanisms
readable and composable while preserving the existing baseline players.

## Acceptance Criteria

- Each mechanism has its own module, README, and focused tests.
- Previous-best, killer, and history ordering preserve legal action coverage;
  SEE handles Xiangqi screens and pinned recapturers and only affects ordering.
- Positional evaluation exposes material, placement, mobility, and king-safety
  contributions, with consistent side-to-move signs and color symmetry.
- Check extensions have a path-local allowance and share the global node budget.
- Cached bounds include remaining depth/extension context, normalize mate scores,
  and distinguish repetition and ply-limit contexts; incomplete results are not stored.
- SEE and quiescent MCTS leaves charge actual visits to the shared budget;
  interrupted leaf estimates never enter MCTS backup statistics.
- Explicit single-feature and combined recipes run through CLI, HTTP, browser,
  and replayable arena. Diagnostics explain extra work and root static terms.
- Controlled component comparisons, legacy tests, full repository checks,
  browser cases, and paired arena games pass or have honestly recorded outcomes.

## Context and Trade-offs

User authorized all six techniques and required well-structured composition.
SearchOptions is an immutable per-player recipe; move-ordering memory and tables
are created per decision. Existing baseline IDs retain their defaults. Six alpha-beta
recipes isolate each change and a combined positional/quiescent recipe; a seventh
player adds quiescence to MCTS. Components remain in-process with no training dependency.

SEE is a least-valuable-legal-recapturer estimate with optional stopping on one
square, not a tactical solver or pruning proof. Every capture examined by SEE is
charged. Positional terms are transparent hand-set heuristics, not tuned weights.
Extensions add at most two plies per path in the registered recipes (component cap
four). TT identity includes board, turn, current ply count, and all prior position
occurrence counts; order is irrelevant under this ruleset. This conservative key
can reduce reuse. Cutoff reuse requires the exact remaining horizon; other entries
only provide move hints. Each table holds at most 2048 entries and is local to a
single search recipe, so evaluator semantics cannot cross recipe boundaries.

The MCTS tactical leaf searches up to two quiescence plies in quiet positions;
checked positions continue through legal evasions under the global budget. A
budget exception discards the current simulation and preserves completed samples.
No material fallback silently replaces an unfinished tactical result.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-08 | Codex | — | wip | User authorized all six composable improvements |
| 2026-09-08 | Codex | wip | done | Six components, seven recipes, all checks and paired replay validation passed |

## Implementation Ledger

### 2026-09-08 — decision

- Evidence: the existing alpha-beta leaf callback, MCTS loop, immutable referee,
  catalog, and arena already provide the reusable boundaries.
- Consequence: extend those loops with per-search components instead of creating
  copied search implementations. Reserve hard work accounting for every simulated
  exchange/leaf transition; static evaluation terms remain heuristic computation.
- Follow-up: verify each feature in isolation, their composition, and every adapter.
- Review: not-required.

### 2026-09-08 — implementation and verification

- Evidence: [component guide](../../../src/qi/players/components/README.md),
  [alpha-beta recipes](../../../src/qi/players/enhanced/README.md), and
  [MCTS leaf recipe](../../../src/qi/players/mcts_quiescence/README.md) own the
  interfaces and learning explanations. Every mechanism has colocated tests.
  CLI/HTTP/catalog and both-color arena tests cover all seven registered recipes.
- Consequence: all accepted mechanisms are composable through shared search loops.
  The browser shows component work and root positional terms; arena summaries
  preserve corresponding totals. Original baseline decisions remain covered by
  their existing tests. No dependency or referee change was needed.
- Validation: `UV_CACHE_DIR=/tmp/qi-uv-cache make check` passed: 220 Python tests,
  three web request-lifecycle tests, Ruff, 56 governed Markdown files,
  TypeScript/Prettier, and production build. Optional learning tests ran with
  existing locked dependencies and hermetic fixtures. Existing FastAPI/Starlette
  dependency deprecation warnings remain.
- Browser validation: with the existing explicit local policy checkpoint,
  `QI_POLICY_CHECKPOINT="$PWD/artifacts/learning/policy-v1.pt" npm run test:e2e --prefix web`
  passed all 40 desktop/mobile cases, including all seven new recipes. Mobile
  combined-player screenshot inspected; diagnostic terms fit without overflow.
  E2E server used port 18765 and exited after the run.
- Controlled comparisons: four fixed corpus openings, all eight combinations of
  ordering/SEE/table, depth two, node ceiling 100000. All 32 searches completed
  and each opening retained its baseline score. Without SEE the four visit counts
  were 174, 183, 191, 178; with SEE they were 1922, 1051, 1092, 372. These positions
  showed no node saving from ordering/table at this depth. SEE changes branch
  order as well as charging exchange analysis; its larger total is not solely
  exchange-analysis overhead. Exhaustive sparse-position oracles additionally
  check component combinations and bounded check extensions.
- Paired batches: `qi evaluate --corpus data/evaluation/openings-v1.json`, seed 7,
  depth two, 512 nodes, eight rollout plies. Combined alpha-beta versus quiescence:
  **4 wins / 3 draws / 1 loss**, 870 total decisions; average completed depths
  1.484 and 1.645. Quiescent MCTS versus plain MCTS: **2 wins / 3 draws / 3 losses**,
  1139 decisions; 31927 extra tactical leaf visits and 216 discarded leaf estimates.
  An independent artifact pass applied every turn with its state hash, compared
  final snapshots/outcomes, checked seeds and budgets, and recomputed result/work
  summaries for all 16 games and 2009 decisions. Zero invalid actions or retries.
- Artifacts: ignored `artifacts/components/combined-vs-quiescence.json`,
  `mcts-leaves.json`, and `fixed-depth.json`; `compare.py` and `verify.py` in the
  same directory retain the local experiment/verification commands. Browser
  screenshots are under ignored `web/test-results/`.
- Limits: four openings are an engineering comparison, not a strength benchmark.
  The combined batch recorded 9982 cache hits but **zero cached cutoffs**; exact
  history/horizon identity currently provides mostly move hints. The handcrafted
  evaluator is untuned, SEE can reduce completed depth, and two-ply MCTS leaves
  still miss longer exchanges. These are documented recipe limitations.
- Follow-up: none required for this bounded implementation. Training experiments
  remain user-directed; this task did not produce or replace a user checkpoint.
- Review: local code/contract review and independent replay/accounting check;
  no separate reviewer agent.
