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
| The source-coverage direction transferred to fresh blocks and holdouts | [Fresh confirmation](../work-items/items/AB-LEARN-007-fresh-source-confirmation.md): 12.91% → 14.58% agreement across three generation seeds and 6037 held-out positions; all nine pairs favored broader coverage and the predeclared rule passed | Changed teacher, phase distribution, label budget or representation; these absolute scores use a different benchmark from the exploratory comparison |

## Unknowns

Transfer beyond the confirmed early-random-play regime; label quality; curriculum coverage; residual
overconfidence; whether imitation improvements translate into match outcomes.
Different inspected test sets cannot be compared as if they were one benchmark.

## Frontier

Use broader source coverage as the working choice for the next comparable
fixed-label dataset. The [fresh confirmation](../work-items/items/AB-LEARN-007-fresh-source-confirmation.md)
passed its predeclared rule after a documented data-only pool-size amendment.
The remaining questions concern teacher quality, curriculum and representation,
and whether imitation gains translate into match outcomes. Select one variable
and lock its comparison under the [experiment method](../../docs/experiments.md)
before a further run; no new experiment is scheduled here.
[Training Data decisions](../work-items/items/AB-DATA-001-training-data-boundary.md)
own curriculum vocabulary and composition.

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

2026-09-09: fresh confirmation improved agreement by 1.67 percentage points on
average and favored broader coverage in every block and seed pair. Preserve the
original preparation shortfall and pre-fit pool amendment. The fresh result
supports the sampling direction in this regime; it does not resolve the remaining
large training/held-out gap or prove match strength.

## Closeout

Open while the bounded generalization question is being investigated. Promote
adopted behavior to the trainer guide or ADRs and close this campaign when its
remaining questions are answered or explicitly deferred.
