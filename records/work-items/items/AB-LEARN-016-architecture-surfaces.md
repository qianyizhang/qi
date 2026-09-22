---
description: Explore policy architecture mechanisms alongside data, teacher and metric limitations.
scope: backlog item
status: experimental
last_update: 2026-09-22
document_class: work_record
work_id: AB-LEARN-016
work_status: done
work_kind: research
added: 2026-09-12
tags: domain
depends_on: AB-LEARN-014
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-12"
---

# AB-LEARN-016 — Architecture and diagnostic surfaces

## Intent

Use the existing frozen-data and training scaffolding to learn why policy models
behave differently. The user authorized architecture experiments and a consolidated
report investigating data, teacher and metric shortcomings. This is an exploratory
mechanism screen; it neither selects a production default nor claims playing strength.
The broader saved-model/game-validity comparison in [AB-LEARN-015](AB-LEARN-015-evaluation-metric-comparison.md)
retains its separate unresolved protocol.

## Acceptance Criteria

- Freeze five cases × seeds 7/17/27 on the existing mixed-4000 snapshot and its
  373 inspected development inputs. Preserve all 3900 sealed inputs unscored.
  Hash/replay/cache and transformed-input exclusion checks precede fitting.
- Reuse `SnapshotTensors` and full-batch `accumulated_step`; Adam .01, CPU one
  thread, float32, chunks 256. Observe updates 50 and 200 from each fit: 15 fits,
  30 correlated checkpoints. No setting selection from intermediate results.
- Contrast absolute MLP64 with MLP128 (capacity), canonical MLP64 (coordinate
  sharing), canonical MLP64 with bilinear source/destination scores (head
  structure), and canonical conv32 with the same scoring formula (spatial
  sharing). Report parameters, runtime and unresolved capacity/optimizer confounds.
- Diagnose train/development loss and agreement; six-cell macro and micro;
  forced/non-forced positions, legal-choice baseline, action-frequency strata,
  source/phase and confidence. Compare source/destination decisions where useful.
  Fixed temperatures 1 and 2 diagnose calibration with identical argmax moves;
  neither temperature is fitted or selected. This was added before fitting.
- Before any teacher query, freeze eight development inputs per source/phase cell
  using ascending SHA256(`architecture-surfaces-v1:` + input_hash). On these 48
  histories compare fresh 100k and 1M single-PV searches and 1M all-legal MultiPV
  WDL, one thread, Hash16, no depth cap, 20s per-query timeout. Retain raw answers,
  bounds, actual depths, missing assessments, label changes, near ties and WDL
  saturation. Higher-budget estimates are diagnostic references, not ground truth.
- Maximum 1800 seconds cumulative fitting including failed scientific fits,
  600 seconds per fit; 900 seconds teacher stage including failures. Stop before
  another unit when allowance is exhausted, on integrity failure/nonfinite loss,
  or process peak RSS over 1.5GB. Retain partial work; no automatic extension.
  Preparation, engineering checks and offline verification are timed separately.
- Retain source copies, resolved configs, raw per-input observations, weights,
  failed/partial attempts and receipts. Independently reload every completed
  checkpoint, rederive findings, validate the catalog and run repository checks.
- Deliver a report distinguishing observations, explanations and unresolved
  alternatives, and rank the next investigations by explanatory value.

## Context and Trade-offs

[Earlier tuning](AB-LEARN-003-local-policy-tuning.md) found that wider and
mover-relative alternatives did not transfer in the small shallow-label regime.
[Generated scaling](AB-LEARN-014-generated-data-scaling.md) changed the data and
teacher, found useful scaling, and exposed memorization and overconfidence.
[Teacher quality](AB-LEARN-009-teacher-quality.md) found mixed agreement gains but
improved supporting move estimates. This study revisits representation under the
changed regime and couples it to explanatory diagnostics; earlier criteria and
outcomes remain unchanged.

Predictions before fitting: widening may improve fit without addressing sparse
action supervision; coordinate/head sharing may help rare actions but constrain
useful interactions; spatial sharing may generalize efficiently while a small
receptive field misses long-range rook/cannon relations. Canonicalization may add
input aliases, so exclusions must be checked in that equivalence class. The
board-and-turn encoding omits history available to the teacher. Shared architecture
scores and hard-label cross-entropy cannot distinguish near-equal moves from blunders.

The decision rule is explanatory, not a winning-score threshold: prioritize a
mechanism only when its expected diagnostic pattern appears across paired seeds,
and state conflicting slices. A single higher aggregate justifies no adoption.
All cases use one recipe, one training pool and a repeatedly inspected development
set. Seeds probe initialization, not independent datasets. Equal updates do not
equalize compute; a poor fixed-recipe result does not reject an architecture family.
The [protocol](../../../data/experiments/learning/architecture-surfaces-v1/protocol.json)
pins local inputs and execution settings; study weights stay outside production
checkpoint formats. No new generation, cloud spending or match-outcome claim is
part of this screen.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-12 | Codex | — | wip | User authorized a bounded architecture and diagnostic exploration; protocol recorded before execution. |
| 2026-09-12 | Codex | wip | done | 15 fits, 30 checkpoint reloads and 144 teacher queries verified; consolidated findings and next focus recorded. |

## Implementation Ledger

### 2026-09-12 — decision: predeclared exploratory screen

- Evidence: protocol and prior-work links above; existing frozen cache has 4000
  training and 373 development rows, one-thread 100k labels.
- Consequence: five contrasts and diagnostic sample are fixed before scores;
  explanation and next-focus selection are the deliverables.
- Follow-up: preserve all attempted work and consolidate observed mechanisms.
- Review: not-required; authorized research scope, no production adoption.


```experiment
{
  "schema_version": 1,
  "id": "architecture-surfaces-v1",
  "title": "Architecture mechanisms and diagnostic surfaces",
  "question": "Which architecture, data, teacher and metric mechanisms explain the observed imitation limits?",
  "kind": "learning",
  "topics": [
    "architecture",
    "representation",
    "teacher",
    "metrics",
    "data coverage",
    "mechanism",
    "generalization"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Five architectures, seeds7/17/27, mixed4000 train +373 inspected development; updates50/200, Adam.01 CPU1. 48 stratified teacher inputs,100k/1M SPV and1M alllegal.1800s fits+900s queries.3900 sealed inputs excluded.",
  "limitations": "Exploratory one-pool fixed-recipe study; no model default or playing strength.",
  "decision": "Execute fixed contrasts and diagnose limitations; choose next focus from explained patterns.",
  "revisit": "After verified evidence and consolidated report.",
  "evidence": [
    {
      "path": "data/experiments/learning/architecture-surfaces-v1/protocol.json",
      "role": "config",
      "sha256": null
    }
  ],
  "prior_work": [
    {
      "id": "policy-tuning-v1",
      "relationship": "extends",
      "contribution": "Revisit capacity and coordinate sharing on changed generated100k-label regime."
    },
    {
      "id": "generated-data-scaling-v1",
      "relationship": "uses",
      "contribution": "Reuse frozen4k inputs and inspected development to investigate representation rather than scale."
    },
    {
      "id": "teacher-quality-v1",
      "relationship": "extends",
      "contribution": "Diagnose reference instability and metric disagreement on fixed development sample."
    }
  ],
  "novelty": "Couple architecture contrasts to action support, choice difficulty, confidence and teacher stability diagnostics; explain mechanisms rather than optimize one metric."
}
```

### 2026-09-12 — finding: separate action support, transfer and confidence

- Evidence: [consolidated report](../../reports/2026-09-12-architecture-surfaces.md),
  [retained findings](../../../data/experiments/learning/history/architecture-surfaces-v1.json)
  and local-only independent closeout
  `artifacts/learning/architecture-surfaces-v1-closeout/verification.json`.
- Consequence: dense models fit training but identify no unseen positive targets;
  spatial sharing transfers to some unseen combinations, while the fixed CNN
  recipe has late instability and cross-entropy trade-offs. Width and coordinate
  effects depend on update count. Teacher preference, WDL severity and confidence
  measures do not provide interchangeable rankings.
- Follow-up: prioritize [AB-LEARN-017](AB-LEARN-017-action-support-transfer.md)
  for a matched support intervention with stability controls; retain
  [AB-LEARN-015](AB-LEARN-015-evaluation-metric-comparison.md) for metric validity.
  No architecture or player default promotion.
- Review: not-required; exploratory findings, limits and competing explanations retained.

### 2026-09-12 — verification: complete matrix and protected evidence

- Evidence: 15/15 completed fits, 30/30 exact fresh-process checkpoint reloads,
  three historical baseline tensor equalities and 144/144 successful teacher
  queries. All 3900 sealed inputs remain unscored; original and canonical
  exclusions pass. Scientific plus teacher runtime is 933.51 seconds; model
  peak RSS 493.2 MB. Five one-update engineering checks are separate.
- Consequence: measured results are reproducible within the retained local
  environment, not a cross-platform or playing-strength claim. A finite
  completed fit may still exhibit poor optimization, as CNN seed 17 does.
- Follow-up: preserve local ignored inputs, weights and raw outputs. Full repo
  checks passed (670 Python tests, one optional skip, five browser tests and
  build); nine dedicated study tests, script Ruff and catalog checks also pass.
- Review: not-required.

### 2026-09-12 — deviation: strengthen descriptive audit identity checks

- Evidence: original data audit retained unchanged before/after hashes but lacked
  cache-to-snapshot and snapshot-to-database assertions. Independent review added
  them and reran into `architecture-surfaces-v1-data-verified`; all diagnostics
  and supporting rows are unchanged. Full snapshot replay/selection also passed.
- Consequence: original evidence/source retained; no training or teacher setting
  changed and no scientific rerun was needed.
- Follow-up: use the strengthened audit for reconstruction.
- Review: ratified.


```experiment
{
  "schema_version": 1,
  "id": "architecture-surfaces-v1",
  "title": "Architecture mechanisms and diagnostic surfaces",
  "question": "Which architecture, data, teacher and metric mechanisms explain the observed imitation limits?",
  "kind": "learning",
  "topics": [
    "architecture",
    "representation",
    "teacher",
    "metrics",
    "data coverage",
    "mechanism",
    "generalization"
  ],
  "execution": "complete",
  "conclusion": "mixed",
  "finding": "15 fits and 30 exact checkpoint reloads. At 200 updates: macro 16.324% baseline, 18.219% wider, 15.525% canonical dense, 16.726% canonical pair, 20.444% spatial pair. Dense unseen-target accuracy is zero; spatial is 16.667% on 54 canonical development positions. CNN seed 17 destabilizes late despite the highest final CNN development score. 144 teacher queries reproduce all 48 original 100k moves; ten change at 1M and WDL saturates.",
  "conditions": "Frozen mixed 4000 training and 373 inspected development inputs; seeds 7/17/27; five models; 50/200 correlated checkpoints; Adam .01 CPU one thread, full-batch chunks 256. 48 stratified full histories; 100k/1M single-PV and 1M all-legal. 3900 sealed inputs unscored.",
  "limitations": "One training pool and reused development; initialization seeds are not dataset repetitions. Architecture capacity/optimization confounds persist. Absolute 50/canonical 54 unseen slices differ. Teacher WDL is saturated and all-legal search shallower; no game outcomes. 855.95s models plus 77.56s teacher; timings include host contention.",
  "decision": "Prioritize AB-LEARN-017 controlled positive-action support versus representation transfer with stability controls;retain AB-LEARN-015 metric validity. No architecture or player-default promotion.",
  "revisit": "Fresh source games under matched support intervention;declared optimizer/update controls and stable move-severity references with paired game outcomes.",
  "evidence": [
    {
      "path": "records/reports/2026-09-12-architecture-surfaces.md",
      "role": "report",
      "sha256": "541507fbcbf291bb145a6fc7251a047e47108c70bc944753b9cfa2ce59db64c6"
    },
    {
      "path": "data/experiments/learning/architecture-surfaces-v1/protocol.json",
      "role": "config",
      "sha256": "cc91f1a01e7f40480eccc0e2d906bcc6085cf7419b747688da19ed726108a9a6"
    },
    {
      "path": "data/experiments/learning/history/architecture-surfaces-v1.json",
      "role": "results",
      "sha256": "78c797b65e3b3321a9d87e073d801d4d1e22b95630f68f05b13f1ea04cda7bae"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1-closeout/verification.json",
      "role": "results",
      "sha256": "0aee897c4a23809973310d7f24011309530740e21dbd449f35d1c930afcf2907"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1/analysis.json",
      "role": "results",
      "sha256": "7e7697c0de09f27e25ec4c607b69e99b2e61f51a692313a43e2c6ebede9c4c71"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1/study/lineage.json",
      "role": "source",
      "sha256": "3a4b5a21c2092a51494e8523e163b221a9b00a8b1f411fe9ecef893fc9411348"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1/study/verification-32724.json",
      "role": "results",
      "sha256": "799c555f61c8533e1839bbf74a7d9f1045e02722266874406317f7ebe54d7f1e"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1-teacher/verification.json",
      "role": "results",
      "sha256": "bca5bdf43b035abba2020ef70df7b811aac3a0947cc53394164c78d62d81b665"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1-teacher/receipts.json",
      "role": "run",
      "sha256": "c6649977fea6a87354e122c93522bc3584b53537b22c0fc82acafa1408e1cc95"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1-data-verified/verification.json",
      "role": "results",
      "sha256": "d2a17989dd1011cc19444e4fc25309fdf17389d571768a587820c8af60fab857"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1/architecture-surfaces.png",
      "role": "report",
      "sha256": "91fcecb64a52cb45763eb301862c364907e5d11fcf0d295ce6b5e84067237a9d"
    },
    {
      "path": "data/experiments/learning/architecture-surfaces-v1/analyze.py",
      "role": "source",
      "sha256": "6a65fa0510fda7f6abfb7537c24bd7b6007b92cb43420a1374665598560e2c28"
    },
    {
      "path": "data/experiments/learning/architecture-surfaces-v1/verify_closeout.py",
      "role": "source",
      "sha256": "e9509d232b1e3d3ca2c811f7348c9fe6d97292cd2f973904865e2a4dd1db79c1"
    }
  ],
  "prior_work": [
    {
      "id": "policy-tuning-v1",
      "relationship": "extends",
      "contribution": "Revisit capacity and coordinate sharing on changed generated100k-label regime."
    },
    {
      "id": "generated-data-scaling-v1",
      "relationship": "uses",
      "contribution": "Reuse frozen4k inputs and inspected development to investigate representation rather than scale."
    },
    {
      "id": "teacher-quality-v1",
      "relationship": "extends",
      "contribution": "Diagnose reference instability and metric disagreement on fixed development sample."
    }
  ],
  "novelty": "Couple architecture contrasts to action support, choice difficulty, confidence and teacher stability diagnostics; explain mechanisms rather than optimize one metric."
}
```


## HTML presentation delivery — 2026-09-12

The local-only offline reading view at `artifacts/reports/architecture-surfaces-v1.html`
presents the full report, the retained figure, two metric/checkpoint explorers,
and first-level evidence previews. The [view specification](../../../data/experiments/learning/architecture-surfaces-v1/report-view.json)
pins the existing findings JSON; [the reusable exporter](../../../src/qi/experiments/README.md#present-authored-research-reports)
also rendered the earlier teacher advisory without a chart specification.
No new training, teacher queries or sealed evaluation occurred.

Presentation erratum: the original report table prints canonical dense MLP64's
200-update macro as 15.52%. Its retained value is 15.525091719077569%, correctly
rounded to 15.53% in the interactive view. An explicit note appears beside the
original table. Original Markdown and numeric evidence remain byte-identical;
this display correction changes no scientific conclusion. The HTML is a
regeneratable projection; its catalog link has no frozen hash because it embeds
this owning record, whose catalog in turn links the HTML.

Verification: `UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/qi-uv-cache make check` passed
(705 Python tests, one optional skip, five browser unit tests, lint, documentation,
catalog, API/type checks and production builds). The report E2E lane passed all
12 desktop/mobile cases, including existing search reports, with authored-report
network access disabled. Evidence-dialog keyboard focus restoration was repaired
before that passing run. The export guard tests cover frozen hashes, missing versus
zero values, workspace containment, output overwrite, reference links and explicit
presentation corrections. The report front page was visually inspected.


```experiment
{
  "schema_version": 1,
  "id": "architecture-surfaces-v1",
  "title": "Architecture mechanisms and diagnostic surfaces",
  "question": "Which architecture, data, teacher and metric mechanisms explain the observed imitation limits?",
  "kind": "learning",
  "topics": [
    "architecture",
    "representation",
    "teacher",
    "metrics",
    "data coverage",
    "mechanism",
    "generalization"
  ],
  "execution": "complete",
  "conclusion": "mixed",
  "finding": "15 fits and 30 exact checkpoint reloads. At 200 updates: macro 16.324% baseline, 18.219% wider, 15.525% canonical dense, 16.726% canonical pair, 20.444% spatial pair. Dense unseen-target accuracy is zero; spatial is 16.667% on 54 canonical development positions. CNN seed 17 destabilizes late despite the highest final CNN development score. 144 teacher queries reproduce all 48 original 100k moves; ten change at 1M and WDL saturates.",
  "conditions": "Frozen mixed 4000 training and 373 inspected development inputs; seeds 7/17/27; five models; 50/200 correlated checkpoints; Adam .01 CPU one thread, full-batch chunks 256. 48 stratified full histories; 100k/1M single-PV and 1M all-legal. 3900 sealed inputs unscored.",
  "limitations": "One training pool and reused development; initialization seeds are not dataset repetitions. Architecture capacity/optimization confounds persist. Absolute 50/canonical 54 unseen slices differ. Teacher WDL is saturated and all-legal search shallower; no game outcomes. 855.95s models plus 77.56s teacher; timings include host contention.",
  "decision": "Prioritize AB-LEARN-017 controlled positive-action support versus representation transfer with stability controls;retain AB-LEARN-015 metric validity. No architecture or player-default promotion.",
  "revisit": "Fresh source games under matched support intervention;declared optimizer/update controls and stable move-severity references with paired game outcomes.",
  "evidence": [
    {
      "path": "records/reports/2026-09-12-architecture-surfaces.md",
      "role": "report",
      "sha256": "541507fbcbf291bb145a6fc7251a047e47108c70bc944753b9cfa2ce59db64c6"
    },
    {
      "path": "data/experiments/learning/architecture-surfaces-v1/protocol.json",
      "role": "config",
      "sha256": "cc91f1a01e7f40480eccc0e2d906bcc6085cf7419b747688da19ed726108a9a6"
    },
    {
      "path": "data/experiments/learning/history/architecture-surfaces-v1.json",
      "role": "results",
      "sha256": "78c797b65e3b3321a9d87e073d801d4d1e22b95630f68f05b13f1ea04cda7bae"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1-closeout/verification.json",
      "role": "results",
      "sha256": "0aee897c4a23809973310d7f24011309530740e21dbd449f35d1c930afcf2907"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1/analysis.json",
      "role": "results",
      "sha256": "7e7697c0de09f27e25ec4c607b69e99b2e61f51a692313a43e2c6ebede9c4c71"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1/study/lineage.json",
      "role": "source",
      "sha256": "3a4b5a21c2092a51494e8523e163b221a9b00a8b1f411fe9ecef893fc9411348"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1/study/verification-32724.json",
      "role": "results",
      "sha256": "799c555f61c8533e1839bbf74a7d9f1045e02722266874406317f7ebe54d7f1e"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1-teacher/verification.json",
      "role": "results",
      "sha256": "bca5bdf43b035abba2020ef70df7b811aac3a0947cc53394164c78d62d81b665"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1-teacher/receipts.json",
      "role": "run",
      "sha256": "c6649977fea6a87354e122c93522bc3584b53537b22c0fc82acafa1408e1cc95"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1-data-verified/verification.json",
      "role": "results",
      "sha256": "d2a17989dd1011cc19444e4fc25309fdf17389d571768a587820c8af60fab857"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1/architecture-surfaces.png",
      "role": "report",
      "sha256": "91fcecb64a52cb45763eb301862c364907e5d11fcf0d295ce6b5e84067237a9d"
    },
    {
      "path": "data/experiments/learning/architecture-surfaces-v1/analyze.py",
      "role": "source",
      "sha256": "6a65fa0510fda7f6abfb7537c24bd7b6007b92cb43420a1374665598560e2c28"
    },
    {
      "path": "data/experiments/learning/architecture-surfaces-v1/verify_closeout.py",
      "role": "source",
      "sha256": "e9509d232b1e3d3ca2c811f7348c9fe6d97292cd2f973904865e2a4dd1db79c1"
    },
    {
      "path": "data/experiments/learning/architecture-surfaces-v1/report-view.json",
      "role": "config",
      "sha256": "42728dc944a99fd64315732743ec0034df3601a0f5afded904a57c099026c67d"
    },
    {
      "path": "artifacts/reports/architecture-surfaces-v1.html",
      "role": "report",
      "sha256": null
    }
  ],
  "prior_work": [
    {
      "id": "policy-tuning-v1",
      "relationship": "extends",
      "contribution": "Revisit capacity and coordinate sharing on changed generated100k-label regime."
    },
    {
      "id": "generated-data-scaling-v1",
      "relationship": "uses",
      "contribution": "Reuse frozen4k inputs and inspected development to investigate representation rather than scale."
    },
    {
      "id": "teacher-quality-v1",
      "relationship": "extends",
      "contribution": "Diagnose reference instability and metric disagreement on fixed development sample."
    }
  ],
  "novelty": "Couple architecture contrasts to action support, choice difficulty, confidence and teacher stability diagnostics; explain mechanisms rather than optimize one metric."
}
```

### 2026-09-22 — portable report locator

This final revision records the report after ignored artifact links were
made explicit local-only paths. The scientific result and old digest remain
historical evidence.

```experiment
{
  "schema_version": 1,
  "id": "architecture-surfaces-v1",
  "title": "Architecture mechanisms and diagnostic surfaces",
  "question": "Which architecture, data, teacher and metric mechanisms explain the observed imitation limits?",
  "kind": "learning",
  "topics": [
    "architecture",
    "representation",
    "teacher",
    "metrics",
    "data coverage",
    "mechanism",
    "generalization"
  ],
  "execution": "complete",
  "conclusion": "mixed",
  "finding": "15 fits and 30 exact checkpoint reloads. At 200 updates: macro 16.324% baseline, 18.219% wider, 15.525% canonical dense, 16.726% canonical pair, 20.444% spatial pair. Dense unseen-target accuracy is zero; spatial is 16.667% on 54 canonical development positions. CNN seed 17 destabilizes late despite the highest final CNN development score. 144 teacher queries reproduce all 48 original 100k moves; ten change at 1M and WDL saturates.",
  "conditions": "Frozen mixed 4000 training and 373 inspected development inputs; seeds 7/17/27; five models; 50/200 correlated checkpoints; Adam .01 CPU one thread, full-batch chunks 256. 48 stratified full histories; 100k/1M single-PV and 1M all-legal. 3900 sealed inputs unscored.",
  "limitations": "One training pool and reused development; initialization seeds are not dataset repetitions. Architecture capacity/optimization confounds persist. Absolute 50/canonical 54 unseen slices differ. Teacher WDL is saturated and all-legal search shallower; no game outcomes. 855.95s models plus 77.56s teacher; timings include host contention.",
  "decision": "Prioritize AB-LEARN-017 controlled positive-action support versus representation transfer with stability controls;retain AB-LEARN-015 metric validity. No architecture or player-default promotion.",
  "revisit": "Fresh source games under matched support intervention;declared optimizer/update controls and stable move-severity references with paired game outcomes.",
  "evidence": [
    {
      "path": "records/reports/2026-09-12-architecture-surfaces.md",
      "role": "report",
      "sha256": "a992d71c74f15f968d53e037990f24be616b7ad4ad1607a39af85aa976f0c07c"
    },
    {
      "path": "data/experiments/learning/architecture-surfaces-v1/protocol.json",
      "role": "config",
      "sha256": "cc91f1a01e7f40480eccc0e2d906bcc6085cf7419b747688da19ed726108a9a6"
    },
    {
      "path": "data/experiments/learning/history/architecture-surfaces-v1.json",
      "role": "results",
      "sha256": "78c797b65e3b3321a9d87e073d801d4d1e22b95630f68f05b13f1ea04cda7bae"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1-closeout/verification.json",
      "role": "results",
      "sha256": "0aee897c4a23809973310d7f24011309530740e21dbd449f35d1c930afcf2907"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1/analysis.json",
      "role": "results",
      "sha256": "7e7697c0de09f27e25ec4c607b69e99b2e61f51a692313a43e2c6ebede9c4c71"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1/study/lineage.json",
      "role": "source",
      "sha256": "3a4b5a21c2092a51494e8523e163b221a9b00a8b1f411fe9ecef893fc9411348"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1/study/verification-32724.json",
      "role": "results",
      "sha256": "799c555f61c8533e1839bbf74a7d9f1045e02722266874406317f7ebe54d7f1e"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1-teacher/verification.json",
      "role": "results",
      "sha256": "bca5bdf43b035abba2020ef70df7b811aac3a0947cc53394164c78d62d81b665"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1-teacher/receipts.json",
      "role": "run",
      "sha256": "c6649977fea6a87354e122c93522bc3584b53537b22c0fc82acafa1408e1cc95"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1-data-verified/verification.json",
      "role": "results",
      "sha256": "d2a17989dd1011cc19444e4fc25309fdf17389d571768a587820c8af60fab857"
    },
    {
      "path": "artifacts/learning/architecture-surfaces-v1/architecture-surfaces.png",
      "role": "report",
      "sha256": "91fcecb64a52cb45763eb301862c364907e5d11fcf0d295ce6b5e84067237a9d"
    },
    {
      "path": "data/experiments/learning/architecture-surfaces-v1/analyze.py",
      "role": "source",
      "sha256": "6a65fa0510fda7f6abfb7537c24bd7b6007b92cb43420a1374665598560e2c28"
    },
    {
      "path": "data/experiments/learning/architecture-surfaces-v1/verify_closeout.py",
      "role": "source",
      "sha256": "e9509d232b1e3d3ca2c811f7348c9fe6d97292cd2f973904865e2a4dd1db79c1"
    },
    {
      "path": "data/experiments/learning/architecture-surfaces-v1/report-view.json",
      "role": "config",
      "sha256": "42728dc944a99fd64315732743ec0034df3601a0f5afded904a57c099026c67d"
    },
    {
      "path": "artifacts/reports/architecture-surfaces-v1.html",
      "role": "report",
      "sha256": null
    }
  ],
  "prior_work": [
    {
      "id": "policy-tuning-v1",
      "relationship": "extends",
      "contribution": "Revisit capacity and coordinate sharing on changed generated100k-label regime."
    },
    {
      "id": "generated-data-scaling-v1",
      "relationship": "uses",
      "contribution": "Reuse frozen4k inputs and inspected development to investigate representation rather than scale."
    },
    {
      "id": "teacher-quality-v1",
      "relationship": "extends",
      "contribution": "Diagnose reference instability and metric disagreement on fixed development sample."
    }
  ],
  "novelty": "Couple architecture contrasts to action support, choice difficulty, confidence and teacher stability diagnostics; explain mechanisms rather than optimize one metric."
}
```
