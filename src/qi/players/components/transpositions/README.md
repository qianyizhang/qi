---
description: History-aware bounded cache keys and search bounds.
scope: transposition tables
status: stable
last_update: 2026-09-08
document_class: coordination
---

# Transposition tables: reuse compatible search work

Different move sequences can reach the same board. A **transposition table** keeps
a searched score, its best move, and whether that score is exact, a lower bound,
or an upper bound. A compatible bound can answer a later visit immediately.

Board identity alone is unsafe here: repetition and the 300-ply ceiling affect
outcomes. `position_key(game)` includes the ruleset, actual board, side to move,
current ply count, and occurrence counts of **all** historical positions. History
order is irrelevant under this referee's rules. This deliberately conservative
key often prevents reuse between visually identical boards.

Each entry includes effective remaining depth and remaining check-extension
allowance. Cutoffs require both to match exactly, preserving fixed-depth evaluator
semantics; other entries supply move hints only. Mate scores are normalized on
storage and restored relative to the probing ply. Terminal outcomes are always
checked first. Interrupted nodes never store unfinished results; completed bounds
from their children remain valid.

Tables are created per decision and stay within one evaluator/leaf recipe. The
registered `alphabeta-tt` and combined recipes keep at most 2048 entries, evicting
the oldest stored entry. Every reused position still costs one node. A cache hit
can be only a move hint: inspect `tt_cutoffs` separately from `tt_hits`.

Tests cover repetition/ply context, exact and bound entries, horizon mismatches,
mate-distance conversion, capacity, interrupted nodes, and charged repeated reuse.
At shallow depth this key may yield no cached cutoffs; no speedup is assumed.
