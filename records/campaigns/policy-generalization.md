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
| More source games at equal label count might help | [Source-coverage investigation](../work-items/items/AB-LEARN-006-source-coverage.md) proves matched selection is feasible; the learning effect remains unmeasured | Run the controlled exploratory comparison |

## Unknowns

Source-game coverage versus label count; label quality; curriculum coverage; residual
overconfidence; whether imitation improvements translate into match outcomes.
Different inspected test sets cannot be compared as if they were one benchmark.

## Frontier

Prepare the [source-coverage comparison](../work-items/items/AB-LEARN-006-source-coverage.md)
using the [experiment method](../../docs/experiments.md) and full configs.
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

## Closeout

Open while the bounded generalization question is being investigated. Promote
adopted behavior to the trainer guide or ADRs and close this campaign when its
remaining questions are answered or explicitly deferred.
