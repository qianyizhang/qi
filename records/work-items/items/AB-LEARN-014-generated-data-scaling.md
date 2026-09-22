---
description: Compare nested generated-data sizes with fixed passes and fixed example presentations.
scope: backlog item
status: experimental
last_update: 2026-09-22
document_class: work_record
work_id: AB-LEARN-014
work_status: done
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
| 2026-09-11 | Codex | wip | done | All 30 fits independently verified; both mixtures pass the scaling rule under both compute views. |

## Implementation Ledger

### 2026-09-11 — decision: freeze natural-tag nested curves

- Evidence: both 16k selections and their exact 4k/1k prefixes are retained in
  the plan; the mixed 16k maximum contribution is eight per trajectory.
- Consequence: execute after verifying the semantic stage. Keep this plan fixed
  regardless of that stage's result; run the shared 4k condition only once.
- Follow-up: complete snapshot proofs, resource pilot, 30 fits and verification.
- Review: not-required; user authorized the next two stages.

### 2026-09-11 — verification: snapshot preparation and largest-size resource gate

- Evidence: all six datasets passed recipe/snapshot/cache checks after 1426.290
  seconds of preparation. The 16k mixed-data resource pilot completed all 200
  updates in 245.030 seconds, with process peak RSS 573538304 bytes (546.969 MiB),
  under the frozen 600-second and 1.5GB ceilings. Raw evidence is retained at
  `artifacts/learning/generated-followups-v1/scaling/study/resource-pilot/`.
- Consequence: execute the 30-fit scientific matrix unchanged. Preparation
  overlapped the semantic fits and finished before this pilot. Pilot scores do
  not select scientific settings. Charge the semantic stage's 945.074 seconds,
  including its retained failed attempt, against the same 7200-second allowance.
- Follow-up: complete all fits, independently verify the matrix and assess both
  compute views under their predeclared rules.
- Review: not-required; frozen resource gate passed.

### 2026-09-11 — finding: more distinct inputs help under both compute views

- Evidence: [compact results](../../../data/experiments/learning/history/generated-data-scaling-v1.json),
  local-only learning curves at
  `artifacts/learning/generated-followups-v1/scaling/learning-curves.png`,
  `artifacts/learning/generated-followups-v1/scaling/verification.json` and its
  receipt manifest retain all 30 fits, fresh checkpoint reloads, complete
  prediction parity, nested selection proofs and source archive. The six 4k
  fits are shared between views. The 4k selections here come from the pooled
  nested master and differ from the semantic study's three block selections.

| Compute view | Training sources | 1k | 4k | 16k | Frozen scaling rule |
| --- | --- | --- | --- | --- | --- |
| 200 updates | Plausible only | 12.726% | 14.849% | 16.986% | Pass |
| 200 updates | 80/10/10 | 12.364% | 16.324% | 17.543% | Pass |
| 800000 presentations | Plausible only | 12.986% | 14.849% | 17.210% | Pass |
| 800000 presentations | 80/10/10 | 12.451% | 16.324% | 18.151% | Pass |

- Observation: every curve increases at both successive mean points and has
  positive 16k-minus-1k differences in all three paired initialization seeds.
  Those endpoint differences span +3.287 to +7.041 pp. This supports scaling in
  the fixed model/teacher regime even when example presentations stay constant;
  source coverage and concentration change as part of the size treatment.
- Composition tradeoff: the mixture trails plausible-only at 1k but leads at
  4k and 16k on the balanced primary. At 16k, plausible-endgame agreement remains
  lower with the mixture: 21.875% versus 25.521% at 50 updates, and 19.792%
  versus 24.479% at 200 (64 development inputs). Capture agreement at 50 updates
  favors the mixture, 13.399% versus 9.150% (102). The full slices, denominators
  and initialization results are retained; no source mixture is universally best.
- Training behavior: at 16k/50 updates, plausible and mixed training agreement
  are 94.548% and 95.219%, with development cross-entropy 5.437 and 5.334.
  At 200 updates both fit training labels completely, while development
  cross-entropy rises to 9.946 and 9.582. Mean primary also falls slightly with
  the extra updates, though that direction is not uniform across seeds. This is
  consistent with overfitting; 50 updates is not an established optimum and the
  study did not predeclare a stopping-rule confirmation. The large training-to-
  development gap remains.
- Resources and audit: the scaling stage, including its 245.030-second pilot,
  takes 1808.485 seconds. All comparative fits complete within configured
  limits; the largest process high-water mark is 708591616 bytes (675.766 MiB).
  Independent matrix verification takes 21.68 seconds. The additional local-only
  closeout audit at `artifacts/learning/generated-followups-v1/closeout-audit.json`
  checks all 52 retained fits (48 comparisons, one pilot, three earlier controls),
  independently reloads the pilot, verifies all 39 frozen files and the original
  collection hash, and finds zero scored sealed inputs. Its 3.645-second runtime
  is separate from fitting. Combined charged time is 2753.559 seconds (45.893
  minutes) of 7200, including the failed semantic attempt; raw evidence remains
  intact. The chart was visually inspected; rendering environment and SVG are
  retained beside the run.
- Consequence: advance larger natural-tag datasets as exploratory candidates.
  Keep plausible-only as a comparator and preserve the endgame tradeoff. The
  reused 373-position development set, one generation seed and one nested
  master pool do not establish general superiority, playing strength or an
  optimal update count. Initialization seeds are not dataset replications.
- Follow-up: a separately frozen confirmation on sealed evaluation data,
  retaining source/phase slices and a declared update budget, before any default
  promotion. The 3900 sealed inputs remain unscored; no further run is scheduled.
- Review: not-required; authorized matrices and their predeclared decisions completed.


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


```experiment
{
  "schema_version": 1,
  "id": "generated-data-scaling-v1",
  "title": "Generated data scaling under two compute views",
  "question": "Does 1k to 16k scaling improve generated-data imitation under fixed passes and fixed example presentations?",
  "kind": "learning",
  "topics": [
    "generated data",
    "data scaling",
    "source mixing",
    "semantic tags",
    "full-batch",
    "overfitting"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "30 verified fits on 373 reused development inputs: all four 1k/4k/16k curves pass the predeclared scaling rule. At 200 updates, plausible-only agreement rises 12.726% to 16.986% and 80/10/10 rises 12.364% to 17.543%. At 800000 presentations, the corresponding endpoints are 12.986% to 17.210% and 12.451% to 18.151%. All paired seed endpoint gains are positive (+3.287 to +7.041 pp).",
  "conditions": "Plausible-only and 80/10/10; one pooled training set with nested 1000/4000/16000 inputs; natural tags independent of enrichment result; seeds 7/17/27; 200 passes and 800000 presentations (800/200/50 updates); 30 unique fits with six shared 4k points. Fixed one-thread 100k labels, CPU one thread, MLP 1261-64-8100, Adam .01, float32, chunks 256. Fixed 373-input six-cell macro development metric; 3900 sealed inputs unscored. Combined follow-ups 7200 seconds, max 600 seconds/fit and 1.5GB process peak RSS.",
  "limitations": "Exploratory reused development set, one generation seed; initialization seeds are not independent datasets. No correctness or playing-strength claim. The mixture loses at 1k and on plausible endgames at 16k. At 16k, 200 updates memorize training labels and increase development cross-entropy relative to 50; primary differences between update counts vary across seeds. Six 4k fits are shared between views. Both stages, the pilot and the retained failed semantic attempt consume 45.893 of 120 allowed minutes; all 52 retained fits exclude sealed inputs.",
  "decision": "Advance larger natural-tag datasets as exploratory candidates for a separately frozen sealed confirmation. Retain plausible-only as a comparator and report source/phase tradeoffs; no player-default promotion or optimal stopping-rule claim.",
  "revisit": "Fresh evaluation under a declared source mixture, phase reporting and update budget; separate generation seeds for dataset replication or a changed teacher/model.",
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
    },
    {
      "path": "data/experiments/learning/history/generated-data-scaling-v1.json",
      "role": "results",
      "sha256": "3bab23d0b6ecc3778e32bf48cdbf4a2cdec036e8f61ee9d1d873458dd85aff98"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/scaling/verification.json",
      "role": "results",
      "sha256": "a8e61d616a7d3ee7a9940b68cb9e9d000b8d7bf406bd1342aa87e2afb7cbd282"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/scaling/receipts.json",
      "role": "run",
      "sha256": "1491de08795722bbbed7450a81c99bb25ef343c2ac07cb5f42e8f2f95b6450e6"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/scaling/study/summary.json",
      "role": "run",
      "sha256": "9c2a98f7e3ce4fdeeb5dcb8d96b159f1610d86995715020bfeb9189705eff204"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/scaling/study/source-files.json",
      "role": "source",
      "sha256": "cade61dcf4cb8b1939f786402a08c4e7327ff86472fe0314120f6b81a8e69cc8"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/scaling/preparation.json",
      "role": "data",
      "sha256": "968c4065a3be43d99d9af76e221824ebf779a6dc5dfca7c2e828f7a1e94263c3"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/scaling/verification-timing.log",
      "role": "report",
      "sha256": "b3abe6e3407595ca845b259c38f212aa13fa8d2d44c657ce8e1de5ea1f5c887b"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/closeout-audit.json",
      "role": "report",
      "sha256": "d415dfa6281c621f23fd2665534b482b4fab70f57db82e48ca454bdd6d550fee"
    },
    {
      "path": "data/experiments/learning/generated-followups-v1/verify_closeout.py",
      "role": "source",
      "sha256": "bc381ff81c8f90ebbde39bbadf81ced2736030ee0eb18db7faaf9ff031fd3a61"
    },
    {
      "path": "data/experiments/learning/generated-followups-v1/summarize.py",
      "role": "source",
      "sha256": "1ef7bbaf0e87979e70434047f1b4c993f6699d8aa41315a9fb05dc6210658188"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/scaling/learning-curves.png",
      "role": "report",
      "sha256": "876a4c37a25983487973dd83f0342aeff12d431f6a3888ee5f03919ebbee4e87"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/scaling/learning-curves.svg",
      "role": "report",
      "sha256": "aaa4342ed1c20869c1321bc784882ffa5b486b07223448d2f056d66a8e19443d"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/plot-environment.json",
      "role": "source",
      "sha256": "74d8ed2a22ab04e0c656024145e0bd9dfa4c93858439d78aeb42bb7c5093ddd1"
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
    },
    {
      "id": "generated-semantic-enrichment-v1",
      "relationship": "uses",
      "contribution": "Retains the preceding negative enrichment result; natural tag frequencies and the scaling plan were frozen independently of that outcome."
    }
  ],
  "novelty": "First generated-source nested curve with separate fixed-pass and fixed-presentation views."
}
```
