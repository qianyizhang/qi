---
description: Accepted adjudication contract for the first qi training ruleset.
scope: xiangqi training adjudication
status: stable
last_update: 2026-09-21
document_class: coordination
---

# xiangqi-training-v1

This contract is implemented by `packages/qi-game/src/qi_game/reference.py` and verified by its colocated
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

## Move-generation implementation

The referee builds immutable piece destinations, rays and attack masks once at
import. Legal generation filters candidates by occupancy and updates a 90-bit
integer for each hypothetical move. King safety counts occupied squares along
potential attack paths, excluding captured attackers. `is_attacked` reuses the
inverse geometry for arbitrary targets, including empty squares used by positional
evaluation; `reaches` remains the direct geometry reference. The fast path
preserves the original source-square/target-square ordering, so fixed-budget
search behavior is unchanged. Colocated exhaustive
oracle tests cover both legal trajectories and arbitrary piece placements;
[AB-EVAL-007](../records/work-items/items/AB-EVAL-007-move-generation.md) records
equivalence controls and measured performance. The further data-structure study
is [AB-EVAL-008](../records/work-items/items/AB-EVAL-008-movegen-layout.md).
These implementation changes do not change the ruleset or repetition/ply-limit
adjudication.
