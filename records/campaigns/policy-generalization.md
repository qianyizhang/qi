---
description: Current evidence and open questions about local policy generalization.
scope: policy generalization campaign
status: experimental
last_update: 2026-09-12
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
| Stronger labels gave mixed student-imitation results but better supporting move estimates | [Teacher-quality comparison](../work-items/items/AB-LEARN-009-teacher-quality.md): +0.955 percentage points mean agreement, block differences -0.521/+1.042/+2.344; supporting expected-score loss improved in all three blocks; 18 fits on fixed inputs with a shared 1M reference | Fresh source blocks and evaluation games under a separately locked decision rule; current result remains exploratory and inconclusive |
| Intervention mixtures improved balanced longer-game imitation, with source-specific losses | [Generated-source screen](../work-items/items/AB-LEARN-012-generated-source-mixing.md): 4000 inputs, fixed one-thread 100k labels, 36 fits; 80/10/10 improved six-cell macro agreement from 14.998% to 16.020%, positive in every training block. Random alone reduced agreement. Plausible endgame agreement fell; all cases fit training labels completely | Semantic enrichment and nested scaling under frozen source/phase ratios, followed by sealed confirmation; one generation seed and shared development set do not establish general superiority |
| Matched immediate-tag enrichment did not improve the primary metric | [Semantic enrichment](../work-items/items/AB-LEARN-013-semantic-enrichment.md): +10 pp union-tag coverage at identical trajectory contributions; 18 verified fits, 16.020% → 15.771%, two of three blocks declined. Capture and checking-move slices improved | Separately locked tag-specific hypothesis and fresh evaluation; retain natural frequencies |
| More generated inputs helped at fixed passes and fixed example presentations | [Generated-data scaling](../work-items/items/AB-LEARN-014-generated-data-scaling.md): 30 verified fits, nested 1k/4k/16k; both source cases pass both scaling rules. At 16k/50 updates, balanced agreement is 17.210% plausible-only and 18.151% mixed; the mixture loses on plausible endgames. More updates fit training labels completely but increase development cross-entropy | Sealed confirmation with source/phase slices and declared update budget; one nested pool and initialization seeds remain exploratory |
| Architecture contrasts expose action-support and optimization limits | [Architecture screen](../work-items/items/AB-LEARN-016-architecture-surfaces.md): 15 verified fits; dense heads get zero unseen-target agreement, spatial pair model transfers but has late instability and source losses. Teacher and metric probes show budget sensitivity and WDL saturation | Matched positive-support intervention with stable optimization and fresh sources; no architecture default selected |

## Unknowns

Transfer beyond the confirmed early-random-play regime; label quality; curriculum coverage; residual
overconfidence; whether imitation improvements translate into match outcomes.
Different inspected test sets cannot be compared as if they were one benchmark.

## Frontier

The [architecture report](../reports/2026-09-12-architecture-surfaces.md) recommends
[AB-LEARN-017](../work-items/items/AB-LEARN-017-action-support-transfer.md): separate
positive action coverage from transferable representation using matched support
conditions and fresh evaluation sources. Keep canonical dense and spatial models
as prespecified comparators; freeze matching, optimization/stopping controls and
budget before execution. A higher development score can coincide with unstable
training, so another unconstrained width/update sweep would explain less.

[AB-LEARN-015](../work-items/items/AB-LEARN-015-evaluation-metric-comparison.md)
retains the broader metric-validity frontier. The architecture screen's 48-input
probe demonstrates preference changes with search allocation and heavily saturated
WDL; it does not validate severity rankings against game outcomes. Use a small
prespecified panel and explicit reference-stability/paired-game evidence when
that protocol is settled. Preserve all earlier primary outcomes and the sealed
boundary. Neither follow-up is launched by this synthesis.

The earlier generated-data follow-ups still support natural-tag scaling under
both compute views. Preserve plausible-only as a source comparator: the mixture
loses in some source/phase cells. The same caution applies to the spatial model's
large random-middlegame gain and plausible-endgame loss. All 3900 sealed inputs
remain unscored; this inspected development pool cannot support confirmation.

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

- [Architecture mechanism screen](../work-items/items/AB-LEARN-016-architecture-surfaces.md).
- [Positive action support and transfer](../work-items/items/AB-LEARN-017-action-support-transfer.md).
- [Evaluation metric validity](../work-items/items/AB-LEARN-015-evaluation-metric-comparison.md).

- [Config scaffold and retrospective migration](../work-items/items/AB-LEARN-005-experiment-configs.md).
- [Teacher-quality training comparison](../work-items/items/AB-LEARN-009-teacher-quality.md).
- [Generated-source mixture screen](../work-items/items/AB-LEARN-012-generated-source-mixing.md).
- [Matched semantic enrichment](../work-items/items/AB-LEARN-013-semantic-enrichment.md).
- [Generated-data scaling](../work-items/items/AB-LEARN-014-generated-data-scaling.md).
- [Historical recipes and observations](../../data/experiments/learning/README.md).

Work-item records own execution status; this page owns only the synthesis.

## Learning ledger

2026-09-12: the architecture screen completed 15 fits and independently reloaded
30 checkpoints; all three baseline weight states exactly match the earlier
scaling controls. Dense heads fail the unseen-positive-action slice; spatial
sharing transfers to some combinations but exposes optimizer instability and
confidence growth. The 144-query teacher probe reproduces 48/48 original100k
choices, changes ten at1M, and finds substantial WDL saturation. Prioritize a
matched support intervention with stability controls; keep metric validity
separate and all3900 sealed inputs unscored. No player defaults changed.

2026-09-11: completed 18 matched enrichment and 30 nested scaling fits, each
independently verified. Enrichment fails its all-block-positive rule; retain
natural frequencies. Scaling passes all four predeclared curve rules, including
fixed presentations, while the mixture's plausible-endgame loss and the large
training/development gap persist. All 52 retained fits, including the resource
pilot and three controls from the repaired first attempt, exclude sealed inputs.
Combined charged fitting time is 45.893 minutes; no player defaults changed.

2026-09-11: all 36 generated-source fits completed and independently verified.
Both intervention-containing mixtures improved the frozen balanced metric in
all three blocks; random-only substitution reduced top-1 agreement despite
lower cross-entropy. The 80/10/10 candidate has only a 0.240 pp average margin
over intervention-only and does not beat it in every block. Preserve this
distinction, the plausible-endgame loss, and the untouched confirmation boundary.

2026-09-10: the teacher-quality comparison completed all 18 fits in 20.02 minutes.
Stronger labels improved mean shared-reference agreement by 0.955 percentage
points and reduced supporting move disadvantage in every block, but one block
failed the positive primary-direction criterion. Retain the inconclusive outcome
and existing defaults; repeatability of the supporting signal needs fresh sources.

2026-09-10: selected a controlled shallow-versus-100k teacher-label training
comparison, using the September 9 teacher-budget and MultiPV pilots as prior
evidence. AB-LEARN-009 locks identical training inputs, 18 paired fits, a shared
1M-node evaluation reference on 384 previously inspected validation positions,
and a two-hour execution allowance. This planning entry preceded the completed
exploratory result recorded above.

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
