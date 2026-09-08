---
description: Quiescence as a budgeted MCTS leaf evaluator.
scope: quiescent MCTS player
status: stable
last_update: 2026-09-08
document_class: coordination
---

# MCTS with quiescent leaves

ID: `mcts-quiescence`. Version: `mcts-quiescence-v1`.

The [plain MCTS player](../mcts/README.md) scores material when a random rollout
stops. If that stop falls after a tempting capture but before its recapture, the
estimate can be misleading. This recipe uses [quiescence](../quiescence/README.md)
there, while keeping the existing UCT tree, random rollouts, and backup loop.

`tactical_value(game, budget)` searches captures up to two extra quiescence plies
when not in check. Checked positions always search legal evasions, even past that
cap. The referee still decides terminal outcomes. Nonterminal scores become
`score / (abs(score) + 900)`; forced mate scores map to ±1. These are heuristic
returns, not calibrated win probabilities. Two plies can still miss longer exchanges.

The MCTS `budgeted_leaf(Game, NodeBudget) -> float` hook receives an already charged
frontier and the same hard allowance as tree traversal and rollout. Every extra
quiescence visit is charged. If leaf search exhausts that allowance, the current
simulation is discarded without backing up a partial score; completed samples
remain. An expanded child can therefore have zero completed visits and a null
mean at the end of a decision.

`tree_visits + rollout_steps + leaf_nodes == nodes`. `leaf_nodes` counts additional
work, whereas `qnodes` also includes already-counted frontiers. `leaf_aborts`
is a subset of unfinished simulations. CLI JSON, arena summaries, and the browser
show the extra leaf work. More precise estimates compete with simulation count.

```bash
uv run qi choose --state game.json --player mcts-quiescence \
  --nodes 512 --rollout-plies 8 --seed 7
```

The default browser allowance is 512 nodes and eight rollout plies. Tests cover
a poisoned capture, discarded interrupted leaves, root statistics, and exact work
accounting. No model or training run is needed.
