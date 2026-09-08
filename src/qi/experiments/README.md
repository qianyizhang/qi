---
description: Plan, run, verify, compare, and inspect bounded local search experiments.
scope: search experiment evidence and reports
status: experimental
last_update: 2026-09-08
document_class: coordination
---

# Search experiments

Experiments configure comparisons and preserve evidence. Players choose moves;
the referee owns legality and outcomes; reports are derived views. This module
is provisional, local, synchronous, and search-only.

## Run and inspect

From the repository root:

```bash
uv run qi experiment preview --plan data/experiments/search-components-v1.json
uv run qi experiment run --plan data/experiments/search-components-v1.json \
  --output artifacts/experiments/search-v1 --seconds 600
uv run qi experiment verify --run artifacts/experiments/search-v1
uv run qi experiment report --run artifacts/experiments/search-v1 \
  --output artifacts/experiments/search-v1/report.html
```

Open the HTML locally: no server, network, or external assets. Filter recipes and
budgets, inspect boards and move diagnostics, and read the plan/provenance. The
report provides a command for tracing the selected saved decision:

```bash
uv run qi experiment inspect --run artifacts/experiments/search-v1 \
  --unit unit-00007 --turn 0 \
  --output artifacts/experiments/search-v1/traces/combined.json
uv run qi experiment report --run artifacts/experiments/search-v1 \
  --output artifacts/experiments/search-v1/report.html
```

Runs and traces require fresh paths; reports may be regenerated. There is no
resume, scheduling, database, or publication. A deadline is an incomplete result;
errors/interrupts save available evidence and produce a nonzero CLI exit.

## Plans and persistence

`model.py` owns schema v1: embedded corpus, recipes, visit budgets, seeds, depth,
rollout length, matchups/openings, and optional immediate-win targets. Targets
must list every legal immediate win, exhaustively checked by the referee.
The first tracked plan embeds a frozen copy of the reserved corpus; a test checks
their agreement. Its 12 positions, 10 recipes, three budgets, and one seed produce
360 probes and 24 paired games. Six midgame prefixes and two immediate-win
positions come from earlier local matches; four original openings are retained.
This is selected engineering coverage, not representative strength evidence.

Future training must use `data/evaluation/search-positions-v1.json` as its reserved
corpus, including all history-prefix board/turn inputs. Older datasets do not
automatically reserve these new positions. This module changes no training data
or weights.

| Run file | Meaning |
| --- | --- |
| `manifest.json` | Immutable plan/digests, player versions, source digest, Git state, Python/package/platform identity, allowance |
| `units/unit-NNNNN.json` | Exact job, recorded turns, final snapshot, status; outcome only for a completed game |
| `status.json` | Observed run state; completion counts are re-derived from units |
| `traces/*.json` | Optional inspected decisions linked by source/unit digests |
| `report.html` | Regeneratable offline projection |

`runner.py` atomically saves each started unit and every decision. The allowance
starts after preflight and is checked before decisions; one bounded search can
finish past it. It is elapsed wall time, not a hard CPU quota. A crashed process
may leave `running` status; the report still shows partial evidence. Incomplete
games never receive an inferred draw. Temporary unfinished writes are ignored.

`evidence.py` replays every turn and checks state, side, seed, version, budgets,
diagnostics, snapshots, and outcomes. `report.py` recomputes comparisons from raw
units. Code identity hashes Python/report assets under `src/qi`, plus project and
lock files; Git state is additional context. Hashes identify content, not
authorship or tamper-proof signatures. Replay cannot reproduce measured timing.

## Reading results

- Probe counts show the planned denominator. Partial matrices may sample uneven
  positions: inspect matching positions before inferring a gain. Only the named
  immediate-win targets have best-move ground truth; changed scores are not proof.
- Outcome totals use complete color pairs with identical opening/configurations.
  Missing partners and incomplete games remain outside these totals. There is no
  universal winner ranking, Elo estimate, or general strength claim.
- Latency surrounds untraced `choose`, including validation, excluding file writes.
  Recipes run in fixed order with shared referee caches; these observations are
  not isolated speedup measurements. Equal visits are not equal compute. Depth is ordinary alpha-beta depth, not an
  MCTS metric. Static score breakdowns describe the position before the move.
- Score timelines show one player's side-to-move values at a time. MCTS estimates
  are not calibrated win probabilities. Work columns are not additive: quiescence
  frontiers can overlap MCTS tree/rollout work. Its disjoint accounting remains
  tree visits + rollout steps + extra leaf visits.

## Optional explored-tree recording

`players/trace.py` is an observational, context-local recorder. Small hooks emit
event kinds and parent references from the existing algorithms. There is no
alternate search engine or persistent global trace.

Alpha-beta records iterations, bounds, ordering, pruning, cache use, extensions,
quiescence, and exchange analysis. MCTS records simulation selection/expansion,
rollouts, leaves, backups, and its final retained tree with visits, values, and
unexpanded moves. Repeated visits are separate execution events; the retained
MCTS tree has its own view. Exchange analysis is board-only heuristic work,
not a referee-adjudicated trajectory. Unsearched branches get no invented score.

The default capacity is 100000 events, configurable up to 1000000. Capacity stops
recording only; search remains unchanged. Omitted events make the recording
explicitly incomplete. An interrupted search can have a complete recording of
everything it actually explored. The viewer expands lazily and pages siblings.

Inspection requires the original source digest and Python/package versions, then
checks the move and every deterministic diagnostic against the saved untraced
choice. Trace timing stays separate. Validation checks parent ordering and all
charged visits; it does not independently prove each heuristic score.

## Beginner guide and glossary

The offline report includes a reading guide, dotted-underlined term explanations
(hover, keyboard focus, or tap), and a searchable English/Chinese glossary.
Escape or a click outside dismisses help. JSON field annotations preserve copied
text; visits in MCTS node records are distinguished from charged-work visits.

Definitions and field aliases come from `docs/glossary/ddd.md`, the vocabulary
authority, read from this checkout when generating the report. Add new report
terms there. The embedded glossary records its own digest independently of the
original run's provenance. Regenerating an existing report updates its help
without changing saved experiment evidence or rerunning searches.

## Checks

`make check` covers trace parity/accounting, deadlines, failures, altered evidence,
corpus/plan boundaries, HTML escaping, and existing player/adaptor behavior.
`npm run test:e2e --prefix web` also checks report controls, board/tree inspection,
and mobile layout using temporary hermetic runs. Those report cases need no
teacher or learning dependency.
