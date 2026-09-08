---
description: A readable UCT player with bounded random rollouts and inspectable root statistics.
scope: MCTS player and extension contract
status: stable
last_update: 2026-09-08
document_class: coordination
---

# MCTS: search by repeated simulation

ID: `mcts`. Version: `mcts-uct-v1`.

MCTS builds a tree by sampling continuations. Each simulation follows promising
or underexplored branches, adds one new child when possible, plays some random
moves, and updates the visited nodes. This implementation uses UCT for selection,
following the [original UCT paper](https://sites.ualberta.ca/~szepesva/papers/ecml06.pdf).
It needs no teacher, checkpoint, training library, or network connection.

## Follow one simulation

1. **Select.** Start at the root. At a fully expanded node, choose a child using
   its estimated value and an exploration bonus. The opponent also seeks its own
   advantage; we do not assume it helps the root player.
2. **Expand.** Take one untried legal move and retain its complete immutable Game.
   Each node's expansion order is shuffled by the per-decision seeded RNG.
3. **Roll out.** Play uniformly random legal moves, up to the configured limit.
   The referee checks terminal outcomes, including repetition, after every move.
4. **Back up.** Add one visit and the estimated return to each node on the tree
   path. Reverse the sign at each parent because the side to move alternates.

Every node stores values from **its side-to-move perspective**. Selection maximizes:

```text
-child.mean_value + sqrt(2 * log(parent.visits) / child.visits)
```

The minus sign converts the child's estimate to the parent's perspective. Every
child has a completed sample before it participates in UCT selection. The final
move has the most root visits, breaking ties by root-relative mean and then
coordinate order. This final selection does not include the exploration bonus.

## Where the values come from

Actual terminal results give +1 for a win, -1 for a loss, and 0 for a draw.
At a nonterminal cutoff, use the existing material-and-soldier heuristic:

```text
material / (abs(material) + 900)
```

For example, a +900 material advantage becomes +0.5. This is a bounded heuristic
estimate, not a 75% win probability. Reaching a rollout or work limit never turns
an unfinished game into a referee draw. In-check cutoffs can still use this naive
heuristic; this first MCTS version has no quiescence extension.

## Budgets and diagnostics

```bash
uv run qi new > game.json
uv run qi choose --state game.json --player mcts --nodes 512 --rollout-plies 8 --seed 7
uv run qi match --red mcts --black random --nodes 512 --rollout-plies 8 --seed 7
uv run qi evaluate --corpus data/evaluation/openings-v1.json \
  --player-a mcts --player-b alphabeta --nodes 512 --rollout-plies 8 --seed 7
```

The browser catalog defaults to 512 visits and eight rollout plies. CLI commands
retain their shared 128-visit default, so set `--nodes` explicitly for comparisons.
`--rollout-plies` allows 0-64; zero evaluates expanded leaves immediately. Ordinary
alpha-beta `--depth` is ignored by MCTS, and completed_depth remains zero.

The hard `nodes` allowance counts:

- One root visit each time a simulation starts.
- Every tree-child visit, including revisiting a stored child.
- Every successor reached during a random rollout.

A transition is charged before applying the move. Cutoff evaluation uses an already
visited position. The same allowance covers all simulations; it is not a memory,
unique-position, or wall-clock limit. Legal move generation and leaf evaluation
have costs that vary by position. Node counts across algorithms are not equivalent
amounts of computation.

If the budget ends below the root, the current position supplies a valid cutoff
estimate for backup. If it ends before leaving the root, that unfinished simulation
adds no visits or values to the statistical tree. With no completed simulation,
choose the first coordinate-sorted legal move and report all means as null.

`Choice.mcts` records completed simulations, tree visits, rollout steps, terminal
results, rollout-length cutoffs, work-budget cutoffs, unfinished simulations, and
maximum tree depth. Tree visits plus rollout steps equal the reported total nodes;
root-child visits sum to completed simulations. If both limits are reached at once,
classify a nonterminal result as a rollout-length cutoff; terminal outcomes always
win precedence.

The root table includes every legal move. Unvisited moves have zero visits and a
null mean. All displayed means belong to the choosing player, regardless of color.
CLI/match JSON retains the full table. In the browser, open **Last computer move**
to inspect the sorted table and highlighted selection. Batch summaries aggregate
simulation work and maximum tree depth; per-turn records keep the detailed counts.

## The extension point

`search(game, config, leaf=material_value)` accepts a callable `Game -> float`.
The callback evaluates a nonterminal position from its side-to-move perspective
and must return a finite value in [-1, 1]. Terminal outcomes bypass the callback.
Use `choose()` for ordinary public dispatch; the lower-level `search()` seam is
for implementing and testing another player variant.

The tree stores full histories and is rebuilt for each decision. There is no
board-only transposition merging, tree reuse, policy prior, or model inference.
A future value model can replace the leaf callback; PUCT will additionally need
policy priors and explicit model-call accounting. Those changes belong to a later
player version. Current random rollouts and material cutoffs are deliberately
simple; a working tree search does not imply superiority to alpha-beta.
