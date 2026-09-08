---
description: Add inspectable UCT search with bounded random rollouts and no learned dependency.
scope: backlog item
status: stable
last_update: 2026-09-08
document_class: work_record
work_id: AB-ENGINE-003
work_status: done
work_kind: build
added: 2026-09-08
tags: domain
depends_on: AB-ENGINE-002
residual_of: none
residual_items: none
---

# AB-ENGINE-003 — Plain MCTS player

## Intent

Build a readable, playable UCT implementation while the user experiments with
training independently. Preserve referee ownership and the shared player catalog.

## Acceptance Criteria

- A named mcts player performs selection, expansion, seeded random rollout, and
  alternating-perspective backup; final choice uses root visit counts.
- A shared hard work budget covers tree and rollout visits, with no uncharged
  simulated transitions. Full history remains available to referee adjudication.
- Actual terminal outcomes take precedence over a bounded heuristic cutoff.
- A small replaceable leaf evaluator supports future experiments without adding
  trained-model or teacher dependencies.
- Root moves report visits and mean estimated return, including unvisited moves;
  diagnostics reach CLI, arena records, and the browser.
- Tests cover perspective, terminal/repetition semantics, deterministic seeds,
  low budgets, and integration. Full games replay under the existing ruleset.
- The module README explains the algorithm, accounting, and limitations.

## Context and Trade-offs

User explicitly approved plain MCTS, bounded rollouts, diagnostics, and adapter
integration. UCT uses exploration constant sqrt(2), node values from that node's
side-to-move perspective, and negated child means during selection. Expansion
order is seeded and shuffled. Final root selection uses visits, then root-relative
mean, then coordinate order. No transposition merging or tree reuse between moves.

The existing nodes setting counts the root once per simulation, every visited tree
child (including reused children), and every rollout successor. Defaults for the
browser are 512 visits and eight rollout plies; CLI retains its explicit shared
nodes default and gains rollout-plies (0-64). Ordinary alpha-beta depth has no MCTS
meaning. Budget exhaustion below the root uses the current heuristic estimate;
an iteration unable to leave the root is uncompleted and contributes no backup.

Terminal values are +1/-1/0 from the current side's perspective. Nonterminal leaf
values use material / (abs(material) + 900), explicitly an estimate, not a win
probability. The leaf callback must return a finite value in [-1, 1]. Root mean
values are always from the choosing player's perspective. No training changes.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-08 | Codex | — | wip | User authorized the proposed independent search slice |
| 2026-09-08 | Codex | wip | done | Full checks, browser inspection, and 16 paired replayable games passed |

## Implementation Ledger

### 2026-09-08 — decision

- Evidence: existing immutable Game, shared material heuristic, player catalog,
  and replayable arena already provide the surrounding boundaries.
- Consequence: implement one concrete player with a leaf callback; retain budget
  and rollout diagnostics instead of adding a speculative generic search framework.
- Follow-up: validate sign conventions, history, bounded accounting, and adapters.
- Review: not-required.

### 2026-09-08 — verification

- Evidence: `make check` passed with 158 Python tests, three request-lifecycle
  unit tests, documentation/lint/type/format checks, and the production build.
  New tests cover UCT exploration and opponent perspective, alternating backup,
  terminal precedence, repetition during rollout, forced one-move wins, seeded
  reproducibility, evaluator bounds, root coverage, and exact low-budget accounting.
  CLI/HTTP diagnostics agree, invalid rollout limits and inconsistent statistics
  fail explicitly, and paired arena JSON preserves root statistics and summaries.
- Evidence: all 26 desktop/mobile Playwright cases passed, including the existing
  learned-policy path and the new MCTS diagnostics. The MCTS case checks all 44
  initial legal root moves, exactly one highlighted selection, simulation counts,
  and no horizontal overflow. The mobile screenshot was visually inspected.
- Evidence: eight paired-color games against random over qi-openings-v1, seed 7,
  with 512 visits and eight rollout plies yielded MCTS W/D/L = 8/0/0. MCTS used
  141,312 visits, 13,991 simulations, and 110,397 rollout steps; 74 simulations
  reached terminal outcomes and 13,917 used heuristic cutoffs. Maximum tree depth
  was two. Mean measured decision latency was 165.32 ms in that run.
- Evidence: eight paired-color games against alpha-beta with the same nodes
  allowance, alpha-beta depth two, and otherwise identical settings yielded
  MCTS W/D/L = 0/1/7. MCTS used 257,536 visits, 24,699 simulations, and 189,874
  rollout steps; 1,129 simulations reached terminal outcomes, 23,570 used cutoffs,
  and maximum tree depth was three. Mean measured decision latency was 100.95 ms
  versus alpha-beta's 25.10 ms. Node costs and cache conditions differ by algorithm;
  these timings are observations, not a controlled performance benchmark.
- Evidence: every turn guard, legal root-move set, root-visit sum, and work-budget
  total was independently checked for all 16 games. Final snapshots and outcomes
  replayed exactly, with no illegal actions or retries. Full records remain in
  ignored artifacts/mcts/vs-random.json and artifacts/mcts/vs-alphabeta.json.
- Consequence: the standalone educational MCTS player is usable and inspectable.
  Random rollouts with material cutoffs remain weak against the existing tactical
  baseline in this sample; no general strength claim is warranted. The replaceable
  leaf evaluator is available without coupling the search to training.
- Follow-up: none required for this slice. Learned priors/value integration and
  PUCT remain later experiments; the user's training implementation was untouched.
- Review: not-required.
