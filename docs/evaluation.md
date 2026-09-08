---
description: Versioned paired-game evaluation specs, durable evidence, and replaceable scoring.
scope: performance evaluation contract
status: stable
last_update: 2026-09-08
document_class: coordination
---

# Performance evaluation

`src/qi/evaluation.py` owns three typed records and two ordinary functions:

| Boundary | Meaning |
| --- | --- |
| `EvalSpec` | Schema/protocol versions, embedded evaluation corpus, and both player configurations |
| `run_evaluation(spec)` → `EvalRun` | Bound spec/digest, code/environment/player identities, and every planned game slot |
| `summarize_evaluation(run)` → `EvalSummary` | Revalidated evidence, spec digest, completion status, and versioned per-player scores |

The referee determines results. Evaluation executes players; scoring never does.
There is no registry, base class, or aggregate mixing strength with compute cost.

## First protocol

`paired-games-v1` plays every corpus opening twice, swapping colors. A and B keep
their configurations across the pair. Opening index i adds 2i to each player's
base seed; decisions add the absolute ply. Configurations include node budget,
depth, rollout length, and any pinned checkpoint digest. Full history and the
ruleset travel in each opening. Different node counts are not equal compute.

`src/qi/scoring.py` owns the pure `score_pairs` function and `game-score-v1`:

- Score rate is `(wins + 0.5 * draws) / scored_games`, in [0, 1], from the named
  participant's perspective. Only complete color pairs contribute.
- Report planned/completed pairs, completed/failed/incomplete games, and completed
  games lacking a partner. No complete pair gives a null score, not zero.
- Mean move latency is decision-weighted over the same scored games, measured
  by untraced `choose`. No decisions gives null latency. Timing is observational.

Failed, interrupted, running, and pending games never become draws. A partial run
may have a score for completed pairs, but its status and denominators stay visible.
That subset may be biased; it does not establish a benchmark-wide result.

## Run now, summarize later

From the repository root:

```bash
uv run qi eval run --spec data/evaluation/paired-baseline-v1.json \
  --output artifacts/evaluation/baseline-v1
uv run qi eval summarize --run artifacts/evaluation/baseline-v1/run.json
```

The example embeds the existing four-opening engineering corpus, uses alpha-beta
versus random at depth 1 / 64 nodes, and schedules eight games. It is a smoke
benchmark, not representative playing-strength evidence.

Execution requires a fresh output directory and atomically saves `run.json`
before and after each game. It stops at the first failure or interrupt, preserves
finished games and the failed/interrupted slot, and exits nonzero. Preflight
errors precede execution evidence. An abrupt process death may leave a running
slot. Unfinished games have no move-by-move persistence in this protocol; search
experiments retain that richer recording. There is no resume or time control.

Summarization validates spec identity, planned slots, configurations, turn history,
player/checkpoint identities, basic budget/timing fields, and referee outcomes.
It needs no player execution or checkpoint loading. It does not reproduce timing,
prove heuristic diagnostics, or authenticate artifact authorship. Semantic protocol
changes require a new protocol ID; scoring changes require a new scorer ID.

## Existing paths and future additions

`qi evaluate` remains a compatibility command around this runner. Its old fields
remain and an `evaluation` field carries the new summary. Search experiment
reports use the same paired scorer and show score, planned/completed pairs, and
failures, while retaining their existing detailed probes and recordings.

Future confidence intervals and rating functions can consume retained game
evidence without repeating searches. Elo-like ratings additionally need a defined
opponent pool and reference scale. Position tests and time controls require their
own execution semantics when implemented. No rating or uncertainty estimate is
implemented yet.
