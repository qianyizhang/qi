---
description: Settle and measure a full-game generation regime before choosing a larger overnight run.
scope: backlog item
status: experimental
last_update: 2026-09-11
document_class: work_record
work_id: AB-DATA-008
work_status: ready
work_kind: research
added: 2026-09-10
tags: domain
depends_on: AB-DATA-007
residual_of: none
residual_items: none
produced_by: "experiment@1.0.0 · grilling@1.1.0 · agent=GPT-6 · effort=unspecified · 2026-09-10"
---

# AB-DATA-008 — Generation scaling pilot and overnight preparation

## Intent

Choose a reproducible generation regime and measure retained yield, complete
preparation cost and storage before selecting a larger run size. The earlier
1M figure is illustrative, not a fixed quota or acceptance criterion.
The user accepted full-game coverage, structured metadata, alternative analyses,
small tests first and an eventual overnight run after configuration settles.
The precise run protocol remains open; this record does not schedule execution.

## Acceptance Criteria

- Resolve the frontier below, then freeze the recipe, sources, teacher assets,
  budgets, exclusions, selection policies, repetitions and stop rules.
- Register the planned study in the shared experiment catalog before execution;
  link prior findings and state the new contribution.
- Compare shorter/longer continuations and measure random versus diversified
  teacher-guided source contributions. Keep rollout plies, retained labels and
  phase distribution distinct. Exact cell sizes remain a subsequent decision.
- Compare node-only 10k and 100k supervision on identical sampled states, with
  a smaller shared 1M-node reference; preserve all exact settings and costs.
- Benchmark complete preparation, including rollout, actor and supervisor
  searches, rejected candidates, persistence, validation and export. Report unique
  positions, occurrences, games/families, actual queries/nodes, phase coverage,
  wall time, peak memory, disk bytes and failures separately.
- Verify store interruption/reopen and immutable snapshot behavior before scale-up.
- Freeze the selected overnight config after the pilot; do not silently weaken
  teacher budgets, reduce quotas or extend allowances to reach the target.
- Preserve partial work and distinguish target completion from elapsed cutoff.
  Retain raw evidence and publish assessed findings/limits in the owning catalog.

## Context and Trade-offs

### Prior finding, overlap and contribution

- `policy-data-scaling-v1` / [AB-LEARN-004](AB-LEARN-004-dataset-scaling.md):
  fixed-policy scaling helped imitation in early random play; larger datasets
  also consumed more full-batch compute. It does not establish a full-game regime.
- `source-coverage-confirmation-v2` / [AB-LEARN-007](AB-LEARN-007-fresh-source-confirmation.md):
  broader source coverage helped at fixed labels in its narrow setup. Four labels
  per game is not a general optimum; varied length/phase requires new measurement.
- `teacher-quality-v1` / [AB-LEARN-009](AB-LEARN-009-teacher-quality.md):
  stronger labels gave mixed student agreement. A new generation pilot measures
  cost/quality on a changed position distribution rather than repeating that fit matrix.
- `teacher-throughput-20260909` / [advisory](../../reports/2026-09-09-teacher-generation-advisory.md)
  and `persistent-teacher-v1` / [AB-DATA-004](AB-DATA-004-persistent-teacher.md):
  process reuse is promising, but warm repeated-query and tiny integrated pilots
  do not predict million-position retained throughput.

The contribution is a measured full-game sampling regime with incremental storage,
explicit diversity/yield and a frozen export. It does not establish playing strength,
model scaling laws or a best teacher budget through timing alone. Any teacher
agreement reference remains an estimate, not referee truth.

### Settled direction

- Local generation, structured occurrence metadata and separately reusable analyses.
- Count unique board-and-turn observations separately from occurrences and queries.
- Diverse teacher-guided trajectories plus a random component; actor and supervisor
  are independently specified. Plausible-play diversity uses seeded sampling among
  sufficiently supported teacher candidates throughout the game; exact numerical
  settings and sampling probabilities remain calibration choices.
- Plausible play is the main intended component. Mistakes/recovery is an explicit,
  separately measured component rather than an unrecorded source of move noise.
- Include replay-backed noninitial starts as an independently configurable source
  type, initially from eligible generated trajectories. Curated/recorded sources
  can follow when available; preserve parent lineage and shared source families.
- First use small comparisons; choose the larger run size after settling and
  measuring generation. Neither 1M nor 10M is a locked sample quota.
- SQLite/JSONB collection and SQL-selected Parquet snapshots follow ADR-0008;
  core build is [AB-DATA-007](AB-DATA-007-sqlite-training-data-store.md).

### Operational decisions

- R1 accepted: retain full trajectories/configs and aggregate actor costs;
  persist full raw analyses for selected or fixed-audit occurrences plus failures.
- R2 deferred: 1M was figurative. Do not settle training-versus-total counts now;
  focus on the generation policy first.
- R4 accepted as a low-priority planning allowance: 12 hours end to end, with
  resumable partial work at cutoff. This does not schedule or fix a run size.
- R5 accepted: one recorded retry for a transient teacher failure, then stop
  resumably; identity, legality and integrity failures stop immediately.

### Accepted generation policies

The user accepted G3–G5 with "all your rec". Opening-only randomness can remain
an optional recipe, but is not the main plausible-play policy. Keep the following
axes separately configurable:

| Axis | Configuration dimension | Meaning |
| --- | --- | --- |
| Starting positions | Standard initial board; generated opening prefixes; replay-backed noninitial scenarios | Which situations continuations begin from; scenario/source lineage and splits remain explicit. |
| Actor move selection | Uniform legal random; teacher best move; occasional random alternatives; sampling among teacher-assessed candidates | Which trajectories are visited. Engine-aware sampling requires explicit candidate support and extra search-cost measurement. |
| Exploration schedule | Opening-only; intermittent throughout; phase-dependent | When a non-greedy actor rule applies; separate from the move-selection rule itself. |
| Continuation | Ply limits and referee terminal outcomes | How far to generate, independently of how many positions are retained. |
| Position selection | Phase/ply conditions, spacing, per-game caps, duplicate selection | Which occurrences become reusable inputs; chronological position is not game phase. |

Plausible play is the main component and noninitial starts belong in the first
design. The following behavioral decisions are locked:

| ID | Decision | Accepted policy |
| --- | --- | --- |
| G3 | How to diversify the plausible-play actor? | Seeded sampling among a small teacher-assessed candidate set within a declared score gap, available throughout the game. Compare candidates only with compatible exact scores/depth/perspective; fall back visibly to the teacher-selected legal move for insufficient evidence or mate cases. Candidate count, gap and search budget remain calibration settings. |
| G4 | How to construct mistakes/recovery trajectories? | Introduce one marked non-best legal move at a sampled eligible point, then use teacher-best continuation to observe recovery. Record the intervention and do not assume every alternative is a serious mistake. Multiple interventions and their frequency schedules can follow. |
| G5 | How to retain occurrences from completed trajectories? | Phase-stratified selection with per-game caps and minimum ply spacing; retain provenance for duplicates and freeze the policy. Report phase shortfalls instead of filling them from another phase. Exact weights, caps and spacing remain pilot settings. |

### Remaining pilot calibration

Do not repeat the accepted policy interview. Resolve candidate count, score-gap
units/threshold, sampling probability rule, actor budget, intervention eligibility
and selection, source starts, continuation lengths, phase weights, sample caps,
minimum spacing and the small pilot's size/allowance in a concrete protocol.
These settings have not been accepted as defaults by agreeing to G3–G5.
Worker count and acceptance gates must use representative implementation evidence.
The larger run size remains deliberately open. No mixture weights, numerical
exploration settings or scenario assets are silently selected. Noninitial-start
selection must precede child generation; parents and descendants stay together
for splitting and reference exclusions apply to the whole retained lineage.
If the measured overnight rate cannot meet quotas, present that feasibility
result and revise the scope/config explicitly before dispatch.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-10 | Codex | — | deferred | Capture accepted study direction; exact protocol and infrastructure are pending, so no run is scheduled. |
| 2026-09-10 | Codex | deferred | wip | User authorized build and test alongside AB-DATA-007, with integration if infrastructure is available or a tested boundary and handoff otherwise. |

| 2026-09-10 | Codex | wip | deferred | Generation build and real SQLite/Parquet integration verified; broader numerical calibration and overnight sizing remain unscheduled. |

| 2026-09-10 | Codex | deferred | wip | User requested real per-policy resource pilots, SQL I/O verification and longer gameplay. |
| 2026-09-10 | Codex | wip | ready | Seven resource cells verified and an overnight profile prepared; larger generation remains unlaunched. |

## Implementation Ledger

### 2026-09-10 — decision: build and test alongside the collection task

- Evidence: user explicitly requested implementation/testing, identified the
  concurrent AB-DATA-007 task, and authorized shared-checkout or worktree
  coordination and deferred integration only if the infrastructure is unavailable.
- Consequence: generation owns new policy/runner/adapter/test files under the
  [claim ledger](../../reports/claim-ledger-generation-20260910.md). Existing store,
  snapshot, CLI and dependency files remain the other task's responsibility.
- Follow-up: implement the locked policies with explicit configurable calibration
  values, hermetic counterexample tests and a bounded real-engine pilot after
  freezing its recipe. No million-position or overnight run is dispatched.
- Review: ratified for implementation and bounded tests; scientific defaults
  remain provisional until measured.

### 2026-09-10 — decision: retain the unresolved protocol frontier

- Evidence: user wants to settle generation config, run small tests, and leave
  the eventual 1M case overnight; requested a grill of uncovered decisions.
- Consequence: separate the accepted storage architecture from unsettled pilot
  and operational settings. Prior time/space extrapolations remain estimates.
- Follow-up: obtain R1–R5 answers, inspect available starts and diversity options,
  and freeze a feasible small protocol before registering or running it.
- Review: ratified for study direction; pending for the frontier settings.

### 2026-09-10 — decision: operational policies accepted; generation remains open

- Evidence: user answered yes to retention, accepted the failure policy and
  12-hour allowance, clarified that 1M is figurative, and requested a broader
  discussion of opening-only exploration as one possible setting.
- Consequence: lock R1 and R5, retain R4 as a planning allowance, defer R2 and
  expand R3 into independent generation axes. This supersedes the earlier
  suggested fixed 1M-training-input interpretation.
- Follow-up: settle source/actor intent before numerical generation settings;
  do not revisit settled operational questions or start a scale run.
- Review: ratified for these corrections; pending for generation-policy choices.

### 2026-09-10 — decision: plausible-play priority and noninitial sources

- Evidence: user answered "both your rec" to plausible play as the main component
  with separately measured mistakes/recovery, and inclusion of replay-backed
  noninitial starts beginning with eligible generated trajectories.
- Consequence: both directions are locked without another confirmation. Preserve
  parent/source-family isolation and keep actor policy independent of supervision.
- Follow-up: resolve G3–G5, then calibrate the numerical generator settings and
  freeze a small pilot; the larger sample count remains intentionally open.
- Review: ratified for these directions; pending for G3–G5.

### 2026-09-10 — decision: actor diversity, interventions and sampling locked

- Evidence: user answered "all your rec" to G3 candidate-based plausible play
  throughout games, G4 one marked non-best-move intervention followed by
  teacher-best continuation, and G5 phase-stratified selection with per-game
  caps and minimum ply spacing.
- Consequence: G3–G5 are accepted without another confirmation. Preserve fallback
  evidence, distinguish interventions from proven mistakes, and report phase
  shortfalls without redistributing quotas. These policies extend the locked
  plausible-play priority and replay-backed noninitial sources.
- Follow-up: specify and calibrate numerical settings and probability rules in
  the bounded pilot protocol; do not infer a fixed large-run quota or schedule.
- Review: ratified for G3–G5; remaining calibration is explicitly open.

### Predeclared bounded engineering protocol — generation-policy-engineering-v1

This tests implementation and the real collection boundary, not the full research
acceptance criteria above. Values are explicit provisional engineering settings,
not calibrated defaults or an accepted overnight recipe.

- Question/expectation: can the accepted policies produce replayable games,
  independently budgeted labels, honest phase quotas and a selected-only immutable
  snapshot? Expect the short continuations to miss some phase quotas. Illegal
  actions, lineage/spec mismatches, hidden quota filling or mutable snapshots
  challenge correctness and stop promotion.
- Frozen inputs: [generation recipe](../../../data/experiments/learning/generation-policy-engineering-v1.json),
  [export recipe](../../../data/experiments/learning/generation-policy-engineering-export-v1.json),
  pinned local Pikafish assets, the existing reserved opening corpus, seed 7,
  sequential persistent engine, node-only 10k actor and paired 10k/100k labels.
- Five initial games: plausible play at 32 and 96 plies in train; one intervention
  and one random game at 48 plies in train; plausible play at 48 plies in validation.
  These are different sources, not matched scientific repetitions.
- Plausible actor: three candidates, engine-native exact cp gap 50, seeded uniform
  eligible sampling throughout; visible teacher-best fallback. Intervention:
  one seeded absolute ply in [8,24], one uniformly selected non-best legal move.
- Selection: opening 2 / middlegame 2 / endgame 1 per game; at least four plies
  apart, absolute ply >=4; no quota redistribution. Actor audit every 16 plies.
  Export one selected 100k-label row per split; this tiny quota only tests I/O.
- Optional second stage, specified before the first stage: first completed plausible
  train parent, prefix ply 16, one 32-ply plausible continuation, same family/split.
  Resolve and freeze the exact parent trajectory and child recipe before child
  queries. Stop the stage if the parent/prefix is unavailable or reserved.
- Budget: 600 seconds per stage, at most two stages, no overnight dispatch.
  One retry for timeout/exit; integrity failures stop immediately. Preserve failed
  attempts and source bundles; changing a recipe requires a distinct execution.
- Measurements: actual actor/label calls and reported nodes, wall time, selected
  phase yield and shortfall, game/occurrence/board counts, collection bytes, process
  peak RSS, SQL export and bounded read/verification. No 1M/10M extrapolation from
  this tiny workload. Full paired-budget/reference quality analysis and repeated
  continuation-length calibration remain follow-up work.
- Decision: successful engineering checks allow larger representative calibration;
  they do not settle mixture weights, worker count, overnight size or playing strength.


```experiment
{
  "schema_version": 1,
  "id": "generation-policy-engineering-v1",
  "title": "Generation policy engineering pilot",
  "question": "Do locked generation policies preserve lineage, costs and quotas through SQLite and Parquet?",
  "kind": "other",
  "topics": [
    "generation",
    "plausible play",
    "intervention",
    "phase quotas",
    "SQLite",
    "Parquet"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Five seeded initial games, optional one generated-parent continuation; node-only 10k actor, 10k/100k supervision; 600 seconds per stage. Explicit provisional settings in frozen recipes.",
  "limitations": "Engineering pilot only; one game per source and no scientific optimum or scale claim.",
  "decision": "Run bounded engineering checks and preserve all failures before representative calibration.",
  "revisit": "Incorrect labels, lineage, quota accounting, export isolation or resume behavior.",
  "evidence": [
    {
      "path": "data/experiments/learning/generation-policy-engineering-v1.json",
      "role": "config",
      "sha256": null
    },
    {
      "path": "data/experiments/learning/generation-policy-engineering-export-v1.json",
      "role": "config",
      "sha256": null
    },
    {
      "path": "scripts/run_generation_pilot.py",
      "role": "source",
      "sha256": null
    }
  ],
  "prior_work": [
    {
      "id": "collection-io-v1",
      "relationship": "extends",
      "contribution": "Exercise real actor policies and supervision through the implemented collection."
    },
    {
      "id": "persistent-teacher-v1",
      "relationship": "uses",
      "contribution": "Use pinned sequential persistent teachers while retaining failed attempts."
    }
  ],
  "novelty": "Engineering coverage of the accepted candidate actor, marked intervention and phase sampler over the new collection; no new scaling conclusion."
}
```

### Engineering execution correction before the verification rerun

The first five-game execution completed generation but its export failed closed:
one non-reserved board at ply 6 was selected in both train and validation. The
original collection, failed export and source bundle remain under
`artifacts/learning/generation-policy-engineering-v1/`. This is a useful isolation
counterexample, not a successful preparation. No quotas or teacher budgets changed.

A code review also found that asset locator strings influenced the actor RNG.
Remove locators from the seed identity (retain content hashes and settings), and
include implementation source identity in the logical run config so different
implementations cannot silently reuse each other's completed games. Hermetic tests
cover relocated assets. The verification execution uses a fresh collection with
the original generation recipe; earlier source bytes and results remain preserved.

Before the new execution, fix the export amendment rule: inspect only board hashes
and split membership after generation, add every shared non-reserved observation
as an explicit exclusion corpus opening (including its replay prefixes), freeze a
new selected-only export recipe, then export the original one-row-per-split quota.
Do not inspect label quality or choose favorable outcomes. If exclusions make a
quota infeasible, preserve the failure; do not refill or weaken isolation. This is
an exploratory engineering feasibility correction, not a confirmatory holdout.
The predeclared child stage still uses the first plausible train parent at ply 16.

### 2026-09-10 — verification: generation build and real collection integration

- Evidence: [executable guide](../../../docs/data-generation.md),
  [runner](../../../src/qi/training_data/generation_runner.py),
  [integration tests](../../../src/qi/training_data/test_generation_runner.py),
  and [compact pilot evidence](../../../data/experiments/learning/history/generation-policy-engineering-v1.json).
  Full `make check` passed: 545 Python tests, one opt-in MPS skip, five browser
  tests, lint, formatting, documentation/catalog checks and both production builds.
  The 51 focused generation tests include actual SQLite and Parquet integration.
- Consequence: the requested build/test slice is complete against infrastructure
  commit `9ab7e1a`. Shared-checkout coordination avoided a separate merge. The
  narrow selected-only SQL boundary is included in that infrastructure commit;
  generation implementation and records remain uncommitted in this task.
- Observed workload: six completed trajectories, 304 continuation plies, 16 of
  30 requested occurrences, 15 distinct selected model inputs, 32 stored
  occurrences including audits, three analysis specifications and 60 retained
  successful analyses. Actual work was 256 actor plus 30 supervisor queries;
  raw unselected/unaudited actor responses were discarded according to policy.
- Verified initial generation took 3.16 seconds (3.32 seconds including preflight
  and source archival); child generation took 0.53 seconds. The child invocation
  including preflight, export and verification took 0.78 seconds. Final SQLite
  files occupied 778,240 bytes; the child's process peak RSS was 79,134,720 bytes.
  These tiny observations do not estimate million-position preparation cost.
- Resume reused all five initial games without a teacher query. One explicitly
  audited shared board was excluded with its prefixes before successful two-row
  SQL/Parquet export and replay verification. The original failed export remains
  in execution history. No immutable output was overwritten.
- Calibration finding: only 87/208 plausible actor decisions had sufficient
  candidate support for uniform selection; the other 121 visibly used teacher-best
  fallback. Opening and endgame quotas underfilled; the 96-ply source reached
  endgame while shorter sources did not. One game per source cannot identify an
  optimal horizon or mixture. The single marked intervention occurred once.
- Follow-up: preserve the implemented behavioral policies; calibrate candidate
  evidence coverage/budget and phase/spacing quotas before a larger generation
  run. No overnight run, worker-count default or 1M/10M extrapolation was made.
- Review: ratified for the authorized build/test slice; not-required for reporting
  the measured limits. Broader research acceptance criteria remain open.

### 2026-09-10 — handoff: next calibration, not missing SQL integration

- Evidence: the actual store/export/reader boundary is integrated and tested;
  no temporary JSON sample store or unimplemented I/O protocol remains.
- Consequence: this item returns to deferred research status after its bounded
  implementation slice. Keep the full acceptance criteria above; do not mark the
  larger scaling study done based on an engineering smoke workload.
- Follow-up: use the guide's preview command and frozen recipes to prepare the
  next representative matrix. First assess how actor nodes/candidate count/gap
  change compatible-candidate coverage, then compare continuation lengths and
  phase quota feasibility with repeated independent source families. Retain the
  paired 10k/100k labels and add the smaller declared 1M-node reference on shared
  states when that quality study is frozen. Choose production split/exclusion
  policy before a confirmatory run, since this pilot used a data-only correction.
  Measure distinct retained yield, cumulative query costs, peak memory and bytes
  at representative scale before deciding the overnight scope.
- Integration follow-up: production optimizer consumption is separately owned
  by [AB-LEARN-010](AB-LEARN-010-snapshot-training-protocol.md); it is not a missing
  collection integration step for this generation build.
- Review: not-required; executable handoff and evidence retained.


```experiment
{
  "schema_version": 1,
  "id": "generation-policy-engineering-v1",
  "title": "Generation policy engineering pilot",
  "question": "Do locked generation policies preserve lineage, costs and quotas through SQLite and Parquet?",
  "kind": "other",
  "topics": [
    "generation",
    "plausible play",
    "intervention",
    "phase quotas",
    "SQLite",
    "Parquet"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "Verified six real-engine trajectories (304 continuation plies), 16/30 requested occurrences, 15 distinct selected inputs, 60 retained analyses under three specs, and a two-row immutable Parquet export. Resume reused five games with zero queries. Initial export rejected shared-input leakage; one data-only exclusion corrected the engineering export.",
  "conditions": "Explicit provisional seed-7 recipes: 10k-node actor, paired 10k/100k supervision, 600-second per-stage cap. 256 actor and 30 supervisor queries; initial preparation 3.32s, child plus export/verification 0.78s. Full repository gate: 545 Python passes, one opt-in MPS skip and five browser passes.",
  "limitations": "One game per source; 87/208 plausible decisions had compatible candidate support, remaining decisions visibly fell back. Phase quotas underfilled by 14. Original failed export and source bundles retained; amended exclusion is exploratory. Tiny timings and two exported rows do not establish scale readiness, optimal weights or playing strength.",
  "decision": "Accept the generation build and SQLite/Parquet integration; retain existing behavior while calibrating candidate coverage and phase quotas before scale-up.",
  "revisit": "Repeated representative actor-budget and continuation comparisons, frozen split/exclusion protocol, and full retained-yield/memory/disk measurements before an overnight size decision.",
  "evidence": [
    {
      "path": "data/experiments/learning/generation-policy-engineering-v1.json",
      "role": "config",
      "sha256": null
    },
    {
      "path": "data/experiments/learning/generation-policy-engineering-export-v1.json",
      "role": "config",
      "sha256": null
    },
    {
      "path": "scripts/run_generation_pilot.py",
      "role": "source",
      "sha256": null
    },
    {
      "path": "data/experiments/learning/history/generation-policy-engineering-v1.json",
      "role": "results",
      "sha256": "71f3a55a777b5603d03b4bdb4974255eaadbbcef4d24252ffe1949de6fc351e5"
    },
    {
      "path": "data/experiments/learning/generation-policy-engineering-child-v1.json",
      "role": "config",
      "sha256": "c1096743c9e9972fc16347eb044ae37ac2d61ffd213d472c52cc320191808e56"
    },
    {
      "path": "data/experiments/learning/generation-policy-engineering-export-audited-v1.json",
      "role": "config",
      "sha256": "f4a513e459bbf132b5b20424135bf6bb6587af96c8b50345cf0ed28e97d5f790"
    }
  ],
  "prior_work": [
    {
      "id": "collection-io-v1",
      "relationship": "extends",
      "contribution": "Exercise real actor policies and supervision through the implemented collection."
    },
    {
      "id": "persistent-teacher-v1",
      "relationship": "uses",
      "contribution": "Use pinned sequential persistent teachers while retaining failed attempts."
    }
  ],
  "novelty": "Engineering coverage of the accepted candidate actor, marked intervention and phase sampler over the new collection; no new scaling conclusion."
}
```

### 2026-09-10 — decision: representative resource pilots and long trajectories

- Evidence: user requested a small SQLite generation run for each policy, explicit
  verification against excessive SQL I/O, and realistic parameters for overnight
  generation before larger experiments tomorrow. They also requested longer play
  in preparation for full-game Elo evaluation in the next day or two.
- Prior result/limit: `generation-policy-engineering-v1` verified six trajectories
  but only two exported rows; `collection-io-v1` measured logical SQL callback
  traffic with synthetic teachers, not OS-attributed disk writes. Neither proves
  overnight I/O behavior. This extends those workloads with real policies, larger
  collections, longer trajectories and direct process disk accounting.
- Frozen protocol: [generation-resource-v1](../../../data/experiments/learning/generation-resource-v1/protocol.json).
  Seven serial fresh-process/fresh-collection cells, seed 17: each of random,
  intervention and plausible at 128 games x 96 plies, then 32 games x 300 plies;
  one plausible 100k-actor control at 32 games x 96 plies. Other actors use 10k
  nodes; all selected states receive separate 10k and 100k node-only supervision.
  Candidate count 3, gap 50; intervention ply [12,48]. Per-game phase caps are
  opening 1 / middlegame 8 / endgame 8, spacing 4, minimum ply 1; audit every 32.
  All sources are training sources for this resource study; the reserved corpus
  remains excluded. No generated source is silently promoted to Elo evaluation.
- Expected outcomes: random should have no actor query cost; intervention should
  have at most one marked alternative and teacher-best recovery; plausible uses
  compatible candidates or visible fallbacks. Longer sources should improve
  access to later phases but need not finish naturally or fill every quota.
  Report referee terminal outcomes separately from the 300-ply cap.
- Measurements: trace-callback SQL traffic/transactions, OS-attributed process disk
  reads/writes via macOS `proc_pid_rusage`, WAL/database bytes, sampled parent plus
  live teacher RSS, query/node/wall-time counters, unique retained inputs, phase
  shortfalls, replay/analysis integrity and close/reopen. OS disk counters include
  runner spool and compact journaling; they are not physical NAND-write measures.
  Trace callbacks can repeat SQL for triggers and are labeled accordingly.
- Stop/decision rules: 300 seconds per cell, stop launching after 1800 seconds,
  fail above 1.5GB sampled combined RSS or 4GB OS-attributed writes in one cell;
  inspect checkpoints at 8/32/128 games. Greater than 2x per-game I/O growth from
  32 to 128 at fixed horizon, or >100x writes/final-database amplification, requires
  investigation before recommending overnight. Preserve all failures/deviations.
- Follow-up: fix a demonstrated I/O defect if needed, rerun matched cases with
  archived before/after sources, then prepare a conservative overnight recipe
  with explicit resource/yield estimates. No overnight run is launched here.
- Review: ratified for user-authorized pilots and parameter preparation.


```experiment
{
  "schema_version": 1,
  "id": "generation-resource-v1",
  "title": "Generation policy resource and full-game pilot",
  "question": "Do real generation policies have bounded I/O and useful long-game yield for overnight preparation?",
  "kind": "performance",
  "topics": [
    "generation",
    "SQLite",
    "I/O",
    "long games",
    "overnight",
    "resource"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Seven serial fresh cells, 512 planned games, seed 17, 96 or 300 plies, 10k actor plus one 100k actor control, paired 10k/100k labels. Fixed caps and checkpoint metrics in protocol.",
  "limitations": "Exploratory engineering resource calibration; not playing-strength or absolute Elo evidence.",
  "decision": "Measure before choosing overnight parameters; stop on resource/integrity guards.",
  "revisit": "Superlinear per-game I/O, excess write amplification, weak unique yield or unexpected failures.",
  "evidence": [
    {
      "path": "data/experiments/learning/generation-resource-v1/protocol.json",
      "role": "config",
      "sha256": null
    },
    {
      "path": "scripts/benchmark_generation.py",
      "role": "source",
      "sha256": null
    }
  ],
  "prior_work": [
    {
      "id": "generation-policy-engineering-v1",
      "relationship": "extends",
      "contribution": "More games, long trajectories and OS disk accounting."
    },
    {
      "id": "collection-io-v1",
      "relationship": "extends",
      "contribution": "Real teachers and policies with actual process disk counters."
    }
  ],
  "novelty": "Resource-calibrated generation settings and long-game coverage beyond the earlier correctness and synthetic-I/O pilots."
}
```

### Resource measurement clarification

The first random-96 cell exposed a probe-unit issue: macOS `rusage_info_v2` CPU
counters use Mach absolute ticks on this host, with timebase 125/3. The initial
probe divided by 1e9 without that factor. Preserve those raw results; do not use
that cell's uncorrected `cpu_seconds`. A 0.1-second CPU calibration compared the
corrected process counter against Python `getrusage` (0.09597 vs 0.09587 seconds).
Subsequent cells record the timebase and corrected seconds. Disk byte counts,
RSS, WAL sizes, query counts and measured wall times were unaffected. The initial
cell also lacked a separate referee-outcome summary; its replay audit found 125
unfinished games and three checkmates. Later cells distinguish referee ply-limit
termination from other outcomes. These observational corrections do not change
generation or teacher policies; each cell retains its executed source bundle.

### 2026-09-10 — verification: policy resources and longer gameplay

- Evidence: [all cell results and resource counters](../../../data/experiments/learning/history/generation-resource-v1.json),
  with raw source bundles and SQLite collections under
  `artifacts/learning/generation-resource-v1/`. All seven cells finished their
  planned game counts: 512 trajectories, 5,674 selected occurrences across cells,
  and 14,798 retained successful analyses. Unique counts below are per collection;
  overlapping cells must not be summed as a globally unique dataset.
- Integrity: every trajectory and successful analysis replayed; SQLite integrity,
  foreign-key, WAL checkpoint and read-only reopen checks passed. The first 32
  short/long trajectories have identical shared prefixes for all three policies.
  Phase quotas underfilled explicitly; no quota redistribution or weakened budgets.

| Policy / actor nodes | Games / maximum plies | Unique selected | Generation seconds | OS writes MB | Closed SQLite MB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Random / no actor query | 128 / 96 | 1,117 | 109.18 | 742.5 | 27.4 |
| Intervention / 10k | 128 / 96 | 659 | 181.10 | 776.8 | 38.9 |
| Plausible / 10k | 128 / 96 | 1,381 | 256.69 | 1,177.2 | 56.1 |
| Random / no actor query | 32 / 300 | 464 | 37.80 | 408.8 | 15.4 |
| Intervention / 10k | 32 / 300 | 200 | 42.94 | 189.2 | 11.1 |
| Plausible / 10k | 32 / 300 | 441 | 84.80 | 448.5 | 22.5 |
| Plausible / 100k | 32 / 96 | 369 | 226.65 | 277.4 | 16.4 |

- I/O finding: at fixed 96-ply ceilings, cumulative writes/game increased only
  10–12% between the 32- and 128-game checkpoints, below the predeclared 2x
  investigation threshold. WAL peaks stayed around 4.1–4.3MB; sampled runner plus
  live teacher RSS stayed below 604MB. No runaway collection-size-dependent I/O
  appeared at this scale. Writes are nevertheless substantial: 16.9–27.1x closed
  database size, including runner spool/journal activity. This is not a physical
  NAND-write measurement or proof of million-position behavior.
- Gameplay finding: at a 300-ply ceiling, plausible produced 17 checkmates,
  four stalemates and 11 ply-limit draws; intervention produced 30 checkmates and
  two stalemates; random produced seven checkmates and 25 ply-limit draws. Longer
  plausible games provide later-phase positions and more complete play than the
  short pilot. Reaching the cap must not be reported as a naturally finished game.
- Budget finding: the 10k plausible actor's first 32 short games took 64.57 seconds
  and yielded 368 unique inputs; the 100k actor took 226.65 seconds and yielded
  369. Compatible-candidate selection was 55.6% in the stronger actor's own
  trajectories versus 43.6% across the 10k short cell; changed trajectories prevent
  interpreting this as a matched-position quality improvement. The extra actor
  budget did not improve retained throughput; label quality/playing strength were
  not assessed by these resource timings.
- Consequence: prepare [overnight-long-play-v1](../../../data/experiments/learning/generation-resource-v1/overnight-plan-v1.json):
  9,000 planned games, 80% plausible / 10% intervention / 10% random, 300-ply
  ceilings, 10k actor, paired 10k/100k labels, phase caps 1/8/8 with spacing four.
  Use 100-game blocks to limit mixture drift at a cutoff and allocate 10% of blocks
  to validation. Freeze exclusions for every shared train/validation observation
  before training; preserve sources and fail export on unresolved ambiguity or
  unavailable quotas. Generated training sources are not Elo evaluation openings.
- Forecast/limits: small-pool linear rates imply ~6 hours generation, ~6GB SQLite
  and ~118GB OS writes; budget 8–10 hours and 10–20GB working space, with roughly
  60k–100k unique inputs as a conservative scenario rather than an acceptance
  guarantee. The executable profile stops after 10 generation hours; CLI guards
  are 150GB OS writes, 1.5GB sampled RSS and 30GB free disk reserve. No overnight
  run was launched. Larger-scale duplicate saturation and I/O remain to be observed.
- Verification: `make check` passed 552 Python tests (one opt-in MPS skip), five
  browser tests, lint/format/docs/catalog checks and both browser builds. Seven
  resource-guard tests include fail-closed unavailable counters and an actual
  collection stop/resume without duplicating the completed game. The 9,000-game
  profile passed preview/asset validation and created no output directory.
- Follow-up: launch the prepared bounded profile when requested; inspect its early
  checkpoints against these per-game costs. Preserve any cutoff/shortfall and
  perform the frozen SQL-selection audit before training. The full-game rating
  protocol is recorded in [AB-EVAL-004](AB-EVAL-004-heldout-methodology.md).
- Review: ratified for authorized resource calibration and parameter preparation;
  larger-run results and optimal teacher/sampling choices remain unproven.


```experiment
{
  "schema_version": 1,
  "id": "generation-resource-v1",
  "title": "Generation policy resource and full-game pilot",
  "question": "Do real generation policies have bounded I/O and useful long-game yield for overnight preparation?",
  "kind": "performance",
  "topics": [
    "generation",
    "SQLite",
    "I/O",
    "long games",
    "overnight",
    "resource"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "All seven cells completed: 512 trajectories and 14,798 retained analyses verified. At fixed 96-ply ceilings, OS writes/game grew 10-12% from 32 to 128 games; write amplification was 16.9-27.1x closed database size, sampled combined RSS stayed below 604MB and WAL near 4.3MB. The 300-ply plausible cell yielded 441 unique inputs in 84.8s, with 21/32 checkmate or stalemate outcomes.",
  "conditions": "Seed 17; three policies at 128x96 and 32x300, plus a 32x96 100k-actor control; paired 10k/100k labels. Short/long shared prefixes matched for all 32 paired trajectories in each policy. Serial fresh processes and collections with fixed guards.",
  "limitations": "One seed and small populations. No million-position or overnight execution claim. OS-attributed writes include runner spool/logging and are not physical NAND writes; first-cell CPU tick conversion was corrected in the derived interpretation without replacing raw evidence. Candidate coverage/unique yield do not establish playing strength. Generation phase shortfalls remain.",
  "decision": "Prepare 9000-game 80/10/10 plausible/intervention/random profile with 300-ply ceilings, 10k actor and paired labels. Use 10h generation cap plus sampled 150GB write/1.5GB RSS/30GB free-space guards. No overnight run launched.",
  "revisit": "Compare early overnight checkpoints with measured cost/yield and stop on guards. Audit split overlap and supervision ambiguity before frozen export/training; assess full-game ratings separately.",
  "evidence": [
    {
      "path": "data/experiments/learning/generation-resource-v1/protocol.json",
      "role": "config",
      "sha256": null
    },
    {
      "path": "scripts/benchmark_generation.py",
      "role": "source",
      "sha256": null
    },
    {
      "path": "data/experiments/learning/history/generation-resource-v1.json",
      "role": "results",
      "sha256": "0913fc990aa81fa66f5d185016e0e49820471f7746928fd7422b56a6b68769d6"
    },
    {
      "path": "data/experiments/learning/generation-resource-v1/overnight-plan-v1.json",
      "role": "config",
      "sha256": "9472724738a4a058d1c9798df6200474111680ce9d67c6d3713d63351ab865cd"
    },
    {
      "path": "data/experiments/learning/generation-resource-v1/overnight-long-play-v1.json",
      "role": "config",
      "sha256": "658cdb92a45f4854cb632ed5fdb330a6ee08303d4a765f626436b51d3bd05155"
    }
  ],
  "prior_work": [
    {
      "id": "generation-policy-engineering-v1",
      "relationship": "extends",
      "contribution": "More games, long trajectories and OS disk accounting."
    },
    {
      "id": "collection-io-v1",
      "relationship": "extends",
      "contribution": "Real teachers and policies with actual process disk counters."
    }
  ],
  "novelty": "Resource-calibrated generation settings and long-game coverage beyond the earlier correctness and synthetic-I/O pilots."
}
```


### 2026-09-11 — closeout and authorization: supervised hour-sized batches

- Evidence: the user asked to clean up and commit this task, then hand off to a
  next session that repeatedly launches about one hour of batched work until
  the user wakes and asks it to stop. Bounded quick fixes are authorized; material
  faults may stop dispatch pending the user's decision.
- Completed: generation and measured pilot evidence landed as `4ea57b1`, on top
  of the SQLite infrastructure commit `9ab7e1a`. The full repository gate passed
  again: 552 Python tests, one MPS skip, five browser tests, lint, docs/catalog and
  both browser builds. All parallel claims are closed.
- Consequence: the [session handoff](../../reports/session-handoff-overnight-generation-20260911.md)
  is the next operator's pickup. Begin with numbered 1,000-game batches, a one-hour
  generation allowance and the measured 80/10/10 mixture. Preserve scientific
  settings and source identities; use one SQLite writer. Original 9,000-game/10-hour
  recipes and their evidence hashes remain historical calibration artifacts.
- Resource envelope: 150GB cumulative runner OS writes across every invocation,
  20GB per invocation with at least 21GB session allowance remaining before
  dispatch, 1,500MB sampled RSS and 30GB free disk reserve. Account resumes and
  operator verification; do not reset allowances at a batch boundary. These
  conservative dispatch rules do not assert a hard kernel resource bound.
- Verification: constructed batches 0, 1 and 9 in temporary directories; all had
  1,000 games, 80/10/10 policy proportions, 10% validation, disjoint source IDs and
  valid pinned-asset CLI previews. No generation or collection was created.
- Left: next-session operation and measured larger-pool results; final data-only
  split/label audit and immutable export before training. No overnight job or
  monitor was started by this closeout. Full-game Elo and optimizer migration
  remain with their existing owners.
- Review: ratified for the user's operational handoff. Stop on user request,
  integrity uncertainty, exhausted resource envelope or a material decision;
  retain partial work and failure evidence.
