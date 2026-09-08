---
description: The pluggable player contract and a reading guide to the engine modules.
scope: player architecture and extension
status: stable
last_update: 2026-09-08
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
| [Learned policy](policy/README.md) | Board encoding, legal masking, and checkpoint-backed inference |

## One extension point

Every module exports `PLAYER`, a `Player` descriptor with `PlayerInfo` and a
`select(game, config) -> Decision` callable. `core.py` defines the interface;
`catalog.py` explicitly registers implementations. There is no filesystem scan,
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
hash, player version, seed, and measured elapsed time. The referee still owns
outcomes and transitions. Callers apply the result with the returned state hash.

## Shared mechanics without a framework

`common.py` holds the existing material evaluator, deterministic move ordering,
terminal score conversion, and node counter. Alpha-beta exposes a small leaf
callback; quiescence plugs into it, sharing the search loop and budget. No search
value cache is keyed by board alone: repetition and the ply ceiling need history.

`Decision` reports total nodes, completed ordinary depth, score, and optional
quiescence diagnostics, model calls, and checkpoint identity. `Choice` adds
provenance. Learned-policy encoding and inference budgets are documented in its
module; training stays in the [trainer](../learning/README.md).
See [runtime contracts](../../../docs/baselines.md)
for serialization, seeding, and evaluation limits.
