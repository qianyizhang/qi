---
description: Compare generated-source mixtures with fixed labels, model, phase balance and training updates.
scope: backlog item
status: experimental
last_update: 2026-09-11
document_class: work_record
work_id: AB-LEARN-012
work_status: wip
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
