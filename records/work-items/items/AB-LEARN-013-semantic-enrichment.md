---
description: Test immediate tactical-tag enrichment with identical source trajectory contributions.
scope: backlog item
status: experimental
last_update: 2026-09-11
document_class: work_record
work_id: AB-LEARN-013
work_status: done
work_kind: research
added: 2026-09-11
tags: domain
depends_on: AB-LEARN-012
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-11"
---

# AB-LEARN-013 — Matched semantic enrichment

## Intent

Test whether more immediate tactical positions improve the selected 80/10/10
plausible/intervention/random mixture. The user authorized this and the following
scaling study on 2026-09-11. The [source screen](AB-LEARN-012-generated-source-mixing.md)
improved balanced development agreement but retained a large generalization gap
and losses on plausible endgames. Capture agreement remained low; in-check scores
were partly explained by forced legal actions. An enrichment gain is plausible,
but the union tag contains distinct phenomena and may displace useful coverage.

## Acceptance Criteria

- Use the same one-thread 100k supervision specification and parent exclusions;
  preserve the existing 373 development inputs/labels and 3900 sealed inputs.
  No teacher queries or sealed-test predictions. The benchmark is inspected and
  the selected source mixture was chosen on it: this is exploratory evidence.
- Keep 4000 unique inputs, 80/10/10 policy proportions, and 50/50 middle/endgame
  within each policy in each of the original three disjoint training blocks.
- Enrich `in-check OR teacher-capture OR teacher-gives-check` by 10 percentage
  points in each policy/phase cell: 400 replacements per block. Every removed
  untagged input is paired with a previously unselected tagged input with the
  same phase, policy and complete contributing-trajectory signature. Preserve
  the exact input contribution of every trajectory; retain all matched pairs.
- Training-only feasibility permits up to 10 pp, requiring at least 5 pp and
  choosing a common integer percentage before fitting. Feasibility established
  the full 10 pp; no fit result sets the enrichment amount.
- Freshly run both natural and enriched cases at seeds 7/17/27: 18 fits. Natural
  inputs, ordering and settings equal the previous 80/10/10 controls; independently
  check exact prediction agreement with those historical controls.
- Fixed 1261-64-8100 float32 MLP, CPU one thread, masked teacher-move loss,
  Adam .01, 200 full-batch updates in chunks of 256. Primary remains the equal
  mean of the six development policy/phase agreements. Report cross-entropy,
  train gap, all tag/phase/source slices, denominators, time and peak RSS.
- Advance enrichment only if its seed-mean primary delta is positive in all
  three training blocks; otherwise retain natural frequencies. This is a
  decision rule, not a statistical significance test or playing-strength claim.
- The two follow-up matrices share a 7200-second allowance, including the later
  largest-size resource pilot. Each fit has at most 600 seconds, bounded by the
  remaining total; stop before another fit above 1.5GB process peak RSS. Hash
  checks precede the trainer's timer; finalization can overrun its training
  deadline. Preparation and independent verification are timed separately.
- Preserve resolved configs, exact selection lists, snapshots, cached tensors,
  source archives, every started fit and raw predictions/checkpoints. Freshly
  reload all checkpoints and recompute metrics independently; verify snapshot
  selection, tag derivation, lineage equality and the complete fit matrix.

## Context and Trade-offs

The [frozen config](../../../data/experiments/learning/generated-followups-v1.json)
pins parent evidence, the training pool and both plans. Selection lives in
`qi.training_data.followups`; `scripts/run_generated_followups.py` orchestrates
the accepted snapshot trainer. Existing trainer/optimizer semantics do not change.

The parent-eligible training census reproduces 70378 inputs. Natural union-tag
counts are 1608/1636/1590 across the three blocks; enriched counts are
2008/2036/1990. Exact source contributions remain identical at 2052/1986/2040
trajectories, with a maximum of six inputs per trajectory. Swaps change positions
within a phase and can change individual tag frequencies; the study tests the
union enrichment, not the causal contribution of each tag.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-11 | Codex | — | wip | User said to run the proposed semantic and scaling follow-ups; training-only feasibility and protocol frozen before fitting. |
| 2026-09-11 | Codex | wip | done | All 18 fits independently verified; two blocks declined, so retain natural tag frequencies. |

## Implementation Ledger

### 2026-09-11 — decision: matched enrichment and fixed evaluation

- Evidence: `artifacts/learning/generated-followups-v1/semantic/plan/manifest.json`
  records all 1200 matched replacements and exact trajectory-count fingerprints.
- Consequence: use the feasible +10 pp treatment. Refit both controls and
  treatment, and independently verify old/new control prediction parity.
- Follow-up: complete preparation, gates, fits, verification and assessed catalog entry.
- Review: not-required; user authorized the next two stages.

### 2026-09-11 — verification: preparation and implementation gates

- Evidence: all six datasets are ready after 867.249 seconds of preparation;
  full repository gate passed 597 Python tests, one MPS skip and five browser
  tests. Focused source-signature, nesting, shared-point and decision-rule tests
  passed. Config, plan and catalog evidence hashes were rechecked before fitting.
- Consequence: start the 18 fits with implementation `967d50c`. Independent
  scaling snapshot preparation may overlap these fits; report wall times as
  observations under host contention, not an isolated throughput benchmark.
- Follow-up: independently reload and verify every completed fit before the
  scaling resource pilot or scientific scaling fits.
- Review: not-required; authorized execution of the frozen protocol.

### 2026-09-11 — deviation: repair dataset lookup before the first enriched fit

- Evidence: `artifacts/learning/generated-followups-v1/semantic/study/summary.json`
  retains the failed first attempt, three complete block-0 natural controls and
  100.062 seconds. Dataset lookup incorrectly included update/seed suffixes in
  the snapshot directory. Failure occurred before an enriched fit was created.
- Consequence: resolve datasets by their explicit dataset identity, add a
  regression test for semantic and scaling trials, and retain the original
  attempt in place. Restart all 18 fits under `study-retry-1`; source code,
  checkpoints and the original traceback remain available. Scientific settings,
  selection and decision rules are unchanged. Charge every earlier attempt's
  elapsed time against the original shared 7200-second allowance.
- Follow-up: rerun gates, then the full matrix and independent verification.
- Review: not-required; routine authorized runner repair with evidence retention.

### 2026-09-11 — finding: enrichment does not pass the frozen rule

- Evidence: [compact results](../../../data/experiments/learning/history/generated-semantic-enrichment-v1.json),
  `artifacts/learning/generated-followups-v1/semantic/verification.json` and its
  receipt manifest retain all 18 fits, independently reloaded predictions, exact
  selection proofs and source archive. All nine natural controls reproduce the
  parent screen's predictions exactly. Implementation `ec7613f` passed 598 Python
  tests, one optional MPS skip, five browser tests and the full repository gate.
- Observation: balanced development agreement changes from 16.020% to 15.771%
  (-0.249 pp). Paired block-mean differences are -0.326/-0.452/+0.029 pp. The
  all-block-positive rule fails. Both cases reach 100% training agreement.
- Supporting slices: teacher-capture agreement rises 9.259% → 10.022% (102
  development inputs), teacher-gives-check rises 15.625% → 18.403% (64), while
  in-check falls 74.286% → 71.746% (35, including forced-action positions).
  Plausible endgames fall 18.403% → 18.229% (64); full phase/source slices and
  denominators remain in the compact results. Unweighted development
  cross-entropy changes only slightly, 9.147 → 9.132; it is a different objective
  from six-cell macro agreement and does not reverse the primary decision.
- Resources: the successful matrix takes 845.013 seconds; the retained failed
  attempt adds 100.062 seconds, totaling 945.074 seconds charged to the shared
  allowance. Fits span 23.368–92.785 seconds, with process peak RSS 543031296
  bytes (517.875 MiB). Preparation takes 867.249 seconds. Concurrent scaling
  preparation makes these host-contended timing observations. A standalone
  verification wall timer was not retained; do not infer one from fit times.
- Consequence: retain natural frequencies. These tags describe immediate
  position/teacher-move features; enriching their union is not evidence that
  any individual tactical category is unhelpful. This reused 373-input
  development benchmark and one generation seed remain exploratory; the 3900
  sealed inputs were not scored and no player defaults changed.
- Follow-up: finish the independently frozen natural-tag scaling matrix in
  [AB-LEARN-014](AB-LEARN-014-generated-data-scaling.md). Revisit enrichment only
  with a separately locked tag-specific hypothesis and fresh evaluation data.
- Review: not-required; authorized study completed under its decision rule.


```experiment
{
  "schema_version": 1,
  "id": "generated-semantic-enrichment-v1",
  "title": "Matched generated semantic enrichment",
  "question": "Does +10 pp immediate tactical-tag coverage improve imitation with identical trajectory contributions?",
  "kind": "learning",
  "topics": [
    "generated data",
    "semantic",
    "semantic tags",
    "scaling",
    "full-batch"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "80/10/10; 4000 inputs, exact per-trajectory contributions; +10 pp union-tag enrichment per policy/phase cell; three training blocks and seeds 7/17/27; 18 fresh fits at 200 updates. Fixed one-thread 100k labels, CPU one thread, MLP 1261-64-8100, Adam .01, float32, chunks 256. Fixed 373-input six-cell macro development metric; 3900 sealed inputs unscored. Combined follow-ups 7200 seconds, max 600 seconds/fit and 1.5GB process peak RSS.",
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
      "path": "artifacts/learning/generated-followups-v1/semantic/plan/manifest.json",
      "role": "data",
      "sha256": "b65857bdc5c2e469884fd144a3bef4a401f1edaa48ad7ca7211cb29673890ab7"
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
  "novelty": "First matched semantic intervention on this source pool."
}
```


```experiment
{
  "schema_version": 1,
  "id": "generated-semantic-enrichment-v1",
  "title": "Matched generated semantic enrichment",
  "question": "Does +10 pp immediate tactical-tag coverage improve imitation with identical trajectory contributions?",
  "kind": "learning",
  "topics": [
    "generated data",
    "semantic",
    "semantic tags",
    "scaling",
    "full-batch"
  ],
  "execution": "complete",
  "conclusion": "not-supported",
  "finding": "18 verified fits on 373 reused development inputs: +10 pp matched union-tag enrichment changes six-cell macro agreement 16.020% to 15.771% (-0.249 pp); block deltas -0.326/-0.452/+0.029 pp. All nine natural controls exactly reproduce parent predictions. Capture and checking-move slices improve, but two blocks decline and both cases fit training labels completely.",
  "conditions": "80/10/10; 4000 inputs, exact per-trajectory contributions; +10 pp union-tag enrichment per policy/phase cell; three training blocks and seeds 7/17/27; 18 fresh fits at 200 updates. Fixed one-thread 100k labels, CPU one thread, MLP 1261-64-8100, Adam .01, float32, chunks 256. Fixed 373-input six-cell macro development metric; 3900 sealed inputs unscored. Combined follow-ups 7200 seconds, max 600 seconds/fit and 1.5GB process peak RSS.",
  "limitations": "Exploratory reused development set, one generation seed; initialization seeds are not independent datasets. No correctness or playing-strength claim. First attempt failed before enrichment after three completed controls; retained in place and its 100.062 seconds charged alongside the fresh 18-fit matrix. Fit timings overlap scaling preparation. Independent verification has no separately retained wall timer.",
  "decision": "Retain natural tag frequencies; continue the independently frozen scaling matrix. No player-default or playing-strength promotion.",
  "revisit": "A separately locked tag-specific hypothesis with fresh evaluation data; this union enrichment does not isolate individual tags.",
  "evidence": [
    {
      "path": "data/experiments/learning/generated-followups-v1.json",
      "role": "config",
      "sha256": "6e133c4e6b3c68b3a75b2f02b574a900ba91d40bc7349d2be20fa847b2da8746"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/semantic/plan/manifest.json",
      "role": "data",
      "sha256": "b65857bdc5c2e469884fd144a3bef4a401f1edaa48ad7ca7211cb29673890ab7"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/pool/manifest.json",
      "role": "data",
      "sha256": "f79e9abf0ab8d4c54038ba7d8f3f944140d23c51ce407cd4816a9e1cb2e8d7c9"
    },
    {
      "path": "data/experiments/learning/history/generated-semantic-enrichment-v1.json",
      "role": "results",
      "sha256": "ed1e61a9c7988562e432bbe486b9dccf8c58c7bec2b53cb053ef2c099c70d30a"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/semantic/verification.json",
      "role": "results",
      "sha256": "eda5f13b8ebcb08d76a062fb179bfe601c5f8f3b743d1524df7d76112bfa3aa6"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/semantic/receipts.json",
      "role": "run",
      "sha256": "f8fd14fda819bf00213d37a1487259ed268cc8f2a87681fd6f68affdd28a4794"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/semantic/study-retry-1/summary.json",
      "role": "run",
      "sha256": "90764a2ddf41af6ebcee8c711a1be3a5294f5fb8a8d5c31afaf957bb9cd2aee0"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/semantic/study-retry-1/source-files.json",
      "role": "source",
      "sha256": "cade61dcf4cb8b1939f786402a08c4e7327ff86472fe0314120f6b81a8e69cc8"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/semantic/study/summary.json",
      "role": "run",
      "sha256": "1ee9a34cd41a9c3ff7a7a3f34250f4674091bf78ec05fb2af4ec007bcda703f6"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/semantic/execution.log",
      "role": "run",
      "sha256": "f0e8a8036f161f013e4a61155afd30a3cb038ee42e01543075f8951a3ae5bea5"
    },
    {
      "path": "artifacts/learning/generated-followups-v1/repair-build-check.log",
      "role": "report",
      "sha256": "9a5b734e9e91a1f9a4c47b4baf2a6008a8bcbfc8c81bc903521c3a3a26225361"
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
  "novelty": "First matched semantic intervention on this source pool."
}
```
