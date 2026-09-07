---
description: Baseline player contracts and replayable CLI matches.
scope: player and arena interface
status: stable
last_update: 2026-09-07
document_class: coordination
---

# Baseline players and matches

`src/qi/players.py` owns baseline behavior; `src/qi/arena.py` runs complete games.
The referee still owns legality and adjudication. These are educational baselines,
not trained models or claims of competitive strength.

## Players

`random-v1` uniformly samples a deterministically ordered legal-move list using
Python's seeded random generator. It reports zero search nodes and no score.
Python version is recorded because cross-version RNG behavior is not promised.

`alphabeta-material-v1` uses negamax alpha-beta and iterative deepening. Evaluation
is material plus a crossed-soldier bonus, always from the current player's view.
Terminal results are evaluated before depth cutoffs. Draws score zero; mate scores
prefer a shorter win or a longer loss. Scores are heuristic units, not probabilities.

Captures are ordered by victim value, then coordinate order; ties retain the first
move. The seed is recorded but does not change alpha-beta's deterministic ordering.
No transposition values are cached by board identity. Referee legal-move caching
is history-independent; outcome evaluation always uses the complete game history.

The default budget is depth 2 and 128 visited positions per move, shared across
iterations. Each visited root, internal position, terminal position, and leaf
counts as one node. Work in aborted iterations counts toward the budget. Reported
completed depth may be lower than requested depth. An incomplete iteration cannot
replace the last complete result. If none completes, return the first ordered legal
move, depth zero, and a null score. This fallback is explicit in the diagnostics.

This is a node budget, not a latency guarantee. Move generation and cached results
can change elapsed time without changing selected moves. Depth is limited to 1–8;
node budget must be positive. Random players ignore depth and node settings.

## CLI and artifacts

```bash
uv run qi new > game.json
uv run qi choose --state game.json --player alphabeta --nodes 128 --depth 2
uv run qi match --red alphabeta --black random --seed 7 > match.json
uv run qi match --red random --black alphabeta --seed 7 > reverse-match.json
uv run qi match --opening game.json --red random --black random > opening-match.json
```

`choose` is read-only and emits the move, input state hash, player version, seed,
visited nodes, completed depth, score, and measured milliseconds. Its state hash
can be passed to `qi apply` with the same snapshot.

`match` emits one JSON object with schema version 1, qi/Python versions, platform,
player configurations, opening, final snapshot, outcome, and per-turn diagnostics.
Extract the nested `snapshot` object to a JSON file for browser import or CLI replay.
The match record itself is not a snapshot.

Red's base seed is `--seed`; Black's is `--seed + 1`. Each decision uses its base
seed plus the absolute ply before moving, including opening plies. Repeated runs
with the same code, Python version, configurations, and opening reproduce moves
and outcomes; elapsed times need not match. Opening moves have no fabricated player
diagnostics. Terminal openings are rejected. Runs use the standard 300-ply ruleset
ceiling, including opening plies; there is no separate cutoff disguised as a draw.

## Fixed evaluation batches

`qi evaluate --corpus data/evaluation/openings-v1.json --seed 7` runs both color
assignments for every opening. `--player-a`, `--player-b`, `--depth`, and `--nodes`
configure the same baseline players. `src/qi/evaluation.py` owns batch behavior.
The four hand-authored histories are an engineering baseline, not a representative
strength benchmark. They carry an explicit evaluation-only purpose; future
training pipelines must exclude these histories and derived labels.

The schema validates every opening before any game starts, rejecting terminal or
illegal histories and duplicate IDs or identical full-history states. Equivalent
boards with different histories remain distinct. The artifact embeds the full
normalized corpus and its SHA-256; semantic corpus changes require a new corpus ID
and file version. The digest is over the normalized model JSON, not raw file bytes.

Each opening receives two games, A as Red then A as Black. For opening index i,
A uses the base seed plus 2i; B uses the base seed plus 1 plus 2i. Seeds follow
player identity when colors swap. Existing absolute-ply decision seeding still
applies. Records include complete individual matches and player-relative W/D/L,
termination reasons, decisions, total nodes, mean completed depth, and total/mean
latency. Different algorithms' node counts are reported, not presumed equivalent.

Every final snapshot is replayed before accepting its result. Invalid actions or
other failures abort the batch with structured stderr and no success JSON; they
are never scored as draws. Successful batches have zero invalid actions/retries.
Repeated runs reproduce games and results under the same code and Python version;
latency is observational. Outputs can be large; redirect to ignored `artifacts/`.
No Elo, statistical strength, teacher, or learned-policy fairness claim is made.
