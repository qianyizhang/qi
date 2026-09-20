"""Coarse replay operations, independent of a backend's internal representation."""

from typing import Protocol

from qi_game.contracts import Position, Snapshot


class Referee(Protocol):
    """Implement xiangqi-training-v1 exactly; return fresh results without mutating input.

    Replay the entire snapshot before inspecting or applying a guarded action.
    Preserve ordered legal moves, history-sensitive outcomes and state hashes.
    Invalid actions raise GameError; apply checks stale state before move validity.
    Resource ownership and batching belong to the workload that introduces them.
    """

    def inspect(self, snapshot: Snapshot) -> Position: ...

    def apply(self, snapshot: Snapshot, move: str, expected_hash: str) -> Position: ...
