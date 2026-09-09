---
description: Replay-backed generation, reusable supervision and frozen training mixture contracts.
scope: training data module
status: stable
last_update: 2026-09-09
document_class: coordination
---

# Training Data

This package implements [the accepted model](../../../docs/models.md) and
[ADR-0004](../../../docs/adr/0004-training-data-bounded-context.md). It owns
selection and composition; the referee owns outcomes and the trainer owns weights.

## Formats and compatibility

- `v1.py` owns the supported v1 random generator and Dataset validator.
  Callers import it directly; the `qi.learning.data` forwarding shim was removed.
  Existing `qi learn dataset` commands,
  seeded choices, source splits, labels and artifact digests retain their meanings.
- `loading.py` loads supported prepared-data formats and refuses incomplete
  mixtures before training. This contract lives outside optimization configuration.
- `contracts.py` defines replay-backed starting positions, generation recipes,
  source provenance and reusable examples (`example-library-v1`). Every example
  contains the actual analysis and all contributing source IDs. The fingerprint
  index is reconstructed by `Library.example_index`; `identities()` exports all
  four example-related identities for inspection.
- `generation.py` uses one continuation loop for random and teacher-guided actors.
  The supervisor is independently configured; the Python API accepts a different
  `actor_teacher`. Cached actor analysis is reused only after checking its exact
  replay state and supervision specification. Each UCI query still starts a fresh
  bounded teacher process. No persistent sessions or speculative provider registry.
- `assembly.py` freezes one supervision recipe into `dataset-manifest-v1`.
  `training-dataset-v2` bundles the manifest with its addressable example library.
  The trainer accepts either format without pretending a mixture is a v1 random
  artifact. Checkpoints retain the byte-format `dataset_sha256` and add a separate
  optional `dataset_manifest_fingerprint`; old checkpoints remain readable.

## Selection and provenance

`selection.py` supports bounded reuse of historical v1 labels. Its
`selected-legacy-dataset-v1` format retains exact selected training labels, all
held-out labels, contributing replay sources, and the parent dataset digest.
`select_training` rejects missing, duplicate and held-out input IDs; it reuses
the v1 replay/leakage validator without claiming to regenerate the selected data.
The original artifact stays unchanged. This is an explicit historical selection
adapter; new generated mixtures continue through `assembly.py`.

Each `SourcePlan` declares a named/versioned start, split, actor mode, number of
independent continuations, additional-ply budget (1–300), samples per continuation
(1–16), and an absolute-ply sampling window. Generation allows at most 2048 games
and 7200 seconds. Selection shuffles eligible nonterminal positions reproducibly.
New generation uses `continuations-v2`: actor randomness depends on the seed,
plan ID, replay-backed start, actor recipe and continuation index. Sampling uses
its own random stream. Changing the window, sample quota or total game count no
longer changes existing trajectories. Source fingerprints also pin the actor
recipe. Old `continuations-v1` libraries remain readable, but regeneration must
explicitly upgrade the recipe version; its random stream changes. No old generator
branch or import alias is kept for that experimental continuation scheme.

Reaching the sample quota does not terminate game continuation. Exhausting a ply
budget is `ply-budget`, not a fabricated draw. Only the referee supplies terminal
outcomes, including its existing 300-ply draw rule.

A noninitial replay-backed start requires a source family. Its variations stay in
one split; the same exact starting state cannot be renamed into another family.
Independent games from the standard initial board can have separate families.
Family IDs remain declared provenance: hashes cannot discover an undisclosed
relationship between two different historical positions.

Starting-position themes must be distinct and nonblank. They describe scenario
membership and are inherited by its continuations. They do not assert a tactical
feature remains true at every ply.
The optional `win-in-one` objective admits only labels whose chosen move actually
wins immediately under the referee. The target remains a teacher preference;
an engine mate score is never promoted to a general forced-win proof.

## Phase policy

`mobile-material-development-v1` is an explicit heuristic, independent of ply:

1. Missing either king gives `unknown`.
2. At most four remaining rooks, knights and cannons, across both sides, gives
   `endgame`.
3. At least ten such pieces, with at most two away from their original occupied
   squares, gives `opening`.
4. Otherwise, `middlegame`.

“Developed” here is this board-feature count, not reconstructed movement history.
The thresholds are experimental sampling labels, not a Xiangqi theory claim.
Fixtures exercise the initial board, a four-knight development sequence, and an
endgame reached through seeded legal play. A curated phase requires its authority
and applies only to the exact annotated starting state; successors are classified
afresh. The sampling window filters phase separately from min/max ply and stride.

## Frozen mixtures and identities

Buckets filter split, mode, phase, required themes and optional objective.
`first-bucket-wins` resolves overlapping eligibility **before quota filling**:
a later bucket cannot borrow candidates assigned to an earlier one, including
alternate histories exposing the same model observation. Each retained
model observation counts once. Requested counts live in the recipe; actual counts
and complete/incomplete status live in the manifest. Missing quotas are never
redistributed. Validation reconstructs selection and verifies the fingerprint on
load, so editing counts, references or completion flags cannot bypass the contract.
Review corrected an edge case where alternate histories could bypass bucket
priority. An affected old manifest fails validation and must be explicitly
reassembled from its library; it is never silently rewritten. The saved phase
pilots retain their original manifest fingerprints.

Assembly excludes every reserved evaluation history prefix and rejects any
remaining observation with cross-split lineage or conflicting target moves under
the chosen supervision specification. Alternative teacher recipes can coexist in
the library; each mixture explicitly selects one. Equal examples merge source
lineage. Same-observation, same-target histories deduplicate deterministically.

Hashes use SHA-256 over sorted, compact JSON with a scheme name and payload:
state = full Snapshot; observation = encoding + board + turn; example = state
fingerprint + supervision specification + move; dataset = ordered references,
buckets/splits/recipe/seed, policy versions, selected lineage/source plans and
reserved corpus identity. Timing, search logs and local file paths are excluded
from semantic identity. The network hash replaces its `EvalFile` locator; engine
and network hashes, adapter, engine settings, nodes and depth pin supervision.
Existing `state_hash` and `input_sha256` remain unchanged alongside these identities.

Bucket ordering uses a separate seeded RNG per bucket, so changing only training
quotas preserves the held-out selection. Keep validation sources, buckets and
mixture seed fixed across comparisons. Training reports include every quota slice,
plus observed mode/phase/theme/objective slices; diagnostic tags can overlap and
must not be summed as independent sample counts.

## Dataset generation advisory (non-conclusive)

The [teacher-generation pilot](../../../records/reports/2026-09-09-teacher-generation-advisory.md)
compares worker throughput, search budgets, MultiPV and observational root traces.
It supports these investigation priorities, not a new default recipe:

- **Generation throughput:** prioritize persistent processes and run-scoped engine/network
  identity checks. Start benchmarking one thread and 16 MiB hash per worker; tune
  worker count on the target machine. Eight workers were fastest tested on the
  local shallow workload; four alongside training is an untested headroom proposal.
- **Supervision quality:** keep the teacher and node/depth limits explicit. Neither
  depth 6 nor node-only 10k was established as the best budget. Compare candidate
  recipes on a broader held-out corpus at equal total preparation cost before
  changing defaults. Record actual nodes, retained examples/s and source coverage.
- **Evaluation:** use stronger-reference score loss and, when all candidates have
  comparable estimates, WDL divergence and rank correlation. Exact-move agreement
  measures compatibility. MultiPV changes search allocation; increasing it under
  fixed nodes reduces depth. WDL output alone had little measured cost.
- **Observability:** a MultiPV=1 root trace can preserve search while exposing
  effort, bounds and older scores. It is a diagnostic, not a best-five ranking or
  a complete probability distribution; never fill missing estimates with zero.
- **Concurrent generation/training:** retain frozen datasets for controlled
  comparisons. Saved, validated chunks with fixed held-out families are a possible
  future streaming boundary; throughput contention and learning benefit remain untested.

**Current support:** `qi data prepare` is sequential and starts a fresh teacher
process per query. The adapter fixes Threads=1, Hash=16 and MultiPV=1; preparation
requires a depth and exposes no persistence, worker, WDL, MultiPV or root-trace
options. Training consumes frozen datasets. The experiments changed none of these
contracts. See the [teacher guide](../../../docs/teacher.md#search-settings-and-query-speed)
for setting semantics and the linked report for evidence and review triggers.

## Commands and partial work

For a copyable end-to-end **dataset preparation** recipe, use `config.py`'s
`PreparationConfig` (`dataset-preparation-v1`). It records the reserved corpus
and digest, `generation` with each source's `mode`, `supervision` with engine and
network paths/hashes and query budgets, optional independent `actor_teacher`,
and the existing `assembly` recipe. All file paths resolve relative to the config.
The assembly supervision fingerprint must match the configured label provider.
Teacher supervision supplies preferences, not ground truth; generation mode
chooses who plays. Omitted `actor_teacher` reuses the supervision teacher for
teacher-guided actions, under the existing exact-state/spec reuse checks.

The [two-mode example](../../../data/experiments/learning/preparation-two-mode-v1.json)
pins the local Pikafish installation used by this repository. Change locators when
moving it; changing engine bytes also requires explicitly updating the pins.

```bash
qi data prepare --config data/experiments/learning/preparation-two-mode-v1.json \
  --output artifacts/learning/prepared-example
qi learn train --data artifacts/learning/prepared-example/dataset.json \
  --checkpoint artifacts/learning/prepared-example/policy.pt --steps 30
```

Preparation saves the resolved `config.json`, checkpointed `library.json`,
`dataset.json` when assembly is possible, and `summary.json`. Hash mismatches fail
before output creation or teacher queries. Generation failure or assembly failure
returns nonzero and retains evidence. Preparation does not train or silently use
a partial library after failed generation. For configured training, set the
training recipe's `data.dataset` to the frozen output; the library and manifest
already carry generation and supervision provenance. Generation is never an
implicit side effect of previewing or running a training config.

The individual generation/assembly commands remain available:

```bash
qi data generate --recipe generation.json --corpus data/evaluation/search-positions-v1.json \
  --engine /path/to/pikafish --network /path/to/pikafish.nnue --output library.json
qi data assemble --library library.json --recipe mixture.json --output dataset.json
qi learn train --data dataset.json --checkpoint policy.pt --device cpu --steps 30
```

Training has one command boundary: `qi learn train` for a single fit, or
`qi learn run` for a configured experiment. The duplicate `qi data train` command
was removed. Single fits save `<checkpoint>.config.json` and
`<checkpoint>.report.json`, including slice diagnostics; a partial fit returns
nonzero after saving its report and completed checkpoint.

Generation checkpoints the newly created library after each source. Retained
checkpoint objects are independent snapshots; later lineage merges do not mutate
earlier receipts. A failed teacher query preserves successfully labeled examples and an explicit failure;
reruns require new output paths. Assembly saves shortfalls and returns nonzero.
The trainer rejects incomplete mixtures before optimization or checkpoint writes.
Generation completion means source attempts finished, not that future composition
quotas can be met. A different, explicit mixture can reuse a partial library if
its own quotas are fully met; the library's original failure remains visible.

The executable example `scripts/training_data_pilot.py` writes resolved generation
and mixture JSON, a reusable library, dataset, identity index, coverage, checkpoint
and report. It uses reachable opening/middlegame/endgame starts, both actor modes,
separate held-out families and explicit semantic-phase filters: one retained
opening example and three middlegame/endgame examples per mode and split. It proves the
pipeline, not improved playing strength. CPU is the default test lane; pass
`--device mps` with GPU access for a bounded Metal run.

Learner-driven play, recorded-game ingestion, diagram-only imports, heterogeneous
targets and dynamic epoch mixing remain later extensions.
