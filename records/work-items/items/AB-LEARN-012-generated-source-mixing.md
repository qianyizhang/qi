---
description: Compare generated-source mixtures with fixed labels, model, phase balance and training updates.
scope: backlog item
status: experimental
last_update: 2026-09-11
document_class: work_record
work_id: AB-LEARN-012
work_status: done
work_kind: research
added: 2026-09-11
tags: domain
depends_on: AB-LEARN-010, AB-DATA-008
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-11"
---

# AB-LEARN-012 — Generated-source mixture screen

## Intent

Test whether substituting 10% intervention data, 10% random data, or both improves
held-out teacher imitation relative to plausible-only data. User accepted all
five recommended decisions and authorized implementation and execution on
2026-09-11. The [audit](../../reports/2026-09-11-generated-sample-audit.md) owns the
descriptive findings; [ADR-0010](../../../docs/adr/0010-frozen-selection-and-bounded-full-batch-training.md)
owns the implementation trade-off.

## Acceptance Criteria

- One-thread, single-PV 100k labels; middlegame/endgame only. Keep model and
  label specification fixed, retaining 10k disagreement as a diagnostic.
- Freeze reasoned exclusions for cross-split input lineage and chosen-spec
  conflicts, preserving raw evidence. Audit earlier dataset inputs, cluster
  duplicate trajectories and exclude inputs shared across experimental groups.
- Four 4000-input cases: plausible/intervention/random = 100/0/0, 90/10/0,
  90/0/10 and 80/10/10. Each included policy is 50/50 middle/endgame. Deterministic
  game-balanced selection with at most eight inputs per trajectory per case.
- Three disjoint training-source blocks, initialization seeds 7/17/27: 36 fits.
  All blocks come from one generation seed; seeds are not independent datasets.
- Partition original validation trajectory groups into development and sealed
  test using a frozen hash assignment before predictions. Remove inputs spanning
  these groups. Use the same development inputs across all fits; no sealed-test
  predictions in this exploratory screen.
- Fixed 1261-64-8100 float32 MLP, CPU one thread, full-batch Adam .01, 200 updates,
  bounded chunks of 256, fixed snapshot order. Preserve objective and update
  parity before fitting. Do not change chunk size or hyperparameters mid-matrix.
- Primary: equal-weight mean development agreement over six policy/phase cells.
  Report population-weighted agreement, cross-entropy, semantic slices, source
  concentration, train gap, runtime, memory and completed-update counts.
- Rank by mean primary score; baseline wins ties. Advance a nonbaseline case
  only if every training block has positive seed-mean improvement. Otherwise
  retain baseline and negative/inconclusive evidence. No playing-strength claim.
- Ten-minute engineering/resource pilot; two-hour matrix allowance, per-fit
  training deadline max(60s, three times calibrated pilot time), capped at
  ten minutes. The deadline includes model setup and optimization; snapshot hash
  checks precede it and evaluation/checkpoint finalization may extend past it.
  Freeze the allowance before the first scientific fit. Stop before another fit
  if process lifetime peak RSS exceeds 1.5GB. Preparation
  is timed separately. Any quota shortfall is a data-only failed attempt, never
  silently refilled; amend before looking at fit results. Preserve deadline/failure
  evidence and all started runs. Sealed test, enrichment and scaling remain later
  separately locked comparisons based on this screen's outcome.
- Retain resolved configs, selection lists, snapshots, implementation archive,
  predictions, checkpoints and receipts. Verify reloads, raw metric arithmetic,
  all planned fits and shared evaluation identity. Run repository and focused gates.

## Context and Trade-offs

Earlier source coverage and scaling studies improved shallow-teacher imitation
on early random play. The stronger-teacher study was inconclusive under its
primary rule. This study extends those findings to longer, phase-matched,
multi-policy trajectories. It tests composition at fixed size before scaling.
Budget disagreement and engine scores remain preference evidence, not truth.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-11 | Codex | — | wip | User accepted the five recommendations and requested execution; protocol recorded before fitting. |
| 2026-09-11 | Codex | wip | done | All 36 fits completed 200 updates and passed independent evidence verification; 80/10/10 met the frozen advancement rule. |

## Implementation Ledger

### 2026-09-11 — decision: freeze the first screen

- Evidence: accepted user decisions, audit and ADR-0010.
- Consequence: implement explicit selection and bounded full-batch training,
  then execute the 36-fit matrix under the stated budget.
- Follow-up: record feasibility, parity, complete or partial results and next decision.
- Review: not-required; user explicitly authorized this scope.

### 2026-09-11 — deviation: development quota feasibility before fitting

- Evidence: `artifacts/learning/generated-source-mixing-v1/` and `-run2/` retain
  two data-only shortfalls, frozen configs, failed planner bytes and logs; zero
  teacher queries, snapshots or model fits occurred. Intervention endgame had 61
  candidate inputs but only 36 under middle-first greedy allocation and 53 even
  when processed first under the all-contributing-trajectory cap.
- Consequence: the explicit
  [amendment](../../../data/experiments/learning/generated-source-mixing-v1-amended.json)
  freezes up to 64 development inputs per cell after cap feasibility, scarce
  phase first, requiring at least 20 per cell. Export quotas then equal those
  frozen counts; no replacement from another cell. Training quotas, eight/game
  cap, split hash, metrics, seeds and hyperparameters are unchanged. Third
  preparation is `artifacts/learning/generated-source-mixing-v1-run3/`.
- Follow-up: verify all 12 strict training selections before any fit; final
  development counts will be retained in the plan manifest.
- Review: not-required; the predeclared protocol permits data-only amendments
  before inspecting training results.

### 2026-09-11 — verification: freeze the feasible preparation

- Evidence: `artifacts/learning/generated-source-mixing-v1-run3/plan/manifest.json`.
  All 12 training selections contain exactly 4000 inputs. Development has 373
  inputs: 64 per policy/phase cell except intervention endgame with 53. The sealed
  set contains 3900 eligible inputs and remains unscored.
- Consequence: use the amended configuration for execution. Selected trajectories
  range from 1632 to 2052 per case, with maxima of five or six selected inputs per
  trajectory. The cap is controlled; total trajectory coverage differs by mixture
  and can contribute to a composition effect. No fit results informed these choices.
- Follow-up: complete all snapshot proofs, run the resource pilot and fixed matrix.
- Review: not-required; continuation of the accepted study.

### 2026-09-11 — finding: intervention mixtures improved the balanced screen

[Retained results](../../../data/experiments/learning/history/generated-source-mixing-v1.json)
are reproduced by the
[summarizer](../../../data/experiments/learning/generated-source-mixing-v1/summarize.py).
The [raw verification](../../../artifacts/learning/generated-source-mixing-v1-run3/verification.json)
and its receipts retain all 36 fits, shared development identity, label checks,
raw per-position metric arithmetic, checkpoint/reload equality and source archive.

Agreement below is the mean over nine fits per mixture. Primary gives equal
weight to each of six development policy/phase cells; population-weighted
agreement and cross-entropy use all 373 positions.

| Plausible/intervention/random | Primary agreement | Delta vs baseline | Block deltas, percentage points | Population agreement | Cross-entropy |
| --- | ---: | ---: | --- | ---: | ---: |
| 100/0/0 | 14.998% | — | — | 14.835% | 10.076 |
| 90/10/0 | 15.781% | +0.782 pp | +0.539 / +0.955 / +0.853 | 15.609% | 9.626 |
| 90/0/10 | 14.178% | −0.820 pp | −0.937 / −0.868 / −0.655 | 13.941% | 9.525 |
| 80/10/10 | 16.020% | +1.022 pp | +1.165 / +1.201 / +0.701 | 15.788% | 9.147 |

The 80/10/10 case has the highest primary mean and positive improvements in all
three blocks, so it advances under the frozen rule. Intervention alone also
improves every block. Random alone reduces top-1 agreement in every block even
while reducing cross-entropy. The 80/10/10 margin over 90/10/0 is only 0.240 pp;
their block differences are +0.626 / +0.246 / −0.152 pp. This screen does not
establish that adding random data is reliably better than intervention alone.

### 2026-09-11 — finding: tag slices expose uneven transfer

These are overlapping descriptive slices, not additional selection criteria.

| Development slice | Inputs | 100/0/0 | 90/10/0 | 90/0/10 | 80/10/10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| In check | 35 | 72.38% | 75.24% | 72.38% | 74.29% |
| Teacher captures | 102 | 7.30% | 8.17% | 6.54% | 9.26% |
| Teacher gives check | 64 | 12.50% | 16.49% | 10.42% | 15.63% |
| Plausible middlegame | 64 | 11.63% | 11.28% | 10.76% | 11.11% |
| Plausible endgame | 64 | 21.35% | 18.92% | 15.80% | 18.40% |
| Intervention middlegame | 64 | 20.83% | 25.87% | 20.49% | 25.52% |
| Intervention endgame | 53 | 20.55% | 21.59% | 22.22% | 23.90% |
| Random middlegame | 64 | 3.47% | 4.51% | 3.65% | 4.51% |
| Random endgame | 64 | 12.15% | 12.50% | 12.15% | 12.67% |

The balanced improvement comes with lower plausible-source agreement, especially
in endgames. The post-screen legal-action diagnostic explains why `in-check`
must not be called a uniformly difficult tag: 13/35 positions allow only one
move, and uniform legal choice would already achieve 64.76% expected agreement
on this slice. The corresponding capture expectation is 6.63%. This diagnostic
was added after scoring and did not change the primary metric or decision.

All 36 fits reached 100% training agreement, with mean training cross-entropy
approximately 0.0011–0.0012. Development cross-entropy remains 9.15–10.08.
Composition shifts do not remove the large training/generalization gap.

### 2026-09-11 — verification: complete first screen and retain boundaries

- Evidence: 36/36 fits, 200/200 updates each; matrix 928.784 seconds (15.480
  minutes), individual measured fits 22.109–68.183 seconds, frozen training
  allowance 75.218 seconds, maximum process lifetime peak RSS 558514176 bytes.
  CPU one thread, float32; preparation and the 25.073-second seed-917 resource
  pilot are separate. The exact executed source hash is
  `afa7cf75929b49c511df15a308114d8329847cf47ec2f8b5d4c30dc154d3037e`.
- Verification: full repository gate passed 594 Python tests, one MPS skip and
  five browser tests; focused parity/selection tests passed. Independent matrix
  verification and the receipt-checking summarizer passed. The two data-only
  shortfalls and an interrupted preparation are retained; there were no failed
  or discarded scientific fits.
- Consequence: advance 80/10/10 as an exploratory candidate for the balanced
  development objective, retaining 90/10/0 as a close comparator. Do not change
  player defaults or infer correctness/playing strength. Three training blocks
  share one generation seed and one 373-position development set; the decision
  rule is not a statistical significance test. Trajectory coverage also differs.
- Follow-up: freeze the next semantic-enrichment comparison from training-only
  feasibility, then the proposed nested 1000/4000/16000 curve on one master pool.
  Compare constant 200 passes with constant 800000 example presentations
  (800/200/50 updates), reporting their different compute/update semantics.
  Scaling and tag upweighting have not run. All 3900 sealed inputs remain unscored;
  open them only under a separately locked confirmation comparison.
- Review: not-required; authorized first screen completed under its frozen rule.


```experiment
{
  "schema_version": 1,
  "id": "generated-source-mixing-v1",
  "title": "Generated source mixture screen",
  "question": "Does adding intervention or random data improve phase-matched imitation at fixed 4000-input size?",
  "kind": "learning",
  "topics": [
    "mixing",
    "generated data",
    "semantic tags",
    "full-batch",
    "phase"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "One-thread single-PV 100k teacher; four mixtures at 4000 inputs, phase 50/50, three disjoint training blocks and seeds 7/17/27; fixed MLP/full-batch Adam .01/200 updates; 256-row chunks. Symmetric overlap and same-spec conflict exclusions. Six-cell macro development agreement; sealed test unscored. Two-hour matrix cap after resource calibration.",
  "limitations": "Exploratory selection from one generation seed; data-only quota failure precedes any amendment. No strength claim.",
  "decision": "",
  "revisit": "",
  "evidence": [
    {
      "path": "data/experiments/learning/generated-source-mixing-v1.json",
      "role": "config",
      "sha256": "d29b0b006279316f580788971288e5fd3f278c409125b296f9cb098e49b78093"
    }
  ],
  "prior_work": [
    {
      "id": "generated-sample-audit-v1",
      "relationship": "uses",
      "contribution": "Use measured eligible phases/policies and explicit quality exclusions to freeze the comparison."
    },
    {
      "id": "source-coverage-confirmation-v2",
      "relationship": "extends",
      "contribution": "Control source concentration under changed longer-game multi-policy supervision."
    },
    {
      "id": "teacher-quality-v1",
      "relationship": "uses",
      "contribution": "Keep preference fidelity distinct from playing strength and hold teacher identity fixed."
    }
  ],
  "novelty": "First controlled fixed-size generated-policy mixture comparison on the completed collection."
}
```


```experiment
{
  "schema_version": 1,
  "id": "generated-source-mixing-v1",
  "title": "Generated source mixture screen",
  "question": "Does adding intervention or random data improve phase-matched imitation at fixed 4000-input size?",
  "kind": "learning",
  "topics": [
    "mixing",
    "generated data",
    "semantic tags",
    "full-batch",
    "phase"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "One-thread single-PV 100k teacher; four mixtures at 4000 inputs, phase 50/50, three disjoint training blocks and seeds 7/17/27; fixed MLP/full-batch Adam .01/200 updates; 256-row chunks. Symmetric overlap and same-spec conflict exclusions. Six-cell macro development agreement; sealed test unscored. Two-hour matrix cap after resource calibration. Amended development allocation: 373 inputs, five cells of 64 and intervention endgame 53; 3900 sealed inputs. Stop before next fit above 1.5GB process lifetime peak RSS.",
  "limitations": "Exploratory selection from one generation seed. Fixed trajectory cap, but coverage varies from 1632 to 2052 trajectories per case. Two retained data-only quota failures preceded a cap-aware development amendment, with no fit results inspected. No strength claim.",
  "decision": "",
  "revisit": "",
  "evidence": [
    {
      "path": "data/experiments/learning/generated-source-mixing-v1-amended.json",
      "role": "config",
      "sha256": "7eb9d52ad6a383d572158eb7a82dd8eabb2857c0d33feeebba8b6b55e39b78e6"
    },
    {
      "path": "artifacts/learning/generated-source-mixing-v1-run3/plan/manifest.json",
      "role": "data",
      "sha256": "4dcb05654f6c17b7265eeee5a6af690b8776fd55051cb33a715bcdbbce446951"
    },
    {
      "path": "artifacts/learning/generated-source-mixing-v1/failure.json",
      "role": "report",
      "sha256": "b5a686dc846272dfc6e8fe538faa91f8ee605f3d324893a05718a5550954d773"
    },
    {
      "path": "artifacts/learning/generated-source-mixing-v1-run2/failure.json",
      "role": "report",
      "sha256": "13ecf382639f32ca2020a274bdc3c1e71144392486431b7b0a6889891231825a"
    }
  ],
  "prior_work": [
    {
      "id": "generated-sample-audit-v1",
      "relationship": "uses",
      "contribution": "Use measured eligible phases/policies and explicit quality exclusions to freeze the comparison."
    },
    {
      "id": "source-coverage-confirmation-v2",
      "relationship": "extends",
      "contribution": "Control source concentration under changed longer-game multi-policy supervision."
    },
    {
      "id": "teacher-quality-v1",
      "relationship": "uses",
      "contribution": "Keep preference fidelity distinct from playing strength and hold teacher identity fixed."
    }
  ],
  "novelty": "First controlled fixed-size generated-policy mixture comparison on the completed collection."
}
```


```experiment
{
  "schema_version": 1,
  "id": "generated-source-mixing-v1",
  "title": "Generated source mixture screen",
  "question": "Does adding intervention or random data improve phase-matched imitation at fixed 4000-input size?",
  "kind": "learning",
  "topics": [
    "mixing",
    "generated data",
    "semantic tags",
    "full-batch",
    "phase"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "All 36 fits completed. At 4000 inputs, balanced development agreement was 14.998% plausible-only, 15.781% with 10% intervention, 14.178% with 10% random, and 16.020% with both. The 80/10/10 gain was +1.022 pp with block deltas +1.165/+1.201/+0.701 pp, meeting the frozen advancement rule.",
  "conditions": "One-thread single-PV 100k teacher; four mixtures at 4000 inputs, phase 50/50, three disjoint training blocks and seeds 7/17/27; fixed MLP/full-batch Adam .01/200 updates; 256-row chunks. Symmetric overlap and same-spec conflict exclusions. Six-cell macro development agreement; sealed test unscored. Two-hour matrix cap after resource calibration. Amended development allocation: 373 inputs, five cells of 64 and intervention endgame 53; 3900 sealed inputs. Stop before next fit above 1.5GB process lifetime peak RSS. Calibrated 75.218-second training allowance; all 200 updates completed per fit. Matrix 928.784 seconds, maximum process lifetime peak RSS 558514176 bytes.",
  "limitations": "One generation seed, three training blocks and a shared 373-input development benchmark; initialization seeds are not independent datasets. All-block positivity is a decision rule, not significance. Coverage varies from 1632 to 2052 trajectories per case. Both exceeds intervention-only by 0.240 pp overall but loses in one block; plausible-endgame agreement declines. All cases reach 100% training agreement while development cross-entropy remains high. In-check agreement is partly constrained by 13 forced single-move positions out of 35. No correctness, scaling, default or strength claim.",
  "decision": "Advance 80/10/10 for the next exploratory balanced-data comparison; retain 90/10/0 as a close comparator. Preserve source-specific losses and existing player defaults. Scaling and semantic upweighting have not run; sealed test remains unscored.",
  "revisit": "Freeze training-only semantic enrichment and nested scaling, then separately lock confirmation before scoring the 3900 sealed inputs. Require fresh generation evidence before generalizing the sampling direction.",
  "evidence": [
    {
      "path": "data/experiments/learning/generated-source-mixing-v1-amended.json",
      "role": "config",
      "sha256": "7eb9d52ad6a383d572158eb7a82dd8eabb2857c0d33feeebba8b6b55e39b78e6"
    },
    {
      "path": "artifacts/learning/generated-source-mixing-v1-run3/plan/manifest.json",
      "role": "data",
      "sha256": "4dcb05654f6c17b7265eeee5a6af690b8776fd55051cb33a715bcdbbce446951"
    },
    {
      "path": "artifacts/learning/generated-source-mixing-v1/failure.json",
      "role": "report",
      "sha256": "b5a686dc846272dfc6e8fe538faa91f8ee605f3d324893a05718a5550954d773"
    },
    {
      "path": "artifacts/learning/generated-source-mixing-v1-run2/failure.json",
      "role": "report",
      "sha256": "13ecf382639f32ca2020a274bdc3c1e71144392486431b7b0a6889891231825a"
    },
    {
      "path": "data/experiments/learning/history/generated-source-mixing-v1.json",
      "role": "results",
      "sha256": "a0b4037db3395fa77e78877651cec6fa61ecf71ded0e86f7144f05db230faec8"
    },
    {
      "path": "artifacts/learning/generated-source-mixing-v1-run3/verification.json",
      "role": "report",
      "sha256": "af59ebb7821652275674579480c46789d8e80883d50be7694fbdc8a03473c7d5"
    },
    {
      "path": "artifacts/learning/generated-source-mixing-v1-run3/receipts.json",
      "role": "report",
      "sha256": "17af633e92dc6d51a86b11be4c3bc6528def1cadc6dd6717029b459b01951567"
    },
    {
      "path": "artifacts/learning/generated-source-mixing-v1-run3/study/source-files.json",
      "role": "source",
      "sha256": "e9b312c08bcdf0d888cbe264cae398514bbb6043ee01dc65737de8db5474883b"
    },
    {
      "path": "data/experiments/learning/generated-source-mixing-v1/summarize.py",
      "role": "source",
      "sha256": "5db4cd53d6c6132e58c650fc7df08de804f03ca165bd2ab2c41563dd18e1669e"
    }
  ],
  "prior_work": [
    {
      "id": "generated-sample-audit-v1",
      "relationship": "uses",
      "contribution": "Use measured eligible phases/policies and explicit quality exclusions to freeze the comparison."
    },
    {
      "id": "source-coverage-confirmation-v2",
      "relationship": "extends",
      "contribution": "Control source concentration under changed longer-game multi-policy supervision."
    },
    {
      "id": "teacher-quality-v1",
      "relationship": "uses",
      "contribution": "Keep preference fidelity distinct from playing strength and hold teacher identity fixed."
    }
  ],
  "novelty": "First controlled fixed-size generated-policy mixture comparison on the completed collection."
}
```
