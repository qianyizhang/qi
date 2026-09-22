---
description: Composable search components and their shared accounting contract.
scope: search composition
status: stable
last_update: 2026-09-21
document_class: coordination
---

# Build a player from small components

The [player contract](../README.md) owns selection and registration. These modules
are search ingredients: each has a small interface, its own explanation, and tests.
They do not own outcomes or update model weights.

| Component | Changes | Try it |
| :-- | :-- | :-- |
| [Ordering](ordering/README.md) | Which legal continuation is tried first | `alphabeta-ordered` |
| [Positional evaluation](positional/README.md) | How a nonterminal position is scored | `alphabeta-positional` |
| [Static exchanges](exchange/README.md) | Whether a capture should be tried late | `alphabeta-see` |
| [Check extensions](extensions/README.md) | Where to spend extra search plies | `alphabeta-checks` |
| [Transpositions](transpositions/README.md) | Reuse of compatible results and move hints | `alphabeta-tt` |
| [Quiescent MCTS leaves](../mcts_quiescence/README.md) | How MCTS estimates a tactical frontier | `mcts-quiescence` |

The [recipes](../enhanced/README.md) include `alphabeta-enhanced`, combining the
first five with quiescence. Start with one change and compare before stacking them.

## Composition in Python

```python
from functools import partial
from qi_game.reference import Game
from qi.players import PlayerConfig
from qi.players.alphabeta import SearchOptions, search
from qi.players.components.extensions import CheckExtensions
from qi.players.components.positional import evaluate
from qi.players.quiescence import quiesce

options = SearchOptions(
    evaluator=evaluate,
    ordering=True,
    exchange=True,
    extensions=CheckExtensions(2),
    table_capacity=2048,
)
result = search(
    Game(),
    PlayerConfig(depth=2, nodes=2048),
    leaf=partial(quiesce, evaluator=options.evaluator),
    options=options,
)
```

`SearchOptions` is an immutable recipe. Each call creates fresh ordering memory,
previous-best hints, and a bounded table; nothing leaks between games or players.
A custom leaf callback owns its evaluation, so pass the same evaluator into it
when combining positional scoring and quiescence. Register a new descriptor when
you want a named recipe in the CLI and browser; use a new version for changed
algorithm or budget semantics. Existing baseline IDs retain their behavior.

## One budget, several kinds of work

`nodes` counts ordinary visits, exchange-analysis transitions, and additional
quiescence visits, including abandoned work. A quiescence frontier was already
visited: `qnodes` includes it but never charges it twice. `see_nodes` is disjoint
from `qnodes`. Cache probes still require a charged position visit. Static score
calculation and ordering bookkeeping are not extra nodes; this is not a time cap.

`Choice.search_stats` exposes cutoffs, SEE visits, extension events/deepest path,
and cache hits/cutoffs. `Choice.evaluation` exposes the choosing side's **before-move
static assessment**, not a decomposition of the searched score. MCTS has separate
tree, rollout, and leaf work counters. The browser's **Last computer move** and
arena records expose these diagnostics. More mechanisms need not mean stronger
play at a small fixed budget.
