---
description: The pluggable player contract and a reading guide to the engine modules.
scope: player architecture and extension
status: stable
last_update: 2026-09-10
document_class: coordination
---

# Players: the learning surface

A **player** answers: “Given this game and budget, which move do I choose?”
The [glossary](../../../docs/glossary/ddd.md) owns the terminology. Search
explores continuations; an evaluator scores positions; a policy maps states to
action preferences/probabilities. Tactics and strategy describe play, not module
interfaces. Human players use the board; this package implements automated players.

Read these implementations in order:

| Module | What it teaches |
| :-- | :-- |
| [Random](random/README.md) | Seeded decisions and the legal-move boundary |
| [Alpha-beta](alphabeta/README.md) | Alternating perspectives, pruning, iterative deepening |
| [Quiescence](quiescence/README.md) | Looking beyond an exchange at the normal search horizon |
| [MCTS](mcts/README.md) | UCT exploration, random rollouts, value backup, and root visits |
| [Search components](components/README.md) | Ordering, positional scores, exchanges, extensions, and safe caching |
| [Combined recipes](enhanced/README.md) | Assemble and compare alpha-beta ingredients |
| [Quiescent MCTS](mcts_quiescence/README.md) | Budget tactical leaf work alongside simulations |
| [Learned policy](policy/README.md) | Board encoding, legal masking, and checkpoint-backed inference |

## One extension point

An implementation exports a `Player` descriptor with `PlayerInfo` and a
`select(game, config) -> Decision` callable. `core.py` defines the interface;
`catalog.py` explicitly registers implementations (`PLAYER`, or `PLAYERS` for recipes). There is no filesystem scan,
SDK dependency, class hierarchy requirement, or arbitrary executable loading.
The local teacher stays outside this catalog so evaluated players do not gain
teacher access implicitly.

Checkpoint-backed players can additionally expose a checkpoint-digest callable
and an availability predicate. The shared boundary pins the digest, and the
catalog uses these hooks to expose configured players without adapter allowlists.

```python
from qi.game import Game, legal_moves
from qi.players import Decision, Player, PlayerConfig, PlayerInfo


def select(game: Game, config: PlayerConfig) -> Decision:
    return Decision(legal_moves(game.board, game.turn)[0])


PLAYER = Player(
    PlayerInfo("first-legal", "first-legal-v1", "First legal", "A tiny example.", False),
    select,
)
```

To add a player:

1. Create a subpackage with `__init__.py`, a short README, and colocated tests.
2. Export its descriptor and add it to the explicit catalog.
3. Run `make check`; compare it with another player through `qi evaluate`.

The CLI (`qi players`) and HTTP (`GET /api/players`) expose catalog metadata. The
browser fetches that metadata; selection, arena, and evaluation dispatch through
the same catalog. Adding an implementation requires no consumer-specific branch.
IDs are stable configuration keys; versions identify algorithm semantics. Change
a version when changing decisions or budget semantics. Unknown IDs fail at lookup,
not when constructing the transport-neutral `PlayerConfig` record.

`choose()` is the public boundary: it rejects terminal games, dispatches the
player, validates move legality and budget diagnostics, then attaches full-state
hash, player version, seed, and measured elapsed time.
[`validation.py`](validation.py) owns pure legality, common budget, MCTS accounting,
root-visit/value, and search-counter checks for both `Decision` and `Choice`.
Live selection, arena evaluation and search evidence call it directly. It raises
`ValueError` at the first failed invariant with a specific reason; live selection
translates that to `GameError("invalid_player_result", ...)`. Callers retain
identity, timing, protocol and replay checks, including referee transition errors.
Optional statistics are checked only when present. Validation does not execute
players, load checkpoints, prove that recorded work occurred, or repair evidence.
The referee still owns
outcomes and transitions. Callers apply the result with the returned state hash.

## Shared mechanics without a framework

`common.py` holds the existing material evaluator, deterministic move ordering,
terminal score conversion, and node counter. Alpha-beta exposes a leaf
callback and immutable `SearchOptions`; [components](components/README.md) plug
into its search loop and budget. MCTS exposes both static and budgeted leaf callbacks. No search
value cache is keyed by board alone: repetition and the ply ceiling need history.

`Decision` reports total nodes, completed ordinary depth, score, and optional
quiescence diagnostics, MCTS/search statistics, root evaluation terms, model calls,
and checkpoint identity. `Choice` adds
provenance. Learned-policy encoding and inference budgets are documented in its
module; training stays in the [trainer](../learning/README.md).
See [runtime contracts](../../../docs/baselines.md)
for serialization, seeding, and evaluation limits.
