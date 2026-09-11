---
description: Compare nested generated-data sizes with fixed passes and fixed example presentations.
scope: backlog item
status: experimental
last_update: 2026-09-11
document_class: work_record
work_id: AB-LEARN-014
work_status: wip
work_kind: research
added: 2026-09-11
tags: domain
depends_on: AB-LEARN-012, AB-LEARN-013
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-11"
---

# AB-LEARN-014 — Generated-data scaling

## Intent

Measure whether the larger generated collection helps the fixed policy, and
separate more data with more passes of computation from a fixed number of
example presentations. The user authorized execution after the semantic screen.
The [earlier shallow-teacher curve](AB-LEARN-004-dataset-scaling.md) improved from
16.74% to 25.70% across 768–12288 labels. This comparison changes to longer games
and a 100k teacher; those absolute scores are not a common benchmark.

## Acceptance Criteria

- Compare plausible-only and the selected 80/10/10 source mixture at nested
  1000/4000/16000 distinct inputs. Pool the three previous training blocks into
  one master training pool, retaining all parent exclusions and the same 373
  development inputs/labels. Keep all 3900 sealed inputs unscored.
- Freeze a deterministic game-balanced 16k master selection for each mixture,
  max eight inputs per contributing trajectory. Smaller sets use exact per-cell
  prefixes, preserving source proportions and 50/50 middle/endgame per policy.
  Assert strict nesting, quotas and complete input disjointness from evaluation.
- Preserve natural deterministic tag frequencies independently of the semantic
  screen's outcome. This study isolates size and source composition; it does not
  carry a selected semantic treatment into a different-size comparison.
- Fixed 1261-64-8100 float32 MLP, masked teacher move objective, Adam .01,
  one CPU thread and 256-row full-batch gradient chunks; seeds 7/17/27.
- Two views: 200 updates at every size; and 800000 example presentations at
  every size, requiring 800/200/50 updates for 1k/4k/16k. The six 4k/200-update
  fits are exactly the same points in both views and are run once. There are
  30 unique fits, not 36 independent trials. No warm starts or learning-rate tuning.
- Primary: equal-weight six-cell development agreement. For each mixture and
  each view, support the scaling direction only if both successive mean
  increases are positive and 16k-minus-1k is positive for every paired seed.
  Report each view separately, including negative/intermediate results, source
  coverage, per-slice metrics, train gap, cross-entropy, runtime and memory.
- This is one nested master pool from one generation seed. Initialization seeds
  are not independent dataset repetitions; the rule is not a significance test.
  Compare mixture differences descriptively at each size, retaining the previous
  plausible-endgame loss. No playing-strength or player-default promotion.
- Follow the shared 7200-second fit allowance and 600-second per-fit ceiling
  in [AB-LEARN-013](AB-LEARN-013-semantic-enrichment.md). Before scientific scaling
  fits, run a 16k mixed-data, 200-update resource pilot at seed 917; require full
  completion and process peak RSS at most 1.5GB. Pilot scores do not select settings.
- Retain all started runs, selected inputs, recipe and cache fingerprints, code
  archive, raw predictions and checkpoints. Independently reload every checkpoint,
  recompute metrics, verify the 30-fit matrix and shared-point accounting, and
  record conclusions in this owner and the catalog.

## Context and Trade-offs

The [frozen config](../../../data/experiments/learning/generated-followups-v1.json)
and `artifacts/learning/generated-followups-v1/scaling/plan/manifest.json` retain
the feasible pre-fit selection. Plausible-only covers 568/2259/5029 trajectories
at 1k/4k/16k; mixed data covers 608/2376/6111. Coverage and concentration change
with size and are part of this data-scaling treatment.

Fixed passes spend more compute as size increases. Fixed presentations change
the number of Adam updates and do not guarantee equal wall time or FLOPs.
Development has already informed source-mixture selection; these curves are
exploratory and require separate sealed confirmation before general claims.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-11 | Codex | — | wip | User authorized both follow-ups; all six nested selections passed training-only quota/cap feasibility before fitting. |

## Implementation Ledger

### 2026-09-11 — decision: freeze natural-tag nested curves

- Evidence: both 16k selections and their exact 4k/1k prefixes are retained in
  the plan; the mixed 16k maximum contribution is eight per trajectory.
- Consequence: execute after verifying the semantic stage. Keep this plan fixed
  regardless of that stage's result; run the shared 4k condition only once.
- Follow-up: complete snapshot proofs, resource pilot, 30 fits and verification.
- Review: not-required; user authorized the next two stages.


```experiment
{
  "schema_version": 1,
  "id": "generated-data-scaling-v1",
  "title": "Generated data scaling under two compute views",
  "question": "Does 1k to 16k scaling improve generated-data imitation under fixed passes and fixed example presentations?",
  "kind": "learning",
  "topics": [
    "generated data",
    "scaling",
    "semantic tags",
    "scaling",
    "full-batch"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Plausible-only and 80/10/10; one pooled training set with nested 1000/4000/16000 inputs; natural tags independent of enrichment result; seeds 7/17/27; 200 passes and 800000 presentations (800/200/50 updates); 30 unique fits with six shared 4k points. Fixed one-thread 100k labels, CPU one thread, MLP 1261-64-8100, Adam .01, float32, chunks 256. Fixed 373-input six-cell macro development metric; 3900 sealed inputs unscored. Combined follow-ups 7200 seconds, max 600 seconds/fit and 1.5GB process peak RSS.",
  "limitations": "Exploratory reused development set, one generation seed; initialization seeds are not independent datasets. No correctness or playing-strength claim.",
  "decision": "",
  "revisit": "",
  "evidence": [
    {
      "path": "data/experiments/learning/generated-followups-v1.json",
      "role": "config",
      "sha256": "6e133c4e6b3c68b3a75b2f02b574a900ba91d40bc7349d2be20fa847b2da8746"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/scaling/plan/manifest.json",
      "role": "data",
      "sha256": "ec230844d9e8c45c251e35e71e6d335c45eae5743558c62cb57a0c3eea216c03"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/pool/manifest.json",
      "role": "data",
      "sha256": "f79e9abf0ab8d4c54038ba7d8f3f944140d23c51ce407cd4816a9e1cb2e8d7c9"
    }
  ],
  "prior_work": [
    {
      "id": "generated-source-mixing-v1",
      "relationship": "extends",
      "contribution": "Keep the chosen source mixture and measured limitations while isolating the next data variable."
    },
    {
      "id": "policy-data-scaling-v1",
      "relationship": "extends",
      "contribution": "Measure changed longer-game stronger-teacher data, separating passes from presentations."
    }
  ],
  "novelty": "First generated-source nested curve with separate fixed-pass and fixed-presentation views."
}
```
