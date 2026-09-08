---
description: How quiescence search looks through exchanges before evaluating a position.
scope: quiescence player
status: stable
last_update: 2026-09-08
document_class: coordination
---

# Quiescence: wait for the exchange to settle

ID: `quiescence`. Version: `alphabeta-quiescence-v1`.

The normal search depth is a stopping point we chose, not a guarantee that the
position is ready to evaluate. **Quiescence search** extends the leaf through
captures and, when in check, every legal evasion before assigning a score.

Consider the initial Xiangqi position:

```text
Red cannon b2 -> b9, taking a horse       Red material gain: +400
Black rook a9 -> b9, taking that cannon  Red net material:   -50
```

The original depth-one player stops after the first line. This player can see the
second. At 128 total nodes, the initial-position regression chooses a quiet move
with score zero instead of that cannon capture. This demonstrates the particular
horizon repair, not overall playing strength.

## The algorithm

At the ordinary search frontier:

1. Honor the referee's terminal outcome first, including history-dependent draws.
2. If in check, search **all legal evasions**, including non-captures. Evaluating
   the board as though the player could ignore check is forbidden.
3. Otherwise use the current material score as a **stand-pat** baseline and
   search legal captures that might improve it. Stand pat is a search estimate;
   it is not a legal pass move and can be inaccurate in zugzwang positions.
4. Repeat from the opponent's perspective, using alpha-beta bounds to prune.

There is no extra pool of free nodes. Ordinary and quiescence search share the
same hard budget, including abandoned iterations. The frontier is counted once,
even though it is also included in `qnodes`. `max_qply` is the deepest number of
extra plies beyond a frontier across all attempted work. `completed_depth` remains
ordinary iterative-deepening depth, not the combined depth of a selective branch.

Budget exhaustion interrupts the whole current iteration. It never invents a
quiet evaluation while in check. The last completed move survives; if none
completed, the original explicit depth-zero fallback applies. Repetition and the
300-ply ruleset also bound continuations; no board-only result cache is used.

## Read and try it

`select()` in `__init__.py` supplies `quiesce` to the existing alpha-beta search.
`test_quiescence.py` covers the recapture, quiet check evasion, exact node counting,
terminal history, and interrupted-iteration contracts.

```bash
uv run qi choose --state game.json --player quiescence --depth 2 --nodes 128
uv run qi evaluate --corpus data/evaluation/openings-v1.json \
  --player-a quiescence --player-b alphabeta --depth 2 --nodes 128 --seed 7
```

The browser catalog suggests 512 nodes for this player; original alpha-beta keeps
128. Use equal explicit budgets for comparisons. Extra tactical work can reduce
completed ordinary depth, so adding quiescence does not guarantee stronger play.
Quiet threats, positional planning, learned evaluation, and selective pruning
beyond alpha-beta remain outside this implementation.

For a production-engine example of entering quiescence at depth zero, see
[Stockfish's search entry](https://github.com/official-stockfish/Stockfish/blob/master/src/search.cpp).
Qi's implementation is small and independently written for its own ruleset.
[Parent contract and extension guide](../README.md).

`quiesce` also accepts an `evaluator` callback and optional `max_plies` cap for
non-check frontiers. The original player leaves that cap unset;
[MCTS quiescent leaves](../mcts_quiescence/README.md) use two. Checked positions
always continue through legal evasions under the global budget, even past a cap.
