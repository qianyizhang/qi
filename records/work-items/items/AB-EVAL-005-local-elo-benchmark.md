---
description: Build local ratings, resumable paired benchmarks and a Qi Lab results view for player iteration.
scope: backlog item
status: stable
last_update: 2026-09-14
document_class: work_record
work_id: AB-EVAL-005
work_status: done
work_kind: build
added: 2026-09-11
tags: domain, frontend
depends_on: AB-EVAL-004
residual_of: none
residual_items: none
---

# AB-EVAL-005 — Local Elo benchmark

## Intent

Guide checkpoint iteration using local ratings against a frozen, diverse panel,
with replayable games and explicit costs and uncertainty.

## Acceptance Criteria

- Frozen series/spec/entrant identity; six-reference round robin and extensible
  candidate gauntlet; alpha-beta anchored to 1000 local Elo.
- Sourced, replay-validated human-game opening book with family-separated
  development/locked-test partitions, and separate standard-start diagnostics.
- Atomic per-game evidence, writer exclusion, preserved attempts, explicit
  resume and compatible evidence reuse; paired scoring and offline validation.
- Draw-aware regularized batch ratings, family-level uncertainty, disconnected
  and sparse-result handling, immutable reports and locked-pool reveal/retirement.
- Typed CLI and read-only Qi Lab progress/results with ratings, matchups, costs,
  provenance and partial/failed states.
- Focused integrity/statistics/recovery tests, API and browser coverage, full
  repository checks, and a retained real-Pikafish throughput pilot.

## Context and Trade-offs

All thirteen interview recommendations were accepted, then implementation was
authorized with “go build”. [Contract](../../../docs/benchmark.md) and
[ADR-0009](../../../docs/adr/0009-local-benchmark-ratings.md) retain the decisions.
Prior teacher-quality evidence remains inconclusive for imitation and says
nothing about playing strength. Existing paired evaluation supplies outcome
validation; this work adds multi-player scheduling, persistence and ratings.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-11 | Codex | — | wip | User accepted the decision interview and authorized build. |
| 2026-09-11 | Codex | wip | done | CLI, ratings, source books, resumable evidence and Lab results delivered; repository/browser checks and real-Pikafish pilot passed. |

## Implementation Ledger

### 2026-09-11 — decision

- Evidence: accepted interview, repository evaluation/referee/player contracts,
  and the linked statistical primary sources.
- Consequence: implement the explicit Davidson MAP and family-bootstrap method
  described in the contract; retain unavailable uncertainty for sparse evidence.
- Follow-up: source the book, implement and validate the complete delivery;
  calibrate provisional presets using a bounded throughput pilot.
- Review: ratified for product decisions; statistical implementation recorded
  for reproducibility, with approximation limits explicit.

### 2026-09-11 — delivery and verification

- Delivered the Python benchmark authority, CLI, immutable report snapshots and
  read-only Lab results page. Candidates can reuse compatible development
  reference games; fresh locked-test pools execute the full comparison matrix.
  Replay validation, writer exclusion and a durable pool registry protect
  recovery, test reservation and reveal/retirement boundaries.
- Retained [CCPD source attribution and selection](../../../data/evaluation/human-openings-v1/README.md):
  170 development starts in 93 opening families and 30 locked-test starts in 17
  families. This is a bounded, audited subset, not a representative dataset claim.
- `UV_NO_SYNC=1 UV_CACHE_DIR=/tmp/qi-uv-cache make check` passed: 591 Python tests,
  one optional MPS skip, five JavaScript lifecycle tests, lint, docs, catalog,
  generated API/type checks and production build. All 70 desktop/mobile browser
  tests passed. Integrity cases cover interrupted/failed games, evidence reuse,
  locked-pool lifecycle, replay corruption, snapshot integrity and path boundaries;
  statistical cases check derivatives, known odds and family resampling.
- [Retained pilot result](../../../data/evaluation/benchmark-pilot-v1.json): all
  60 predeclared games completed in 229.902 seconds, with zero failed attempts;
  30 varied-opening games and 30 standard-start diagnostics. Offline replay and
  no-op resume preserved the evidence digest. The archived executed source was
  independently hashed against attempt provenance. Raw evidence remains in
  `artifacts/benchmarks/reference-pilot-v1`; protocol, bindings and executed source
  remain in `artifacts/benchmark-pilot-v1`.
- The one-family pilot verifies engineering behavior and records throughput; it
  does not establish representative playing strength or useful uncertainty.
  Concurrent local checks and heterogeneous per-move resources limit timing
  interpretation. The editable 16-start default is an initial working size.
- Future candidate checkpoints use the delivered gauntlet interface; no new
  trained model or automatic promotion policy is part of this delivery.


```experiment
{
  "schema_version": 1,
  "id": "benchmark-throughput-v1",
  "title": "Local Elo benchmark engineering and throughput pilot",
  "question": "Can the six-reference benchmark complete replayable paired games and record useful cost observations?",
  "kind": "performance",
  "topics": [
    "Elo",
    "full-game",
    "paired games",
    "Pikafish",
    "benchmark",
    "throughput"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Six frozen entrants; one development-book start plus one standard-start diagnostic, both colors, 15 matchups and 60 games. One thread and 16 MiB hash for Pikafish. Fixed native node/depth and qi-visit profiles; 900-second wall allowance.",
  "limitations": "One varied starting family is an engineering pilot; ratings and intervals cannot establish representative strength. Heterogeneous resources and per-move fresh Pikafish processes are intentional.",
  "decision": "",
  "revisit": "",
  "evidence": [
    {
      "path": "artifacts/benchmark-pilot-v1/protocol.json",
      "role": "config",
      "sha256": null
    },
    {
      "path": "artifacts/benchmark-pilot-v1/frozen.json",
      "role": "config",
      "sha256": null
    }
  ],
  "prior_work": [],
  "novelty": "Adds multi-player rating, restart/reuse and UI evidence over the existing paired-game and named-player boundaries."
}
```


```experiment
{
  "schema_version": 1,
  "id": "benchmark-throughput-v1",
  "title": "Local Elo benchmark engineering and throughput pilot",
  "question": "Can the six-reference benchmark complete replayable paired games and record useful cost observations?",
  "kind": "performance",
  "topics": [
    "Elo",
    "full-game",
    "paired games",
    "Pikafish",
    "benchmark",
    "throughput"
  ],
  "execution": "complete",
  "conclusion": "supported",
  "finding": "All 60 planned games (30 rated, 30 standard-start diagnostics) completed in 229.902 seconds with zero failed attempts. Every completed game replayed; a no-op resume preserved all evidence. The retained executed-source archive matched its recorded hash. The human book has 170 development starts in 93 families and 30 locked starts in 17 families.",
  "conditions": "Six frozen entrants; one development-book start plus one standard-start diagnostic, both colors, 15 matchups and 60 games. One thread and 16 MiB hash for Pikafish. Fixed native node/depth and qi-visit profiles; 900-second wall allowance. Shared Mac workload included concurrent repository/browser checks. Executed source is retained independently of subsequent scheduling and snapshot-persistence hardening.",
  "limitations": "One varied starting family; no representative playing-strength conclusion or usable family-bootstrap interval. Heterogeneous settings, fresh Pikafish processes and concurrent local work affect timing. Source archive and raw games are local, ignored artifacts.",
  "decision": "Accept benchmark execution, replay, recovery and result presentation. Keep configurable 16-start development batches as an initial working size; the pilot does not establish an optimal sample count or reference resource profile.",
  "revisit": "Run the full varied-opening development batch with candidate checkpoints; inspect family-level intervals, matchup discrepancies, failures and actual runtime before changing sample counts or reference profiles.",
  "evidence": [
    {
      "path": "artifacts/benchmark-pilot-v1/protocol.json",
      "role": "config",
      "sha256": "0d27206112cccac486b94eca405560b526cf7325ee14ec968fc2f6c4b74c33a4"
    },
    {
      "path": "artifacts/benchmark-pilot-v1/frozen.json",
      "role": "config",
      "sha256": "d69963a2c35c1d93e5ac34120b8105987739a1750314b5ccde77410d6bbae73c"
    },
    {
      "path": "data/evaluation/benchmark-pilot-v1.json",
      "role": "results",
      "sha256": "fba2560a4a901f368e72f8f66f811aafc7b8aa707a747bf4d4dbb18c999b2c71"
    },
    {
      "path": "artifacts/benchmarks/reference-pilot-v1/manifest.json",
      "role": "run",
      "sha256": "580abb1d781bab13eb4213f6c40b373ca04dc606d632512643219ab46deafcf8"
    },
    {
      "path": "scripts/import_benchmark_book.py",
      "role": "source",
      "sha256": "aa9641f97b2b757a570f8ed712bd8e52542983d80b0def1a092df1590b7b0440"
    }
  ],
  "prior_work": [],
  "novelty": "Adds multi-player rating, restart/reuse and UI evidence over the existing paired-game and named-player boundaries."
}
```


### 2026-09-14 — saved checkpoint development evaluation (predeclared)

Produced by: experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-14.

User authorized selecting the strongest saved checkpoint and evaluating different
strategies with Elo. No checkpoint has prior comparative full-game strength
proof. Select an exploratory candidate from saved production `policy-mlp-v1`
checkpoints under `artifacts/learning`, using highest six-cell macro teacher
agreement on the existing 373-position development cache. Break ties by lower
cross-entropy, then path. Reject train/development overlap, validate loading,
and deduplicate tensor states. Prototype architecture checkpoints cannot enter
the current production player; inventory and explicitly report their exclusion.
Scores from different historical evaluation pools are not directly ranked.

Expectation: the selected greedy policy may beat random, while limited tactical
search and teacher imitation need not translate into wins against search players.
The measured result may challenge that expectation; no automatic promotion.

Freeze the established six-reference series and first 16 development starts,
plus a separate standard-start diagnostic, with both colors. Retain the existing
128-visit alpha-beta/enhanced/MCTS and 1k/depth-3, 100k/depth-8 Pikafish presets.
Complete the 510-game reference schedule, reusing compatible pilot slots, then
204 candidate games against that panel. Fit `davidson-map-v1`, anchor alpha-beta
at 1000, and report raw W/D/L, family-bootstrap intervals or unavailable reasons,
costs and incomplete attempts. Development exploration; no held-out claim.
Budget: one serial writer, one CPU thread per engine/model, 90-minute wall cap
per stage; stop at completion, errors or the cap, retaining resumable evidence.
No training or sealed-pool scoring. This extends `benchmark-throughput-v1` from
execution evidence to a candidate strength assessment and uses generated-data
and architecture findings only for candidate-selection context. Revisit with
another checkpoint or supported architecture when game results justify it.

Selection and frozen configs: `artifacts/benchmark-checkpoint-20260914`.
Raw runs: `artifacts/benchmarks/reference-development-20260914` and
`artifacts/benchmarks/checkpoint-development-20260914`.


```experiment
{
  "schema_version": 1,
  "id": "saved-checkpoint-elo-20260914",
  "title": "Saved checkpoint versus strategy panel",
  "question": "How strong is the best development-selected playable checkpoint against the frozen strategy panel?",
  "kind": "performance",
  "topics": [
    "checkpoint",
    "Elo",
    "playing strength",
    "strategies"
  ],
  "execution": "planned",
  "conclusion": "unassessed",
  "finding": "",
  "conditions": "Select compatible saved MLP by six-cell macro agreement on 373 development inputs; 16 development starts plus standard diagnostic, both colors; six frozen references; 90-minute cap per stage.",
  "limitations": "Exploratory selection; imitation is not strength. Prototype checkpoint formats excluded. Local Elo only; no training-overlap certification for opening book.",
  "decision": "",
  "revisit": "",
  "evidence": [],
  "prior_work": [
    {
      "id": "benchmark-throughput-v1",
      "relationship": "extends",
      "contribution": "First full development reference matrix and selected saved-policy gauntlet."
    },
    {
      "id": "architecture-surfaces-v1",
      "relationship": "uses",
      "contribution": "Retain format and imitation-versus-strength limitations."
    }
  ],
  "novelty": "Evaluate an existing policy using end-to-end referee outcomes across the frozen diverse strategy panel."
}
```


### 2026-09-14 — saved checkpoint evaluation complete

The [result report](../../reports/2026-09-14-saved-checkpoint-elo.md) and
[compact measurements](../../../data/evaluation/saved-checkpoint-elo-20260914.json)
retain selection, frozen conditions, raw-game receipts and limitations.
Selected natural-mixture block 1 seed 27 (200 updates): 19.300% balanced
agreement, first among 151 distinct compatible MLP states. All 373 choices
matched saved predictions and fresh production inference. The 143 prototype
format exclusions prevent a strongest-across-all-architectures claim.

All 714 combined game slots completed and replayed with no failed/interrupted
attempts: 654 new games plus 60 compatible pilot games. The checkpoint's 192
rated games gave 7/42/143 W/D/L and 298.116 local Elo; versus random, 6/22/4.
Its 12 standard-start diagnostics were excluded from fitting. Alpha-beta is
anchored at 1000; the candidate is sixth of seven entrants. Five of 200 bootstrap
fits failed, so intervals remain unavailable under the frozen method. Retain
this weak-policy baseline; no strength promotion follows from imitation ranking.
Fresh starts and a directly compared supported checkpoint are the revisit trigger.
No training or sealed-pool scoring occurred.


```experiment
{
  "schema_version": 1,
  "id": "saved-checkpoint-elo-20260914",
  "title": "Saved checkpoint versus strategy panel",
  "question": "How strong is the best development-selected playable checkpoint against the frozen strategy panel?",
  "kind": "performance",
  "topics": [
    "checkpoint",
    "Elo",
    "playing strength",
    "strategies"
  ],
  "execution": "complete",
  "conclusion": "inconclusive",
  "finding": "Selected the best development-scoring compatible MLP from 151 distinct states: 19.300% macro agreement. All 714 game slots verified; 654 newly executed, no failures. Candidate: 298.116 local Elo, 7/42/143 W/D/L in 192 rated games; versus random 6/22/4. All five search-opponent results all below 50% score. 195/200 bootstrap fits succeeded; interval unavailable.",
  "conditions": "Six frozen reference profiles; 16 human-opening prefixes in 11 families, both colors; 192 candidate rated games and 12 separate standard-start diagnostics. Alpha-beta=1000. One-thread CPU inference and Pikafish, heterogeneous caps. Selection on 373 inspected development inputs.",
  "limitations": "Imitation selection does not prove strongest playing strength. 143 prototype-format files excluded. No certified held-out opening claim. Five failed bootstrap fits prevent intervals. Pikafish-large finite gap is prior-dependent after one-sided outcomes. Local Elo only.",
  "decision": "Retain this as an exploratory greedy-policy baseline. The small observed random edge and heavy losses to search do not justify a strength promotion.",
  "revisit": "A new checkpoint, a supported architecture entrant, or a predeclared head-to-head checkpoint comparison on fresh development starts.",
  "evidence": [
    {
      "path": "records/reports/2026-09-14-saved-checkpoint-elo.md",
      "role": "report",
      "sha256": "b6246f546e0b5410ce6112b4f4f995a9fbadf6a02d4e09427b42990fb3cf2c6b"
    },
    {
      "path": "data/evaluation/saved-checkpoint-elo-20260914.json",
      "role": "results",
      "sha256": "767b0bfbff9404426b973affe6230246f78588fae76f4450e4b161e04b9347c8"
    },
    {
      "path": "artifacts/benchmark-checkpoint-20260914/protocol.json",
      "role": "config",
      "sha256": "13b780d24dcb50b3e02d1f34290d1aedb228091e25ffdfe32a48808775e0387a"
    },
    {
      "path": "artifacts/benchmark-checkpoint-20260914/selection.json",
      "role": "results",
      "sha256": "dd81e7dcd012675ede67859bb4d8243cb9d918c7ab17760aef439194fba12506"
    },
    {
      "path": "artifacts/benchmark-checkpoint-20260914/selection-verification.json",
      "role": "results",
      "sha256": "f1b9015d2eb84f32727618900d8703efc347454db8544747794b498333a808ea"
    },
    {
      "path": "artifacts/benchmark-checkpoint-20260914/candidate-spec.json",
      "role": "config",
      "sha256": "4b2f903337e24a5786adcaff9792a2eb11edf697f8ff048ff41d2ef032672a05"
    },
    {
      "path": "artifacts/benchmarks/checkpoint-development-20260914/manifest.json",
      "role": "run",
      "sha256": "2a0065ba623743c02b3dc51be32432bffd8465d5dd72e74c76345404b784e0e7"
    },
    {
      "path": "artifacts/benchmark-checkpoint-20260914/candidate-run.log",
      "role": "results",
      "sha256": "7b304e691b7927718665fd1e87dfc267390403840d7cf773c09e8fd270b0257c"
    },
    {
      "path": "data/evaluation/select_saved_checkpoint.py",
      "role": "source",
      "sha256": "0d4ab55e941cd975e24dd001ba37fec25ef3ed3411046137d685820fe786453d"
    }
  ],
  "prior_work": [
    {
      "id": "benchmark-throughput-v1",
      "relationship": "extends",
      "contribution": "First full development reference matrix and selected saved-policy gauntlet."
    },
    {
      "id": "architecture-surfaces-v1",
      "relationship": "uses",
      "contribution": "Retain format and imitation-versus-strength limitations."
    }
  ],
  "novelty": "Evaluate an existing policy using end-to-end referee outcomes across the frozen diverse strategy panel."
}
```
