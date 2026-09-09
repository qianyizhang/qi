---
description: Compare equal label counts from fewer versus more source games under matched move-number coverage.
scope: backlog item
status: experimental
last_update: 2026-09-09
document_class: work_record
work_id: AB-LEARN-006
work_status: ready
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
mean adding training labels. This item owns the proposed learning comparison;
the completed investigation below establishes selection feasibility only.

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
The minimal next implementation is a bounded Training Data selection/preparation
step with explicit selected-input evidence. Do not add model knobs or change
training to enforce dataset composition. Existing config runs can consume the
resulting prepared datasets separately; cases within one recipe share a dataset.

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

## Implementation Ledger

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
