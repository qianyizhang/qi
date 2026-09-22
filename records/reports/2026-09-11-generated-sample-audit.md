---
description: Measured generated-data composition, provisional semantic tags and a controlled mixing/scaling proposal.
scope: generated sample audit and proposed learning experiment
status: experimental
last_update: 2026-09-22
document_class: report
report_outcome: inconclusive
inconclusive_reason: Descriptive data quality is measured, but no training comparison has run.
review_trigger: Frozen eligibility and trainer parity pass, followed by complete paired training results.
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-11"
---

# Generated samples: nature, quality and next comparison

The larger collection supports a controlled middlegame/endgame composition study.
It is not yet a training-ready dataset: recorded cross-split inputs must be
excluded, ambiguous labels resolved explicitly, and teacher specifications kept
distinct. This audit measures data properties; no student was trained and no
claim of improved playing strength follows. The training proposal below is not
a locked execution protocol.

Outcome is **inconclusive for training benefit**. Review after a frozen selection
passes the remaining eligibility checks and the proposed paired training study
produces complete results.

Subsequent execution: [AB-LEARN-012](../work-items/items/AB-LEARN-012-generated-source-mixing.md)
owns the accepted protocol, implemented tag/exclusion selection, retained data-only
amendment and completed 36-fit screen. It advances 80/10/10 for the balanced
development objective. This audit's original descriptive findings and proposal
remain historical; the follow-up record owns training conclusions.

## Evidence and prior contribution

Source: the completed collection owned by
[AB-DATA-008](../work-items/items/AB-DATA-008-generation-scaling-pilot.md).
The local-only final generation closeout at
`artifacts/learning/overnight-batches-20260911/extension-final-closeout.json`
retains replay/analysis validation through analysis 443832 and SQLite integrity
and foreign-key checks. This audit independently counts the current collection
through a read-only transaction; it does not rerun every trajectory replay.

- [Reproducible audit](../../data/experiments/learning/generated-sample-audit-v1/audit.py)
  is an analysis script, not a supported data preparation command. Run with
  `.venv/bin/python data/experiments/learning/generated-sample-audit-v1/audit.py`.
- [Retained results](../../data/experiments/learning/history/generated-sample-audit-v1.json)
  include source/specification hashes, denominators, detailed strata and limitations.
- Provisional per-input tags at
  `artifacts/learning/generated-sample-audit-v1/provisional-tags.jsonl` are local
  diagnostic output, not an exported dataset or adopted selection policy.
  The collection and this detailed output are ignored artifacts, not Git backups.

The collection was unchanged during inspection: 10000 game rows, 187727 occurrence
rows and 443832 analysis rows. Its database SHA-256 is
`5ff947c479a9a5de22446bead1d37e2bc0e71015308211a1aac77c46742a07ad`;
the WAL was empty. Independent SQL reproduced the selected occurrence/input counts,
and every selected accepted occurrence has both single-PV supervision budgets.

Prior work matters, but its regime differs:

- [policy-data-scaling-v1](../work-items/items/AB-LEARN-004-dataset-scaling.md):
  768/3072/12288 labels gave 16.74/21.27/25.70% held-out agreement under a fixed
  shallow teacher, early random play and 200 full-batch updates. Compute grew with data.
- [source-coverage-confirmation-v2](../work-items/items/AB-LEARN-007-fresh-source-confirmation.md):
  192 games × 4 labels beat 48 × 16 at equal 768 labels in all three fresh blocks;
  mean agreement rose from 12.91% to 14.58%. This did not establish four labels/game
  as universally optimal.
- [teacher-quality-v1](../work-items/items/AB-LEARN-009-teacher-quality.md): stronger
  labels improved aggregate imitation but failed the all-block-positive primary
  criterion. Supporting move estimates improved; the conclusion remains inconclusive.

The contribution here is to characterize longer legal trajectories, different
generation policies, board-based phases and paired 10k/100k labels before testing
whether composition and scale help under these changed conditions.

## What was generated

There are **9963 accepted games and 37 rejected trajectories**. Accepted game
counts are 7993 plausible, 970 intervention and 1000 random; 8982 are training
and 981 validation. There are 9810 distinct accepted full trajectories: 150 extra
training occurrences and three extra validation occurrences repeat a trajectory
within the same split. Such repetitions are retained evidence, not independent games.

The **140599 selected occurrences represent 117792 distinct model inputs**.
An occurrence is a position in one game's history; the model input is board plus
side to move. The 443832 analyses also include actor evidence and two supervision
budgets: they are not 443832 independent training examples.

| Selected phase | Occurrences | Share |
| --- | ---: | ---: |
| Opening | 9295 | 6.61% |
| Middlegame | 79112 | 56.27% |
| Endgame | 52192 | 37.12% |

Phase is the existing `mobile-material-development-v1` board heuristic, not a ply
range or a verified theoretical classification. The requested 1/8/8 phase quotas
often underfilled in endgames; do not interpret the retained ratio as a balanced
sample of all reached positions.

Two teacher/generation regimes coexist: **6963 accepted games with one engine
thread and 3000 with eight**. Six analysis specifications distinguish actor
MultiPV=3 from single-PV labels and both thread settings. The one-thread 100k
single-PV specification is
`942721450301e4969917ce4e2ece508a388f40d659e91b3e64d04e4f41e9b3a7`.
Thread changes can change engine output. These source blocks are different, so
their differences do not isolate a causal effect of thread count.

For the first study, use the larger one-thread stratum. Its policies have visibly
different characteristics:

| Policy | Nature and measured one-thread evidence |
| --- | --- |
| Plausible | Candidate-based engine play, with explicit fallbacks. Median 167 plies; 1427/5593 games reach the referee's ply limit. Only 420620/1049186 actor decisions offered more than one eligible choice, so the policy name does not guarantee diversity at each move. |
| Intervention | Teacher-best play with a seeded non-best legal deviation; applied in 650/670 accepted games. Median 71 plies. An intervention is not proof of a blunder, and later positions need their own timing tag. |
| Random | Uniformly random legal actor moves, with independent teacher labels. Median 300 plies; 486/700 games reach the ply limit. These are legal but need not resemble ordinary competitive play. |

## Quality and usable population

1. **Leakage:** 949 distinct selected inputs occur in both train and validation.
   Considering all stored accepted occurrences, including actor audits, gives
   1152 cross-split inputs; one is already reserved. There are 19591 selected
   occurrences touching this larger overlap set. `selected_only` does not bypass
   the exporter's all-occurrence lineage check.
2. **Conflicting targets:** after excluding recorded overlap and reserved inputs,
   the one-thread 100k specification has four inputs with conflicting moves
   across histories (17 occurrences); the eight-thread equivalent has 75
   (292 occurrences). Different histories can expose the same model input;
   this audit does not identify whether a conflict reflects history dependence,
   engine variability or another cause.
3. **Budget sensitivity:** 10k and 100k moves differ on 31901/101167 one-thread
   occurrences (31.53%) and 14762/39432 eight-thread occurrences (37.44%).
   For one-thread plausible/intervention/random sources separately the rates
   are 32.34/33.29/23.35%. Neither agreement nor disagreement establishes truth.
4. **Score limitations:** 39135/101167 one-thread 100k answers have bounded cp
   scores. Their moves remain usable preference labels, but those scores must
   not be treated as exact values or reliable move margins. All 101167 paired
   labels are present; missing exact scores are not missing labels.

The following **provisional census** excludes every recorded cross-split input,
reserved inputs and conflicting targets under the chosen 100k specification,
then counts each remaining input once within that specification:

| One-thread policy | Training inputs | Validation inputs |
| --- | ---: | ---: |
| Plausible | 59912 | 6404 |
| Intervention | 3508 | 346 |
| Random | 8746 | 930 |
| Total | 72166 | 7680 |

Only random sources retain opening inputs in this stratum: 433 training and
39 validation. A common phase-matched study therefore has **71733 training and
7641 validation middlegame/endgame inputs** before further checks. The absence
of plausible/intervention openings is an eligibility result, not evidence that
opening training has no value.

This is not a verified snapshot. Actual selection must preserve all source
lineage rather than the census's lowest-occurrence representative, cluster
duplicate trajectories, audit cross-block input overlap and prior external
datasets, and check quotas under the final source/game caps. All intermediate
boards not retained in the collection have not been exhaustively overlap-audited.
The two thread strata also share 24 provisionally clean inputs, so their totals
cannot be summed as one unique pool.

The current snapshot recipe exposes reserved-corpus exclusions and
mode/phase/theme/objective filters. It has no separate arbitrary input-exclusion
set or per-position semantic-tag filter. The implementation proposal must add
explicit, versioned exclusion/tag selection semantics in Training Data; do not
label rejected inputs as evaluation openings or attach transient position features
to inherited starting-position themes merely to fit existing fields.

## Semantic tags to try

Keep measured features separate from interpretation. Tags can overlap; they are
not mutually exclusive buckets unless a selection recipe explicitly makes them so.

| Axis | Proposed tags or raw values | Meaning and scope |
| --- | --- | --- |
| Position phase | `opening`, `middlegame`, `endgame`, classifier version | Existing board heuristic, recomputed per position. |
| Immediate tactical features | `in-check`, `teacher-capture`, `teacher-gives-check` | Referee board predicates and the chosen label's immediate effect. They do not assert a fork, a sound sacrifice or a forced win. |
| Material | Counts of each piece type by side; mobile-piece count | Proposed next cheap features. Preserve counts before choosing balance/endgame subtypes; these counts are not yet in the tag output. |
| Teacher value | Exact cp value/band; signed mate estimate; score bound | Initial diagnostic cp bands: below −300, within ±300, above 300 engine-native units, side-to-move perspective. Bounds/missing values stay explicit; mate is a teacher estimate. |
| Label stability | `budget-agree`, `budget-disagree`, exact specification IDs | Paired 10k/100k preference sensitivity. Do not rename these “clean/noisy” or “easy/hard.” |
| Intervention context | Not applied, before, at deviation, 1–8 plies after, 9+ after | History-specific tags using the actual intervention event. At-deviation means the board before the non-best actor action. |
| Diversity/provenance | Actor policy, source/game/trajectory identity, repeated-input count, actor fallback/eligible-choice count, teacher settings | Controls composition, clustering and interpretation; not a scalar quality score. Some values remain in collection evidence rather than the provisional tag file. |

The first three tactical predicates, cp/mate/bound bands, budget disagreement and
intervention timing were computed on the provisional clean census. For example,
teacher-capture occurs in 17.29% of one-thread plausible inputs, 22.91% of
intervention inputs and 39.80% of random inputs (train and validation combined).
Random and intervention data therefore cannot be interchanged merely as “more
diverse samples.” Most surviving one-thread intervention inputs are late:
3240/3854 are at least nine plies after the deviation; only 609 are 1–8 plies after.

Do not initially use vague tags such as “good position,” “hard tactic,” “blunder
recovery” or “winning endgame.” Tactical motifs and mistake severity need a
separately specified verifier or additional comparable engine evidence.

## Proposed experiment sequence

### First: isolate source mixture at fixed size

Use the one-thread 100k labels, **4000 distinct training inputs per case**, and
the following 2×2 replacement comparison:

| Case | Plausible | Intervention | Random |
| --- | ---: | ---: | ---: |
| Baseline | 100% | 0% | 0% |
| Add intervention | 90% | 10% | 0% |
| Add random | 90% | 0% | 10% |
| Add both | 80% | 10% | 10% |

Hold middlegame/endgame at 50/50 **within each included policy**, use deterministic
game-balanced selection with at most eight inputs/game, and record actual source
counts and concentration. The eight-label cap is a proposed practical constraint,
not an inferred optimum from the earlier four-label experiment. Use three disjoint
source blocks and initialization seeds 7/17/27: **36 fits**. These are disjoint
datasets from one master generation seed, not three independent generation seeds
or nine independent datasets per case.

Current necessary count/capacity bounds support the 4000-input proposal: each
mixed arm needs 400 intervention inputs/block, including 200 per phase. The
smallest provisional block has 771 intervention inputs under the eight/game cap
and 375 endgame inputs. This is a capacity preflight, not proof of final selection
after trajectory grouping and cross-block exclusions. Stop on shortfalls; amend
before fitting rather than silently filling from another source.

Preserve the current 64-hidden-unit float32 policy, CPU one thread, full-batch
Adam at LR .01 and 200 complete updates. No model or optimizer tuning in the
composition comparison. A bounded snapshot-to-optimizer path is still needed
under [AB-LEARN-010](../work-items/items/AB-LEARN-010-snapshot-training-protocol.md).
Recommendation: accumulate the full-dataset mean gradient in bounded chunks and
take one Adam update per pass; validate objective/gradient/update agreement with
the existing trainer on a small frozen fixture. Do not silently switch to
minibatch Adam or force new source semantics through legacy JSON export.

Split validation games/trajectory families into development and sealed test
groups before predictions, stratified by policy. Freeze input exclusions and
all evaluation weights independently of training mixtures. Primary exploratory
metric: equal-weight mean agreement over the six policy × phase development
cells. Also report population-weighted agreement, cross-entropy, every semantic
slice, denominators, source counts, train/held-out gap, runtime and memory.
Changing training composition must not change the benchmark mixture.

Rank arms using the predeclared development metric, with baseline winning exact
ties. Only advance a nonbaseline arm if its seed-mean delta is positive in every
source block; otherwise retain the baseline and the negative/inconclusive evidence.
This screen is exploratory and cannot confirm a general advantage. Test results
must not select the mixture, checkpoint, tags or thresholds. Freeze a separate
confirmation comparison before opening the sealed test results.

Proposed engineering allowance: ten minutes for a small parity/resource pilot.
Proposed screening allowance: two hours total, per-fit allowance calibrated from
the pilot and capped at ten minutes. Preserve incomplete runs and stop on invalid
selection, failed parity, resource-limit breach or deadline; do not compare
partial fits as completed 200-update results. These budgets are proposed, not launched.

### Next: test a semantic intervention

For the selected source mixture at the same size, compare its natural tactical
frequency with one preregistered enrichment of `in-check OR teacher-capture OR
teacher-gives-check`, holding policy, phase, total size and game caps fixed.
Choose the enrichment amount from training-only feasibility counts before fitting.
Keep teacher-disagreement enrichment as a separate later comparison; it would
otherwise change a second axis. Evaluate every fixed tag slice, including those
not upweighted. Tags are first diagnostic tools, then controlled interventions.

### Then: scale the baseline and selected mixture

Propose nested **1000 → 4000 → 16000** distinct-input subsets from a fixed master
training pool, each retaining the same policy/phase ratios and held-out inputs.
Recheck feasibility at the largest size; the intervention pool limits aggressive
oversampling. Use matched initialization seeds and report this as a nested curve
on one master pool, without inventing independent data repetitions.

First keep 200 full-batch updates per size. This holds passes constant and spends
more computation on more data. Then compare a fixed 800000 training-example
presentations: 800/200/50 updates at 1000/4000/16000 inputs. The second curve asks
about data size under a fixed presentation budget; it does not hold optimizer
updates constant or guarantee equal wall time. Report both resource measurements
and learning curves. Avoid combining optimizer, teacher-budget and data-size
changes into a single attribution.

The eight-thread corpus is a later separately reported regime. A small stronger
reference audit and paired full-game evaluation can follow a promising imitation
result; neither is established by the descriptive tags or this proposed screen.


```experiment
{
  "schema_version": 1,
  "id": "generated-sample-audit-v1",
  "title": "Generated sample nature and quality audit",
  "question": "What usable diversity and semantic strata does the 10000-attempt collection provide before mixing and scaling?",
  "kind": "other",
  "topics": [
    "generated data",
    "semantic tags",
    "quality",
    "mixing",
    "scaling",
    "phase",
    "label disagreement",
    "split overlap"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "Descriptive read-only census: 9963 accepted games, 140599 selected occurrences and 117792 distinct inputs. There are 949 selected cross-split inputs (1152 across all stored accepted occurrences, one reserved). Provisional one-thread 100k pool has 72166 train and 7680 validation inputs after overlap and four conflicting-target input exclusions; plausible/intervention opening support is empty. Paired 10k/100k labels disagree on 31901/101167 one-thread occurrences. Immediate tactical and teacher-evidence tags were computed; no fits ran.",
  "conditions": "Completed 10000-attempt collection with paired 10k/100k single-PV supervision, one/eight-thread regimes, standard starts, 300-ply rule and 1/8/8 requested phase sampling. Read-only stable database hash and all table high-water IDs retained. Independent SQL counts and paired coverage passed; final generation replay/integrity evidence was read, not rerun.",
  "limitations": "Descriptive support only, no demonstrated training benefit. Clean pools are provisional, not verified exports: remaining cross-block/old-dataset overlap, full lineage, trajectory clustering and quota selection checks. Phase heuristic; bounded scores not exact; budget agreement is not correctness. Source blocks share a master seed, and thread differences are confounded with source differences. No new teacher queries or model fits.",
  "decision": "Propose one-thread middlegame/endgame 4000-input composition screen: 100/0/0, 90/10/0, 90/0/10 and 80/10/10 plausible/intervention/random, then one semantic enrichment and nested scaling with fixed-pass and fixed-presentation views. Keep the training protocol proposed; resolve bounded snapshot/full-batch integration under AB-LEARN-010.",
  "revisit": "Freeze the exclusion/lineage policy and development/test split, establish quota feasibility and snapshot/trainer parity, then lock budget and execute a separately registered training comparison.",
  "evidence": [
    {
      "path": "data/experiments/learning/generated-sample-audit-v1/audit.py",
      "role": "source",
      "sha256": "647d0adaf82bef02bfeaeddb8a0efe4eb5ff24f70edc0164f3a337ae3a54b9a7"
    },
    {
      "path": "data/experiments/learning/history/generated-sample-audit-v1.json",
      "role": "results",
      "sha256": "23abf55cfe00070441180473aceda1408191cc707156af0376d71f77a51f59e8"
    },
    {
      "path": "artifacts/learning/generated-sample-audit-v1/provisional-tags.jsonl",
      "role": "results",
      "sha256": "6a64d5c3d307c712e6a4e5c329a4dd9eec551d346700a0377701a85432b68b1f"
    },
    {
      "path": "artifacts/learning/overnight-batches-20260911/extension-final-closeout.json",
      "role": "results",
      "sha256": "c20ab435c97eb2acfd6e893d7173dcd1f949844229db66b7a58a1f26582b3be5"
    }
  ],
  "prior_work": [
    {
      "id": "generation-resource-v1",
      "relationship": "extends",
      "contribution": "Characterize the completed larger collection, usable populations and semantic strata beyond resource/yield pilots."
    },
    {
      "id": "source-coverage-confirmation-v2",
      "relationship": "uses",
      "contribution": "Carry the source-concentration control into the proposed composition study without assuming transfer of the old result."
    },
    {
      "id": "policy-data-scaling-v1",
      "relationship": "extends",
      "contribution": "Propose controlled scaling on longer multi-policy trajectories and separate fixed passes from fixed example presentations."
    },
    {
      "id": "teacher-quality-v1",
      "relationship": "uses",
      "contribution": "Treat budget disagreement as diagnostic and retain the distinction between preference compatibility and playing quality."
    }
  ],
  "novelty": "First descriptive semantic/eligibility census of this completed collection; the proposed training comparisons have not run."
}
```
