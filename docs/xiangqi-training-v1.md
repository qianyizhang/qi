---
description: Accepted adjudication contract for the first qi training ruleset.
scope: xiangqi training adjudication
status: stable
last_update: 2026-09-07
document_class: coordination
---

# xiangqi-training-v1

This contract is implemented by `src/qi/game.py` and verified by its colocated
tests. [ADR-0002](adr/0002-version-simplified-training-adjudication.md)
owns the trade-off rationale.

## Adjudication

- Ruleset identity: `xiangqi-training-v1`.
- Implement ordinary piece movement and king safety. A side with no legal move
  loses, whether or not its king is in check.
- After each legal move, evaluate ordinary terminal outcomes before either
  automatic draw condition below.
- Draw on the third occurrence of an identical piece placement and side to move
  within the game's history. Count the initial position as its first occurrence.
  Occurrences need not be consecutive. Check/chase history does not alter this
  repetition decision; repeated checking or chasing can therefore produce a draw.
- Draw when 300 legal plies have been played from the recorded initial position.
  One ply is one player's move. Invalid actions do not advance this counter.
- Both draw conditions are automatic. If both occur on the same move, the result
  is still a draw; diagnostics may report both conditions.

## Replay and evolution

Retain the initial position, ordered legal moves, and ruleset identity. Replay
must reproduce side to move, repetition counts, ply count, and outcome.
Current-board/FEN input alone cannot restore a history-dependent game.

Changes to these adjudication semantics require a new ruleset identity. Preserve
this version for interpreting its saved games and experiment results.

## Interfaces and movement reference

[Interface](interface.md) owns coordinates and snapshots; the referee owns move
generation. Piece-movement behavior was checked against
[Xiangqi.com’s piece guide](https://www.xiangqi.com/help/pieces-and-moves)
and sampled against pyffish. Those references do not own this simplified
adjudication policy.
