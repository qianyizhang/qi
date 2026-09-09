---
description: Compare equal label counts from fewer versus more source games under matched move-number coverage.
scope: backlog item
status: experimental
last_update: 2026-09-09
document_class: work_record
work_id: AB-LEARN-006
work_status: done
work_kind: research
added: 2026-09-09
tags: domain
depends_on: AB-LEARN-005
residual_of: none
residual_items: none
---

# AB-LEARN-006 — Source coverage at equal label count

## Intent

Investigate whether 768 labels from 192 games, four per game, improve teacher
imitation over 768 labels from 48 games, sixteen per game. More games means more
source diversity and fewer correlated positions per trajectory; it does not
mean adding training labels. The completed exploratory comparison found higher
held-out teacher agreement with broader coverage in all nine seed-paired fits.

## Acceptance Criteria

- Freeze prepared datasets with exact 48 × 16 and 192 × 4 contributing-source
  counts, equal move-number histograms, identical held-out examples, no input or
  source leakage, and retained selection identities. Sampling uses no teacher
  move, loss or model outcome to choose positions.
- First exploratory study: three disjoint source blocks, two cases per block,
  initialization seeds 7/17/27: 18 fixed fits. Keep the current 64-unit policy,
  full-batch Adam LR .01, 200 updates, float32 and teacher labels fixed.
- Report per-block paired differences in teacher agreement and cross-entropy,
  seed variation, actual source counts, coverage and incompleteness. Source
  resampling and initialization seeds are separate variations; do not count nine
  model seeds as nine independent datasets or checkpoint picks.
- Keep the existing inspected 4219-position holdout explicitly exploratory.
  Any later confirmatory claim uses fresh source games or a separately locked
  continuation; this comparison cannot be advertised as an untouched final test.
- Measure one representative end-to-end fit before setting the matrix allowance.
  Reporting and data preparation dominate the earlier tiny optimization timings.
  Complete the declared matrix once; do not adapt the recipe to its results.

## Context and Trade-offs

[Data scaling](AB-LEARN-004-dataset-scaling.md) changed label count and source
coverage together. [Tuning](AB-LEARN-003-local-policy-tuning.md) assessed a small-data
regime. This experiment isolates coverage more narrowly while retaining their
current model and teacher boundary.

A fixed master source pool must precede case selection. The current generator
seeds each continuation from the full SourcePlan, including `games` and `samples`;
changing those fields rerolls trajectories. The current mixture buckets constrain
split/mode/phase/theme, not exact per-source counts or global ply histograms.
The bounded Training Data adapter `selection.py` now prepares explicit historical
selections with retained input evidence and parent identity. Config runs consume
these datasets separately; cases within one recipe share a dataset. Model knobs
and optimization behavior are unchanged.

For the exploratory study, the concentrated 48 games are nested inside each
192-game block. Each pair therefore shares exactly 192 training inputs (25%).
The three broader blocks use disjoint sources. Within each block, a deterministic
integer flow selects four labels per broader source while matching the
concentrated set's exact ply counts. This is constrained sampling, not uniform
sampling of every possible matched subset. Both use only already-labeled inputs.
Matching global ply counts also matches side-to-move counts for standard starts.
It does not prove that phases, tactics or all position features are identical.

The existing full-16-label source eligibility condition and one historical
master generation seed limit generalization of the exploratory result. A later
fresh-data design can select positions before labeling, and should record
shortfalls rather than silently relax counts. Shared labels across a pair can be
queried once; a fresh test would be generated and isolated separately.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-09 | Codex | — | ready | User requested investigation after the reviewed scaffold commit; data-only audit proves a matched comparison is feasible. |
| 2026-09-09 | Codex | ready | wip | User authorized preparing the matched data, profiling and executing all 18 fixed fits. |
| 2026-09-09 | Codex | wip | done | All 18 fixed fits completed; exact selections, shared holdout, saved configs, raw metrics and checkpoints verified. |

## Implementation Ledger

### 2026-09-09 — finding: broader coverage improves this fixed-budget comparison

All 18 fits completed 200 updates. Results below average the three initialization
seeds within each of three disjoint source blocks; deltas are broader minus
concentrated. All nine paired agreement deltas are positive, and all nine
cross-entropy deltas are negative.

| Case | Training agreement | Held-out agreement | Held-out cross-entropy |
| --- | --- | --- | --- |
| 48 games × 16 labels | 100% | 14.15% | 12.31 |
| 192 games × 4 labels | 100% | 16.83% | 10.84 |

| Source block | Agreement delta (percentage points) | Initialization std of delta (pp) | Cross-entropy delta |
| --- | --- | --- | --- |
| 0 | +2.31 | 0.34 | −0.91 |
| 1 | +3.55 | 0.44 | −1.26 |
| 2 | +2.19 | 0.59 | −2.24 |

- Evidence: [complete execution summary](../../../data/experiments/learning/history/source-coverage-v1.json),
  six replay recipes under `data/experiments/learning/source-coverage-v1/`, and
  original per-fit artifacts under `artifacts/learning/source-coverage-v1/`.
  Mean agreement gain is **2.68 percentage points**; sample standard deviation
  across the three block-mean gains is **0.75 pp**. These are descriptive
  variations, not nine independent datasets or a confidence interval.
- Consequence: favor broader source coverage for the next comparable fixed-label
  dataset. Both cases perfectly fit training labels while held-out agreement
  remains low; broader sampling reduces this gap without resolving it.
- Limits: the shared 4219-position holdout was previously inspected. Selection
  uses one historical master pool, full-16-label eligible games, constrained ply
  matching, a shallow teacher and the fixed small model. This supports a working
  sampling choice in this setting; it does not establish a general four-label
  optimum, calibration improvement, or playing strength.
- Follow-up: confirm on fresh source games and an untouched holdout before a
  broader claim. Revisit the sampling choice when teacher, phase distribution,
  label budget or representation changes. No further fit is scheduled by this record.
- Verification: a separate raw-JSON pass confirmed unchanged labels, exact
  quotas and ply histograms, 576 disjoint broader sources, and common held-out
  membership. After training it checked every executed input list and preserved
  dataset, the common source identity, completed steps, checkpoint hashes and
  exact reload predictions. Independent arithmetic from raw reports reproduced
  both aggregate deltas and all nine favorable pair directions.
- Gates: final `make check` passed 366 Python tests, with one opt-in GPU skip,
  plus browser tests/build and lint/docs checks. Six selection-contract tests and
  a real saved-config/checkpoint integration test cover the new adapter.
- Review: not-required; executable checks and direct artifact verification.

### 2026-09-09 — execution lock

- Selection is the saved audit, verified by reconstructing the deterministic
  selection before materialization. Six explicit historical-selection datasets
  preserve their parent identity and the full original holdout.
- All 18 scientific configs are saved before training: blocks 0/1/2, cases
  concentrated/broader, seeds 7/17/27. CPU, one thread, source-order, 768 inputs,
  200 full-batch updates, Adam .01, float32, fixed 64-unit policy.
- Profile block 0 concentrated seed 7 first; it counts as the first of 18, with
  no duplicate fit. Only execution allowances may change after observing timing.
  The remaining fits receive three times that end-to-end duration (minimum 60,
  maximum 600 seconds). Scientific settings and selected inputs remain fixed.
- Expectations: broader coverage may improve agreement; report paired broader
  minus concentrated agreement and cross-entropy within each source block and
  initialization seed, including all complete trials regardless of direction.
- Execution helper: `scripts/run_source_coverage.py`, stages `prepare`, `profile`,
  `run`, `summarize`. Local evidence: `artifacts/learning/source-coverage-v1/`. Existing paths
  are never overwritten; a failure retains its original partial evidence.
- Profile: block 0 concentrated seed 7 completed 200 updates in 54.23 seconds
  end to end, including 3.85 seconds of optimization. The remaining 17 fits use
  162.70-second per-fit allowances. This measures runtime, not model selection.
- Six full replay recipes live under
  `data/experiments/learning/source-coverage-v1/`, grouping three seeds per dataset.
  Actual execution uses eighteen individual saved configs; the first fit retains
  its original 600-second profiling allowance. Local source bytes were archived
  before profiling; each run also records its normal source identity.

### 2026-09-09 — finding: selection feasibility

- Sequence: scaffold/review fixes committed as `93dcc77` before this investigation.
- Evidence: the verified data-scaling dataset has 792 contributing training games:
  765 have sixteen labels and 27 have fifteen. Only 32 games have at least four
  labels in every eight-ply band, so requiring that balance separately within
  each of 48 concentrated games would fail on this pool.
- Finding: three disjoint 192-game blocks are feasible with exact 768-label
  cases and matched global ply histograms. Each pair shares 192 inputs. The
  common holdout contains 4219 inputs from 264 source games; it was inspected by
  the earlier scaling study. This audit never measures imitation or strength.
- Verification: `scripts/investigate_source_coverage.py` validates the source
  dataset and solves deterministic source-to-ply flows. A separate pass re-derived
  quotas, source-block disjointness, paired overlap, exact ply histograms and
  held-out exclusion directly from selected input IDs and original labels.
- Artifacts: compact [feasibility evidence](../../../data/experiments/learning/history/source-coverage-feasibility.json);
  full selected inputs remain in ignored
  `artifacts/learning/source-coverage-investigation-v1/selection-audit.json`.
  No teacher query or training fit was run; no improvement claim is supported yet.
- Follow-up: materialize the paired datasets under Training Data ownership, profile
  one fit, then execute the fixed exploratory comparison using saved configs.
- Review: local source/selection audit; scientific result remains unmeasured.
