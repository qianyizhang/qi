---
description: Explanatory architecture comparisons with audits of action coverage, teacher stability and evaluation resolution.
scope: architecture and learning diagnostics
status: experimental
last_update: 2026-09-22
document_class: report
report_outcome: inconclusive
inconclusive_reason: One inspected development pool and one optimizer recipe cannot establish architecture superiority or playing strength.
review_trigger: A fixed cross-metric model panel, stable move-severity references and fresh trajectory-level evaluation.
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-12"
---

# Architecture, data, teacher and metrics: what to investigate next

**Focus next on a controlled action-support experiment, with an optimizer-stability
control.** The useful finding is a distinction between memorizing supported action
labels and transferring to unsupported combinations. The spatial model shows transfer
the dense models lack, but its fixed training recipe is unstable. Teacher preference,
probability calibration and estimated move severity also disagree in informative ways.
No single aggregate settles which architecture should be adopted.

The screen completed **15 fits, 30 independently reloaded checkpoints and 144 teacher
queries**, using 15.56 charged minutes. Its three baseline weight states exactly
match the earlier generated-data study. The [retained findings](../../data/experiments/learning/history/architecture-surfaces-v1.json)
contain the complete tables and evidence receipts.

## What this comparison can explain

The [predeclared study](../work-items/items/AB-LEARN-016-architecture-surfaces.md)
uses the existing snapshot cache and full-batch gradient implementation. Every
architecture receives the same 4000 generated training inputs, 373 development
inputs, 100k-node teacher labels, Adam .01, CPU thread and 256-row chunks. Seeds
7/17/27 each run to 200 updates, retaining a checkpoint at 50. These are 15 fits
and 30 correlated checkpoint observations, not 30 independent experiments.

The development pool already informed source mixing and scaling. All results
are exploratory. All 3900 sealed inputs remain unscored; exact and mover-relative
exclusion checks passed, as did current snapshot replay and recipe verification.
The production policy and checkpoint format are unchanged.

| Contrast | What changes | What remains unresolved |
| --- | --- | --- |
| MLP64 → MLP128 | Hidden capacity; 607268 → 1206436 parameters | More compute and different optimization; width is not a cure for missing information |
| Absolute → mover-relative MLP64 | Rotate/color-swap black inputs and remap actions; same 607268 parameters | Useful coordinate sharing versus inappropriate equivalences |
| Mover-relative MLP64 → pair MLP64 | Global trunk, bilinear source/destination scoring; 279668 parameters | Sharing, interaction rank and capacity change together |
| Pair MLP64 → spatial pair CNN32 | Three shared 3×3 convolutions; same pair-score formula; 23682 parameters | Local context, parameter count and feature construction all change |

Both pair models use a 16-dimensional bilinear interaction plus source and
destination biases. The CNN sees a 7×7 neighborhood around each action endpoint;
their union can still omit intermediate or distant tactical pieces. The referee's
legal mask supplies rule information to every model. Legal output is therefore
an infrastructure guarantee, not evidence that the network learned Xiangqi rules.
No learning rate was selected separately for a model; a poor result rejects only
this tested recipe, not its entire architecture family.

## Architecture observations and competing explanations

Means below use three initialization seeds. Agreement is the six-cell macro;
cross-entropy is the micro mean in nats. Unseen-action accuracy uses each model's
own coordinates: 50 absolute development positions or 54 mover-relative positions.
Those two subsets differ, so compare unseen results within the same coordinates.

| Model | Train agreement at 200 | Dev agreement, 50 → 200 | Dev cross-entropy, 50 → 200 | Unseen agreement at 200 |
| --- | ---: | ---: | ---: | ---: |
| Absolute MLP64 | 100.00% | 16.62% → 16.32% | 8.44 → 9.93 | 0.00% of 50 |
| Absolute MLP128 | 100.00% | 17.51% → 18.22% | 9.75 → 10.52 | 0.00% of 50 |
| Mover-relative MLP64 | 100.00% | 16.98% → 15.52% | 7.89 → 9.50 | 0.00% of 54 |
| Mover-relative pair MLP64 | 100.00% | 16.47% → 16.73% | 23.24 → 21.80 | 1.23% of 54 |
| Mover-relative spatial pair CNN32 | 75.17% | 20.67% → 20.44% | 3.44 → 11.33 | 16.67% of 54 |

Generated diagnostic panels are retained locally at
`artifacts/learning/architecture-surfaces-v1/architecture-surfaces.png`.

**Capacity helps some supported decisions, but does not repair missing action
support.** Widening improves the 200-update macro by 1.90 percentage points on
average, positive in all three seed pairs (+0.52 to +2.77 pp). Both widths already
fit training perfectly by update 50 and score zero on unseen positive actions.
This extends, rather than erases, the negative small-data result in
[earlier tuning](../work-items/items/AB-LEARN-003-local-policy-tuning.md): the
teacher, data regime and evaluation have changed.

**Coordinate sharing interacts with training duration.** Mover-relative MLP64
beats the absolute MLP in all seeds at update 50 (+0.36 pp mean), then loses in
all seeds at 200 (−0.80 pp mean). A statement that canonicalization simply helps
or hurts would discard this interaction. No transformed data leakage was found.

**A pair formula alone is not the transfer mechanism.** The global pair MLP has
very low unseen-action agreement and especially poor cross-entropy. The spatial
pair model uses the same score formula but identifies 8–10 of the 54 unseen
targets per seed at update 200; the canonical dense model identifies none.
Spatial feature sharing is therefore a useful candidate explanation. Its much
smaller capacity and different optimization remain competing explanations.

**The CNN is not a clean success story.** Its 200-update training agreement ranges
from 40.10% to 98.58%, despite identical settings and data. Seed 17's training
loss rises from 0.092 at update 161 to 6.31 at update 165; its final training
accuracy is lower than at update 50. Yet that run has the highest final CNN
development macro, 22.74%. Selecting that checkpoint solely by development score
could reward an unstable trajectory. The other two seeds grow very confident
on errors: final error confidence is 82.7% and 89.2%. The bilinear score's scaling
and Adam .01 deserve investigation; this study does not identify the cause of
the instability or establish an optimal stopping rule.

**The aggregate masks source trade-offs.** At 200 updates the CNN gains most on
random middlegames: 21.88% versus baseline 2.60%, where captures are unusually
common. It loses on plausible endgames (20.83% versus 23.44%) and random endgames
(11.98% versus 13.54%). Its overall gain is not a uniform improvement in Xiangqi
competence. A possible local capture-pattern advantage needs a matched test.

## Data: action coverage, source diversity and missing history

The verified local data audit at
`artifacts/learning/architecture-surfaces-v1-data-verified/data-audit.json`
provides several explanations to test, rather than a generic claim that more data
is always better. Its compact findings are retained in the
[tracked study summary](../../data/experiments/learning/history/architecture-surfaces-v1.json).

| Surface | 4000 training inputs | Existing nested 16000 inputs |
| --- | ---: | ---: |
| Distinct contributing trajectories | 2366 | 6105 |
| Distinct positive absolute action IDs | 1374 / 8100 | 1916 / 8100 |
| Development labels unseen as positive absolute actions | 50 / 373 | 7 / 373 |
| Development labels unseen in mover-relative coordinates | 54 / 373 | 4 / 373 |
| Selected inputs with multiple retained history states | 7 / 4373 | 38 / 16373 |

All 90 source and destination squares appear positively in training; coverage is
missing in their combinations. The targets of all 50 affected development positions
(47 distinct absolute actions) were legal somewhere in training, with 5–114 exposures and median 27,
but never a positive target. Under masked hard-label cross-entropy its logit gets
no positive target gradient on those examples. Shared heads might transfer
knowledge from other actions; whether they actually do is a measured slice below.
Canonicalization alone does not automatically improve coverage: at 4k, its unseen
development count is slightly higher. The 16k audit reuses existing data and does
not add another architecture training comparison.

The evaluation set contains 131 trajectories. The ten largest supply 20.1% of
its positions; initialization seeds and nearby positions do not provide independent
dataset replications. No train/development trajectory or family overlap was found,
but all data still comes from the same generation regime. A larger row count
does not remove that limitation.

Source and phase names hide substantial differences. Median endgame ply is 104
for intervention, 136 for plausible and 249 for random sources. Random middlegames
contain teacher captures on 38/64 positions, versus 17/64 in each other middlegame
cell. Phase is a material/development heuristic. These samples do not represent
opening competence, and aggregate source gains need not transfer to ordinary play.

The teacher receives full history; the model receives only board and turn.
Different retained history states sometimes collapse to one selected input.
There are no conflicting targets among these selected histories under the chosen
teacher specification, so this is evidence of omitted information, not demonstrated
contradictory supervision. A history-aware architecture needs a controlled test
before being justified as the next fix.

## Teacher: repeatable preferences with budget and search sensitivity

The local teacher probe at
`artifacts/learning/architecture-surfaces-v1-teacher/summary.json` froze eight
development inputs per source/phase cell before querying. It kept
identical full histories and pinned engine/network bytes. All 144 fresh-session
queries succeeded and were verified offline from raw answers; query work took
75.8 seconds, with total recorded finalization at 77.6 seconds under the 900-second cap.

| Diagnostic | Observation |
| --- | ---: |
| Original versus repeated 100k single-PV choice | 48 / 48 agree |
| 100k versus 1M single-PV choice | 38 / 48 agree |
| 1M single-PV versus 1M all-legal choice | 36 / 48 agree |
| Complete common-depth all-legal tables | 48 / 48 |
| Median 1M single-PV / all-legal common depth | 22 / 12 |
| Best/second expected-score gap ≤ .01, non-forced positions | 41 / 45 |
| Pure win/draw/loss candidate triples | 932 / 1245 |

Repeatability under identical settings is good here. It does not settle reliability:
ten preferences change with budget, and spreading the same budget over all legal
moves changes twelve choices while reducing typical depth. Higher node budgets
are ceilings; forced or mate searches may finish early. Eight 1M single-PV outputs
report depth 245, another reason to avoid interpreting mean depth as effective
search effort.

WDL has limited resolution on this sample. On 24/48 positions every legal move
is within .01 of the estimated best expected score, including three forced positions.
Best expected score is exactly zero on 13 positions and one on 26. These saturated
estimates are not proof of strategically equivalent moves. Conversely, a different
top-1 label is not proof of a costly mistake. Preserve both views, explicit missing
support, mate values and cp-only comparisons. Do not turn all-legal WDL into a
universal replacement for hard labels on the strength of this pilot.

## Metrics: distinguish choice, confidence and estimated severity

Uniform random selection among legal moves scores **10.93% six-cell macro agreement**
(10.74% micro) on development. Fourteen positions are forced, including 13 of the
35 in-check positions. The uniform baseline ranges from 2.99% on random middlegames
to 18.38% on intervention middlegames. A high raw slice score can therefore reflect
fewer choices. Report non-forced accuracy and each cell's chance baseline, rather
than treating all top-1 percentages as equivalent difficulty.

A board-feature-blind baseline ranks actions by their training target frequency,
then picks the highest-ranked legal action. It reaches **14.50% macro agreement**
in absolute coordinates (12.89% mover-relative). It still receives the position's
referee mask, so this measures the contribution of action priors plus legal support,
not a position-independent player. Baseline MLP64 at 200 reaches only 16.32%.
Neural gains should be interpreted against this reference as well as uniform choice.

Removing forced positions gives 200-update micro agreement of 12.91% for baseline
MLP64, 14.86% for MLP128 and 17.18% for CNN32. The CNN's improvement therefore
survives this exclusion, while absolute scores become less flattering.

The teacher-sample table below uses the same 48 positions per model and averages
three seeds. Repeated model-position observations do not increase the sample to
144 independent positions. Expected-score loss uses the common-depth candidate
table with score `(W + .5 D) / 1000`; smaller is better under that reference.

| Model at 200 updates | Original 100k agreement | 1M single-PV agreement | Estimated expected-score loss |
| --- | ---: | ---: | ---: |
| Absolute MLP64 | 15.28% | 13.89% | .1157 |
| Absolute MLP128 | 19.44% | 18.06% | .1274 |
| Mover-relative MLP64 | 13.19% | 13.89% | .1273 |
| Mover-relative pair MLP64 | 14.58% | 13.89% | .1252 |
| Mover-relative spatial pair CNN32 | 25.69% | 26.39% | .0800 |

Two concrete disagreements matter. Widening improves top-1 while worsening this
estimated severity. For CNN32, 50 → 200 updates reduces original-label sample
agreement from 28.47% to 25.69%, and increases full-development cross-entropy from
3.44 to 11.33, yet reduces estimated expected-score loss from .1234 to .0800.
These metrics answer different questions; none should silently replace an earlier
study's primary outcome.

At update 200, 72.4–77.6% of disagreements with the original 100k label, pooled
across three seeds for each model, have estimated loss ≤ .01. Some of this could reflect acceptable alternatives, but the measured
WDL saturation and shallower candidate search prevent that conclusion. A model
ranking based on these estimates is not validated against game outcomes.

The fixed temperature-2 diagnostic divides logits by two and leaves every chosen
move unchanged. Its cross-entropy change measures a confidence effect. It is not
a fitted calibration model or evidence of better decisions. Confidence on errors,
top-3 agreement, source/destination agreement, unseen-action support and source/phase
slices provide distinct explanations; none is independently sufficient to claim
playing strength.

For example, baseline MLP64 cross-entropy falls 9.93 → 5.60 under this rescaling;
pair MLP64 falls 21.80 → 11.15. Both remain worse than uniform-legal cross-entropy
2.97. The 50-update CNN changes 3.44 → 2.77 with identical moves, crossing that
reference purely through confidence rescaling. These are diagnostics, not selected
deployment temperatures or proof that the resulting probabilities are calibrated.

## What to focus on next

| Priority | Investigation | Why it resolves more than another aggregate comparison |
| --- | --- | --- |
| **1** | [Positive action support versus representation transfer](../work-items/items/AB-LEARN-017-action-support-transfer.md) | Distinguish coverage pressure from shared-feature transfer using a matched intervention |
| **2** | [Metric validity](../work-items/items/AB-LEARN-015-evaluation-metric-comparison.md) on a small prespecified model panel | Separate stable severe mistakes from label ties/saturation, then anchor claims to paired game outcomes |
| **3** | Spatial context and optimization controls | Test whether global relations or a stable optimization recipe repair specific CNN failures without losing transfer |

For the first study, choose action groups from training data alone, then compare
matched positive-support and withheld-positive conditions for canonical dense
and spatial models. Keep row count, source/phase and trajectory contributions
comparable; retain negative legal exposure and quantify any imperfect matching.
Use fresh evaluation source games. The decisive pattern would be selective dense-head
recovery after positive coverage is added, alongside spatial transfer on groups
still lacking positives. Declare the update/fit comparison and stability control
before running it; otherwise optimization and support effects remain entangled.

The metric work should preserve raw top-1, candidate cp/mate distinctions and WDL
resolution together. A small reference-budget stability check and paired games
are more informative than ranking every saved model by one saturated score.
History features and long-range architectures remain hypotheses until error
examples demonstrate what information is missing. Another large width sweep,
more training passes or automatic data expansion would currently explain less.

## Evidence, reconstruction and verification

The [protocol and study code](../../data/experiments/learning/architecture-surfaces-v1/protocol.json)
were frozen in commit `de180bd` before the scientific run. Study weights use an
explicit experimental container; they are not loadable as production policy
checkpoints. Configs, source copies, identities, predictions, observations and
every checkpoint are retained locally. The [owner](../work-items/items/AB-LEARN-016-architecture-surfaces.md)
and catalog preserve the predeclared comparison and final assessment.

The local independent closeout at
`artifacts/learning/architecture-surfaces-v1-closeout/verification.json` checks
all 15 completed 200-update fits, 30 exact fresh-process reloads, unchanged
development targets, protected-input exclusion, three historical baseline tensor
equalities, teacher receipts and resource accounting. The scientific study used
855.95/1800 seconds; the teacher stage 77.56/900 seconds, for 933.51 seconds total.
The five one-update engineering checks used a separate 4.28 seconds and were also
reloaded. Model-process peak RSS was 493.2 MB. Mean fit times were about 24 seconds
for baseline MLP64 and 165 seconds for CNN32 despite the CNN's fewer parameters.
These times include local contention and are not isolated throughput benchmarks.

Fresh checkpoint verification took 13.36 seconds. The existing full repository
checks passed: 670 Python tests, one optional skip, five browser tests, lint,
documentation/catalog checks and production build. Nine study-specific tests
also passed. The default `make check` first hit the sandboxed uv-cache permission
boundary; it passed with the already-installed environment using
`UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/qi-uv-cache make check`. No dependency change was needed.

The first data-audit script recorded unchanged file hashes but lacked two assertions
tying the evidence database and snapshot fingerprint to the cache. Independent
review added those guards and reran into a new directory. Every diagnostic value
and supporting row remained identical; the original source and results are retained.
This is a verification hardening, not replacement training evidence.

Raw data, weights and run directories under `artifacts/` are local and ignored by
Git. The tracked summary and report preserve findings, not a backup of those files.
Reproduction requires those frozen inputs or a separately reconstructed dataset;
a new checkout alone cannot recreate this experiment.
