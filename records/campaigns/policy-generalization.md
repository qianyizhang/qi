---
description: Current evidence and open questions about local policy generalization.
scope: policy generalization campaign
status: experimental
last_update: 2026-09-09
document_class: coordination
---

# Policy generalization

## Destination

Understand which changes improve teacher imitation on held-out games sufficiently
to justify the next learning experiment. Playing strength remains a separate claim.

## Model relationship

Training Data assembles isolated datasets; the trainer changes weights; the policy
player chooses legal actions; the referee owns outcomes. See the [core model](../../docs/models.md).

## Current understanding

| Finding | Evidence and conditions | Revisit trigger |
| --- | --- | --- |
| The small model can fit training examples but generalization is limited | [Initial imitation](../work-items/items/AB-LEARN-001-policy-imitation.md) | New representation or materially different dataset |
| More training data improved held-out imitation | [Initial curve](../work-items/items/AB-LEARN-002-policy-generalization.md), [16× scaling](../work-items/items/AB-LEARN-004-dataset-scaling.md); fixed recipe, shallow teacher, random early-game sources | Learning curve flattens or curriculum/teacher changes |
| Tested tuning alternatives did not improve fresh-test top-1 agreement | [Tuning](../work-items/items/AB-LEARN-003-local-policy-tuning.md); small-data regime | Substantially different data scale; this is not a universal rejection of width or regularization |
| Broader source coverage improved imitation at equal label count | [Source-coverage comparison](../work-items/items/AB-LEARN-006-source-coverage.md): 14.15% → 16.83% agreement; all nine paired fits favored 192 × 4 over 48 × 16, across three source blocks; previously inspected holdout | Fresh source/holdout confirmation, or changed teacher, phase distribution, label budget or representation |

## Unknowns

Transfer of the observed source-coverage benefit; label quality; curriculum coverage; residual
overconfidence; whether imitation improvements translate into match outcomes.
Different inspected test sets cannot be compared as if they were one benchmark.

## Frontier

Use broader source coverage as the working choice for the next comparable
fixed-label dataset. The [completed comparison](../work-items/items/AB-LEARN-006-source-coverage.md)
supports a fresh-source, untouched-holdout confirmation using the
[experiment method](../../docs/experiments.md) and full configs.
[Training Data decisions](../work-items/items/AB-DATA-001-training-data-boundary.md)
own curriculum vocabulary and composition. No new training run is scheduled here.

## Work

- [Config scaffold and retrospective migration](../work-items/items/AB-LEARN-005-experiment-configs.md).
- [Historical recipes and observations](../../data/experiments/learning/README.md).

Work-item records own execution status; this page owns only the synthesis.

## Learning ledger

2026-09-09: distinguish negative tuning results at tiny scale from positive data
scaling under a fixed recipe. Preserve both findings and their conditions. An
apparent conflict should first be checked for changes in data, teacher, budget,
metric or implementation before commissioning another experiment.

2026-09-09: holding 768 labels and move-number coverage fixed, increasing source
games from 48 to 192 improved held-out agreement by 2.68 percentage points on
average. The direction held across all three source blocks and three seeds each.
Both cases memorized training labels; generalization remains limited. Preserve
the exploratory holdout boundary when using this result to choose future data.

## Closeout

Open while the bounded generalization question is being investigated. Promote
adopted behavior to the trainer guide or ADRs and close this campaign when its
remaining questions are answered or explicitly deferred.
