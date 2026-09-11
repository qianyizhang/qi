---
description: Decision handoff for comparing Pikafish move-value evaluation with teacher top-1 agreement.
scope: session handoff report
status: experimental
last_update: 2026-09-12
document_class: coordination
produced_by: "handoff@0.9.0 · agent=GPT-6 · effort=unspecified · 2026-09-12"
---

# Session handoff — Evaluation metric comparison

**Mode:** DECIDE; single-writer session handoff.
**Authorized transitions:** inspect evidence and settle the protocol. No next
experiment execution has been authorized by this planning request.
**Stop condition:** the material decisions, evidence plan, runtime allowance
and next-session execution boundary are explicit in the owning work item.

## Authorities

- Campaign: [policy generalization](../campaigns/policy-generalization.md).
- Primary owner: [AB-LEARN-015](../work-items/items/AB-LEARN-015-evaluation-metric-comparison.md).
- Method: [experiment lifecycle](../../docs/experiments.md).
- Prior metric evidence: [AB-LEARN-009](../work-items/items/AB-LEARN-009-teacher-quality.md).
- Completed studies and storage: [session closeout](generated-data-session-closeout-20260912.md),
  [model inventory](../../data/experiments/learning/generated-model-retention-20260912.json).
- Game-outcome authority if selected: [benchmark contract](../../docs/benchmark.md)
  and the referee; local ratings are conditional on the frozen player panel.

## State

- Done: generated-source mixing, matched immediate-tag enrichment and nested
  data scaling are complete through `a9a92fa`; closeout and model-retention audit
  are committed as `42903ad`. No next-study engine search, game or training fit
  has started. The five unrelated generation files named in the closeout remain
  outside this session's commits.
- Left: finish the interview, then write and register the agreed protocol before
  its implementation or execution. Use saved model predictions where possible.
- Verification: all 89 final checkpoint hashes match their reports; configs and
  predictions are retained. The 84 comparison fits contain 75 distinct tensor
  states and 75 distinct development move vectors. Nine natural semantic
  controls repeat the source-mixing `both` models. Pilots and earlier failed-run
  controls remain evidence but are not extra scientific model observations.
- Data: all retained runs share 373 development inputs across six source/phase
  cells (five cells of 64, intervention endgame 53). The in-check slice has 35
  positions, including 13 with only one legal move. All 3900 sealed inputs remain
  unscored. Existing development scores have informed training choices.

## Open questions — Round 1 pending

These recommendations were presented to the user, not yet accepted:

| Decision | Recommendation | Alternative |
| --- | --- | --- |
| Meaning of effectiveness | Compare metric rankings over saved models, then validate a small, preselected model panel against paired game outcomes | Metric comparison only; defer strength validation |
| Evaluation pools | Use the 373 development positions and development opening book; preserve both sealed pools | Allow sealed confirmation after the protocol is frozen |
| Runtime allowance | Two hours cumulative experiment runtime, including calibration and failed attempts; gate final size on measured cost | Thirty-minute pilot only, or four-hour ceiling |

After these settle, recompute the interview frontier. Model-panel size and game
schedule depend on the selected purpose and runtime allowance. Reference search
allocation, primary/supporting metrics, uncertainty/decision criteria and the
next session's authorized transitions still need an explicit protocol. Do not
treat prior approval of the completed data studies as approval of this new one.

## Implementation pointers and interpretation

[Candidate assessment](../../src/qi/learning/teacher_quality_scores.py) already
extracts the deepest complete same-depth all-legal MultiPV set with exact UCI
score bounds and WDL output. `disadvantage()` computes the difference between
the best and selected move's expected score, where Q = (W + 0.5 D) / 1000. It
keeps absent support unknown and separates centipawn gaps from mate values.
Exact here describes the engine's search bound, not perfect game-theoretic value.

The pinned engine/network are in
`data/teachers/pikafish-2026-01-02.json`. Pikafish's `searchmoves` capability was
verified by a shallow local one-move root probe, but the generic adapter does
not currently expose it. The probe establishes command support only. Reuse the
existing all-legal assessment path if it meets the selected protocol; adding a
restricted-root path is a separate implementation choice.

Keep the original 100k-label agreement distinct from agreement with any newly
queried reference. MultiPV shares its budget across candidate moves; a larger
total budget is not automatically deeper per move. Freeze board/history,
perspective, engine/network, thread/hash settings, reset behavior and budget;
record actual depths and incomplete/bounded results. A separate single-PV
reference and a budget-stability check may diagnose disagreements. Do not
assume WDL is calibrated to these students or pool mate distances as centipawns.

Use per-position severity and model-ranking views for different questions.
Keep near-ties, severe mistakes, forced moves and source/phase differences
visible. Correlations across the 75 distinct models still share training pools,
initialization choices, nested data and evaluation positions; avoid pretending
every model-position pair is independent. A game-outcome anchor, if selected,
requires a preselected panel and enough varied opening families to be informative.

## Suggested skills

- `experiment` for catalog recall, protocol registration and retained evidence.
- `grilling` for material decisions, honoring a clear acceptance without another
  confirmation round.
- `handoff` to update this packet from the settled owner and preserve boundaries.

## Forbidden actions

- No retraining, scoring, games or new default selection during this interview.
- No use or reveal of either sealed evaluation pool without an explicit decision.
- No deletion of saved weights, source data, repeated controls or failed attempts.
- No replacement of earlier primary metrics or conclusions with favorable new ones.
- No parallel writer, silent budget extension or claim that metric agreement
  alone establishes playing strength.
