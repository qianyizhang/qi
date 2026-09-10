---
description: Compare student learning under shallow and stronger teacher labels on fixed inputs.
scope: backlog item
status: experimental
last_update: 2026-09-10
document_class: work_record
produced_by: "experiment@1.0.0 · agent=gpt-6 · effort=unknown · 2026-09-10"
work_id: AB-LEARN-009
work_status: done
work_kind: research
added: 2026-09-10
tags: domain
depends_on: none
residual_of: none
residual_items: none
---

# AB-LEARN-009 — Teacher-quality training comparison

## Intent

Test whether stronger teacher labels improve student learning when training
positions and the learning recipe stay fixed. Reuse the September 9 teacher
pilots as prior evidence under the
[policy-generalization campaign](../../campaigns/policy-generalization.md).

## Acceptance Criteria

- Lock the paired training matrix, shared evaluation inputs, reference settings,
  metrics and execution allowance before new labels or student predictions.
- Compare the existing 1k-node/depth-3 labels with a 100k-node teacher candidate
  using the same pinned engine/network. Preserve identical training inputs,
  source coverage, phase distribution, representation and learning recipe.
- Evaluate both treatments against the same 1M-node reference on evaluation
  positions separate from training; declare prior test reuse explicitly.
- Retain raw teacher evidence, resolved configs, input identities, checkpoints,
  paired metrics, costs and incomplete executions. Report reference uncertainty
  and the next decision without automatic default changes.
- Keep imitation agreement distinct from playing strength and avoid attributing
  existing generalization limits to label quality without evidence.

## Context and Trade-offs

The September 9 [depth-cap pilot](../../../artifacts/pikafish-depth-cap-20260909/report.md)
already compared teacher budgets against 1M-node reference choices on 36 related
positions. The [MultiPV pilot](../../../artifacts/pikafish-multipv-20260909/report.md)
also assessed distributions, rankings and selected-move loss. Their tracked
[summary](../../../data/experiments/learning/history/teacher-generation-pilot-v1.json)
preserves compact results; detailed local artifacts may be unavailable elsewhere.
These pilots did not train students. A larger standalone teacher-budget audit is
superseded by this controlled learning comparison; preparation retains only checks
needed for that comparison. The locked matrix has executed in full, and saved
evidence has passed verification. The result is exploratory and inconclusive
under the predeclared all-block-positive criterion.

## Locked Comparison

| Dimension | Decision |
| --- | --- |
| Question | Does stronger teacher supervision improve student agreement with a shared stronger reference when training inputs and the learning recipe are fixed? |
| Training data | Reuse `artifacts/learning/source-coverage-confirmation-v2/study/datasets/block-{0,1,2}-broader.json`: 768 training positions from 192 games per block, identical between treatments. Preserve original artifacts. |
| Treatments | Existing Pikafish 1k-node/depth-3 labels versus new 100k-node labels from the same pinned engine/network. Use node-only search for the stronger treatment and reference, as in the September 9 pilot; never silently substitute the adapter's default depth cap. |
| Fixed teacher settings | Pinned Pikafish 2026-01-02, one thread, 16 MiB hash, MultiPV=1, no pondering, full history and reset search state per query. Preserve requested limits, actual work, raw output and content hashes. |
| Training matrix | Three blocks × two treatments × seeds 7/17/27 = 18 fresh fits. Rerun both treatments; do not substitute old checkpoints for the baseline. |
| Fixed learning recipe | Existing `mlp-1261-64-8100-v1`, `absolute-board-turn-v1`, legal-masked hard-label cross-entropy, full-batch Adam at 0.01, 200 updates, float32, source-order inputs, CPU and one thread. Pair initialization seeds and input order. |
| Evaluation inputs | Deterministically select one existing labeled position from each validation source game: 128 per block, 384 total. Freeze selected IDs and full histories before new teacher queries or student predictions; check exact train/evaluation observation and trajectory separation. |
| Evaluation reference | Query the same 1M-node single-PV teacher for all treatments. Evaluate each block's six final checkpoints on that block's same 128 reference positions. Reference labels never enter optimizer updates or checkpoint selection. |
| Primary measure | Per-block, initialization-seed-averaged stronger-minus-shallow student agreement with the 1M reference; report all paired seeds and the equally weighted block mean. |
| Supporting measures | Cross-entropy against those same reference labels, teacher/preparation/training costs, and reference-assessed student-move disadvantages. Retain per-position predictions. Reuse the existing common-position candidate-assessment approach, keeping its search allocation and reference identity distinct from the single-PV reference. |
| Interpretation | Exploratory: these validation games were previously inspected. Three source blocks, not nine seeds or 384 positions, supply the independent generation-block variation. A stronger reference is an estimate, and imitation improvement is not playing-strength evidence. |
| Decision rule | Promising only when all three block mean agreement deltas are positive and supporting move assessment shows no consistent deterioration across blocks. Mixed primary directions or incomplete supporting coverage remain inconclusive; no automatic production-default change. |
| Allowance | Two hours for preparation, all fits and evaluation together. Bound individual work by the remaining allowance, retain partial work and errors, and report actual wall time including any bounded operation/cleanup overrun. Never shrink the matrix or evaluation set silently. |

For supporting candidate assessments, preserve common-position, common-depth
complete candidate scores, score perspective and bound flags. Keep mate results
separate from numeric centipawn gaps; unknown or incomplete comparisons are not
zero loss. Report valid/unknown denominators and use matched evaluable positions
when comparing treatments. A consistent deterioration means the stronger treatment
has worse seed-mean move-disadvantage in every block under the frozen supporting
measure; insufficient coverage cannot certify its absence. Freeze that measure
and its handling of mate/unknown cases in the run protocol before predictions.

Implementation must retain a resolved protocol, selected input IDs, parent and
teacher hashes, derived data provenance, complete per-fit configs, raw teacher
answers, checkpoints and recomputable results. Verify the label-only treatment
change, paired input/seed parity, shared-reference evaluation, failed/incomplete
denominators and checkpoint reload behavior. Run focused checks and `make check`.
Commit or preserve the exact executed source before relying on its identity.

## Observed result

All 18 fits completed 200 updates, using 3,456 fresh teacher queries, in
1,201.08 seconds (20.02 minutes) against the 7,200-second allowance. All 384
evaluation positions have complete exact common-depth candidate scores; no
queries or fits failed, and no planned input was dropped.

| Source block | Shallow student agreement | Stronger student agreement | Difference (percentage points) | Expected-score-loss difference |
| --- | --- | --- | --- | --- |
| 0 | 15.885% | 15.365% | -0.521 | -0.018698 |
| 1 | 13.021% | 14.063% | +1.042 | -0.012130 |
| 2 | 17.969% | 20.313% | +2.344 | -0.025169 |
| Equal block mean | 15.625% | 16.580% | +0.955 | -0.018666 |

Rows average seeds 7/17/27; each seed uses the same 128 evaluation positions in
its block. Lower expected-score loss is better. All nine paired seeds improved
this supporting measure, but initialization pairs are not independent datasets.
Shared-reference cross-entropy differences were +1.7855, -0.1243 and -0.0244
nats in the three blocks, respectively (lower is better).

The teacher intervention changed 865/2,304 training labels. On the shared 384
validation positions, shallow versus stronger teacher agreement with the 1M
reference was 246/384 (64.06%) versus 329/384 (85.68%). Every student fit reached
100% agreement with its own training labels; this does not establish held-out
generalization. Median complete all-legal reference depth was 11 in each block,
versus median reported single-PV reference depth 20 across the full sample.

[Compact results](../../../data/experiments/learning/history/teacher-quality-v1.json)
retain paired seeds, teacher changes, query costs and source identities.
[Raw run evidence](../../../artifacts/learning/teacher-quality-v1/status.json),
[file receipts](../../../artifacts/learning/teacher-quality-v1/receipts.json),
[verification](../../../artifacts/learning/teacher-quality-v1-verification.json)
and the [aggregate audit script](../../../artifacts/learning/teacher-quality-v1-observations.py)
remain local. The executed Python source and dependency files are preserved under
the run's `source/` directory with individual hashes; original checkout provenance
is also retained under `artifacts/learning/teacher-quality-execution-v1/`.
These ignored artifacts are required for detailed reconstruction; Git contains
the protocol, implementation and compact findings, not the datasets or weights.

**Inconclusive under the locked rule:** block 0's primary agreement difference
is negative, so the all-block-positive criterion is unmet. Supporting move-quality
estimates improve consistently; this is a useful exploratory signal, not grounds
to change the declared criterion or claim playing strength. Keep existing defaults.
Revisit with a separately locked study on fresh source blocks and evaluation
games to test whether the observed move-quality improvement repeats; retain both
agreement and candidate-score measurements and predeclare which governs decisions.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | Capture the larger teacher-quality review proposal for later selection. |
| 2026-09-10 | Codex | deferred | ready | User accepted the controlled training matrix, shared evaluation sample, success criterion and two-hour allowance after reconciling prior teacher pilots. |
| 2026-09-10 | Codex | ready | wip | User authorized implementation and execution of the locked comparison. |
| 2026-09-10 | Codex | wip | done | Completed and verified 18/18 fits and 3,456/3,456 teacher queries in 20.02 minutes; the primary criterion is unmet, so retain the inconclusive result and existing defaults. |

## Implementation Ledger

### 2026-09-10 — cleanup: verification and superseded instructions

- Reject conflicting CLI modes and invalid/equivalent PyTorch seeds before
  preparation; expose run failures without a traceback. Verification reports
  progress, uses one CPU thread and restores the caller's thread setting.
- Require receipts for consumed evidence and validate raw query input identities.
  Empty preflight failures report the narrower `preflight-failure-receipts` scope.
  Superseded audit instructions and the earlier running catalog revision remain
  available in collapsed historical sections; supported legacy readers remain.
- `make check`: 478 Python tests passed, one opt-in MPS skip, five browser tests
  passed. Rechecking all existing checkpoints and teacher evidence produced an
  identical [verification result](../../../artifacts/learning/teacher-quality-v1-cleanup-verification.json).
  This cleanup ran no new training or teacher queries and changes no finding.

### 2026-09-10 — verification: complete execution, mixed learning signal

- Frozen source executed the exact matrix. The saved-evidence verifier reloaded
  all checkpoints, regenerated selections and relabeled data, reconstructed
  candidate estimates, and reproduced predictions, reference metrics and summaries.
  A separate raw-query audit checked full-history input identity, fixed settings,
  zero invalid actions and zero retries across all 3,456 answers.
- All 18 fits completed 200 updates and preserved equal reload predictions.
  `make check` passed: 473 Python tests, one opt-in MPS skip, five browser tests,
  Ruff/format/docs/catalog checks, TypeScript checks and production builds.
- No protocol deviation, failed attempt or missing support occurred. The catalog
  registration was added during execution when the experiment-recall workflow
  landed; the work-item protocol, source snapshot and input manifest were frozen
  before teacher queries. Preserve that chronology instead of claiming the new
  catalog entry itself predates execution.
- Review: complete implementation and evidence; inconclusive under the locked
  decision rule. Keep defaults and require a new predeclared fresh-source protocol
  before treating the supporting move-quality signal as repeatable.

### 2026-09-10 — implementation: bounded paired comparison

- The [executable study](../../../data/experiments/learning/teacher-quality-v1.json)
  pins parent file hashes, teacher assets, sample counts, seeds and allowance.
  Run `uv run python scripts/run_teacher_quality.py --config
  data/experiments/learning/teacher-quality-v1.json --output
  artifacts/learning/teacher-quality-v1` into a fresh directory. Verify saved
  evidence with the same script's `--verify --output` options.
- Deterministic validation selection uses the minimum canonical SHA-256 of
  `[910, block, source_id, input_sha256]` per game. The protocol and exact IDs
  precede teacher queries. Both cases use all original training inputs in order.
- Supporting loss is the best minus chosen engine-estimated `W + 0.5D` from
  complete, exact, common-depth all-legal MultiPV at 1M nodes with WDL enabled.
  This reallocates the node budget relative to single-PV; it is a separate
  estimate. Centipawn gaps require all-cp scores; mate values remain separate.
  Unknown coverage cannot satisfy the promising criterion.
- Strong dataset validation labels are also relabeled at 100k to retain the
  dataset's uniform supervision invariant. Its internal validation metrics are
  diagnostics. Only the separate shared 1M evaluation compares treatments;
  reference labels never enter fitting or checkpoint selection.
- Raw queries are flushed individually. Failures retain partial evidence and
  planned denominators. The verifier reconstructs selection, derived labels,
  candidate scores, checkpoint predictions, reference metrics and paired summaries.

<details>
<summary>Superseded audit proposal and scope transition — historical decisions only</summary>

The standalone audit below was replaced by the Locked Comparison above. Its
open follow-ups describe the earlier discussion, not outstanding work.

### 2026-09-10 — decision: audit sample, allowance and initial measures

- Evidence: user accepted the recommended position sample and initial quality
  measures, and proposed increasing the wall-time allowance to two hours.
- Consequence: select 192 existing training positions from the broader-coverage
  confirmation datasets: 64 per source block, one per source game, balanced over
  move-number ranges. Selection must be frozen before new teacher results.
  Retain move agreement, search cost and deeper disagreement assessment; richer
  measures can be considered later. The total audit allowance is two hours,
  including disagreement assessment, with incomplete evidence preserved.
- Clarification: the proposed ladder retains the original 1k-node/depth-3
  teacher and compares 1k/10k/100k/1M nodes at a depth-64 ceiling using the same
  pinned engine/network. The 1M result is a reference estimate, not a guaranteed
  upper bound or referee truth. This item audits teachers before any separately
  scoped student-training comparison.
- Follow-up: settle disagreement scoring and the recommendation rule, then
  finalize the executable protocol. No teacher queries or training have started.
- Review: ratified for sample, allowance and measurement direction; ladder/scope
  clarification and remaining method details are still under discussion.

### 2026-09-10 — decision: proceed from teacher pilots to student learning

- Evidence: user identified the overlap with yesterday's experiments and accepted
  the recommendation to compare students trained with shallow versus stronger
  labels while holding inputs and the learning recipe fixed.
- Consequence: rescope this item to the controlled training comparison. The earlier
  standalone 192-position teacher audit and full budget ladder are superseded;
  the two-hour allowance is the proposed bound for the new end-to-end experiment.
  Yesterday's pilot supports 100k nodes as a candidate, not an established optimum.
- Follow-up: lock matrix size, evaluation selection and the primary comparison
  measure. No new teacher queries, fitting or implementation have begun.
- Review: ratified for the change of direction; execution details remain open.

</details>

### 2026-09-10 — decision: controlled training protocol locked

- Evidence: user answered "yes" to the recommended 18-fit matrix, 384-position
  shared evaluation sample, primary/supporting measures and two-hour total bound.
  Read-only inspection confirmed each available broader-coverage dataset contains
  768 training labels from 192 games and 128 validation games.
- Consequence: the Locked Comparison above governs implementation. Reuse the
  existing learning recipe and teacher pilots; this is an exploratory label-only
  treatment comparison, with no new sampling regime or model tuning.
- Follow-up: implement the bounded preparation/evaluation support, freeze the
  exact input selection and executable protocol, then execute the fixed matrix
  when proceeding from this interview. No further product-scope decision is open.
- Review: ratified; no additional confirmation of these decisions is required.


## Catalog revisions

<details>
<summary>Revision 1 — running (superseded by the completed revision below)</summary>

```experiment
{
  "schema_version": 1,
  "id": "teacher-quality-v1",
  "title": "Controlled teacher-label student comparison",
  "question": "Do 100k-node labels improve students on fixed inputs against a shared 1M-node reference?",
  "kind": "learning",
  "topics": [
    "teacher quality",
    "stronger teacher",
    "paired students",
    "1M reference",
    "fixed training inputs"
  ],
  "execution": "running",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Three reused broader-coverage blocks; 768 train positions from 192 games each; shallow 1k/depth3 versus node-only 100k labels; seeds 7/17/27; 18 fresh CPU one-thread fits, fixed MLP, Adam .01 and 200 updates. Shared single-PV 1M evaluation on 128 frozen validation positions per block; separate all-legal MultiPV/WDL support. Total allowance 7200 seconds.",
  "limitations": "Exploratory reuse of inspected validation source games. Three source blocks, not nine independent seed pairs. Engine estimates are not truth or a proven upper bound; no playing-strength conclusion.",
  "decision": "Execute the user-ratified matrix and retain incomplete work; no automatic defaults.",
  "revisit": "Assess the complete paired block differences and candidate-score coverage after saved-evidence verification.",
  "evidence": [
    {
      "path": "data/experiments/learning/teacher-quality-v1.json",
      "role": "config",
      "sha256": "8b234f57d0a4e5e9a7cd7d9ad79c71d936e3333869b9bf897acde49df113f7c4"
    },
    {
      "path": "artifacts/learning/teacher-quality-v1/protocol.json",
      "role": "config",
      "sha256": "40c299fdebd320897b934752e4ad02db51055ca0c9a6e191a71ca18d0ae8ef47"
    }
  ],
  "prior_work": [
    {
      "id": "teacher-budget-20260909",
      "relationship": "extends",
      "contribution": "Moves from teacher-budget agreement to downstream students on identical training inputs."
    },
    {
      "id": "teacher-multipv-20260909",
      "relationship": "uses",
      "contribution": "Uses complete common-depth exact all-legal WDL estimates as separate supporting move assessments."
    }
  ],
  "novelty": "Prior pilots compared teacher answers without training students. This study isolates label budget in paired student fits and uses one shared stronger evaluator."
}
```

</details>

### Revision 2 — completed finding



```experiment
{
  "schema_version": 1,
  "id": "teacher-quality-v1",
  "title": "Controlled teacher-label student comparison",
  "question": "Do 100k-node labels improve students on fixed inputs against a shared 1M-node reference?",
  "kind": "learning",
  "topics": [
    "teacher quality",
    "stronger teacher",
    "paired students",
    "1M reference",
    "fixed training inputs"
  ],
  "execution": "complete",
  "conclusion": "inconclusive",
  "finding": "18/18 paired fits and 3456/3456 queries completed in 1201.08 seconds. Mean student agreement rose from 15.625% to 16.580% (+0.955 percentage points); block differences were -0.521/+1.042/+2.344 points. Expected-score-loss differences were -0.018698/-0.012130/-0.025169, with all 384 candidate sets complete. Saved checkpoint predictions, metrics and summaries reproduced. The all-block-positive primary criterion was unmet.",
  "conditions": "Three reused broader-coverage blocks; 768 train positions from 192 games each; shallow 1k/depth3 versus node-only 100k labels; seeds 7/17/27; 18 fresh CPU one-thread fits, fixed MLP, Adam .01 and 200 updates. Shared single-PV 1M evaluation on 128 frozen validation positions per block; separate all-legal MultiPV/WDL support. Total allowance 7200 seconds.",
  "limitations": "Exploratory reuse of inspected validation source games. Three source blocks, not nine independent seed pairs. Engine estimates are not truth or a proven upper bound; no playing-strength conclusion.",
  "decision": "Keep existing defaults. Retain the consistent supporting move-quality signal as exploratory; do not change the primary criterion after seeing results.",
  "revisit": "A separately locked comparison on fresh source blocks and evaluation games, predeclaring whether agreement or candidate move quality governs decisions.",
  "evidence": [
    {
      "path": "data/experiments/learning/teacher-quality-v1.json",
      "role": "config",
      "sha256": "8b234f57d0a4e5e9a7cd7d9ad79c71d936e3333869b9bf897acde49df113f7c4"
    },
    {
      "path": "data/experiments/learning/history/teacher-quality-v1.json",
      "role": "results",
      "sha256": "795920e5ebe0d00ab1fed1db606cfc56a591389f52d96066346ff4f38a435a4d"
    },
    {
      "path": "artifacts/learning/teacher-quality-v1/protocol.json",
      "role": "config",
      "sha256": "40c299fdebd320897b934752e4ad02db51055ca0c9a6e191a71ca18d0ae8ef47"
    },
    {
      "path": "artifacts/learning/teacher-quality-v1/status.json",
      "role": "run",
      "sha256": "d7aa1763526052cf21a393fec263754316d1305d1027a52de809c006c8b1525b"
    },
    {
      "path": "artifacts/learning/teacher-quality-v1/receipts.json",
      "role": "results",
      "sha256": "7fad9d4cd276efbab41c798fb113c26a9371cf5b694d44219d69d5253810fece"
    },
    {
      "path": "artifacts/learning/teacher-quality-v1/source.json",
      "role": "source",
      "sha256": "a020c49a00d4391960b08f2987f91471c617d9db78142b5dde81d257bcac3757"
    },
    {
      "path": "artifacts/learning/teacher-quality-v1-verification.json",
      "role": "results",
      "sha256": "5ce3275fafad6451e971521487ea0b7c2d1039e2794b517d995c65b39043cf87"
    },
    {
      "path": "artifacts/learning/teacher-quality-v1-observations.py",
      "role": "source",
      "sha256": "6882145cde5593f149c866125d30717fc9b5af8b2efe75e769976ac4eed43d11"
    },
    {
      "path": "artifacts/learning/teacher-quality-v1-check.log",
      "role": "results",
      "sha256": "f50a9e878a3b07453a1df4a066393596a2ce3dba4b1b2307c13cff51cd6869fe"
    }
  ],
  "prior_work": [
    {
      "id": "teacher-budget-20260909",
      "relationship": "extends",
      "contribution": "Moves from teacher-budget agreement to downstream students on identical training inputs."
    },
    {
      "id": "teacher-multipv-20260909",
      "relationship": "uses",
      "contribution": "Uses complete common-depth exact all-legal WDL estimates as separate supporting move assessments."
    }
  ],
  "novelty": "Prior pilots compared teacher answers without training students. This study isolates label budget in paired student fits and uses one shared stronger evaluator."
}
```
