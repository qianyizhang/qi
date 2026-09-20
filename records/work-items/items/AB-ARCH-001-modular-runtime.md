---
description: Accepted modular execution decisions and the first implementation handoff for independent experiments.
scope: architecture decision work item
status: experimental
last_update: 2026-09-21
document_class: work_record
work_id: AB-ARCH-001
work_status: done
work_kind: decision
added: 2026-09-21
tags: domain, architecture, experiments, native
depends_on: none
residual_of: none
residual_items: none
produced_by: "domain-modeling@1.4.3 + grilling@1.2.0 + experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# AB-ARCH-001 — Independent experiments and replaceable execution

## Intent

Let a small experiment change one implementation, run against a stable contract,
and earn integration through retained evidence. Keep Python for experiments,
tools, orchestration and ML; enable native execution of costly game/search loops.
API and frontend design should consume the resulting application operations.

The architecture interview is complete. Rounds 1 and 2 are locked; round 3 accepts
only a low-fidelity serving direction that workloads may reshape. Implementation
sketches below remain illustrative, not additional fixed contracts.
[Execution](../../../docs/adr/0012-replaceable-game-execution.md),
[packages/migration](../../../docs/adr/0013-modular-packages-and-direct-migration.md),
the [core model](../../../docs/models.md) and [experiment method](../../../docs/experiments.md)
own promoted decisions. This decision task changed no runtime code; subsequent
implementation is tracked in AB-ARCH-002. Starting checkout: clean `main`
at `a238aff`.
Related API/FE discussion (Codex task `01a09e23-e58d-7632-bd32-9d7e32685b77`)
proposed Play, Data, Training, Evaluation and Experiments as consumer areas;
that discussion made no repository changes.

## Acceptance Criteria

- Resolve module ownership, dependency direction and the Python/native boundary.
- Define how an isolated candidate runs, is evaluated, and becomes supported.
- Distinguish semantic compatibility, performance evidence and playing strength.
- Select the first migration slice and its measurable acceptance conditions.
- Record accepted decisions in their owning model/ADRs and route implementation
  into bounded work; do not silently promote this proposal into authority.

## Context and Trade-offs

### Findings at the initial architecture survey

The table records the starting checkout. AB-ARCH-002 subsequently extracted game
contracts and the reference implementation; its work record owns current status.

| Current evidence | Implication |
| --- | --- |
| At survey time, `src/qi/game.py` had no imports from other qi modules, but `Game` owned a concrete string board, immutable history, transition and hashing implementation. Search directly called `Game.apply`. Its implementation now lives in [the reference module](../../../packages/qi-game/src/qi_game/reference.py) after AB-ARCH-002. | Preserve the strong rules boundary; decouple callers from its representation before replacing execution. |
| [protocol.py](../../../src/qi/protocol.py) combines Snapshot with player/session and HTTP-facing records; it imports the player package. Arena, teacher and data use Snapshot. | Extract small game interchange records from application/session contracts. A domain snapshot should not import all players. |
| [player core](../../../src/qi/players/core.py) includes MCTS, alpha-beta, heuristic breakdown and engine-specific fields; [bindings](../../../src/qi/players/bindings.py) branches on `policy` and `pikafish`. | Keep a small decision envelope and let each implementation own validated configuration, resources and diagnostics. |
| [search](../../../src/qi/players/alphabeta/__init__.py) already accepts evaluator/leaf callables and reusable components. | Retain this productive experimental seam; changing language must not require a universal Engine class. |
| [training](../../../src/qi/learning/train.py) imports model construction, checkpoint loading and encoding from a particular player. | Give model implementations and observation codecs a home shared by inference and training. |
| [data contracts](../../../src/qi/training_data/contracts.py) import evaluation's Corpus, a player encoding, concrete teacher analysis and protocol Snapshot. | Move reusable input contracts to their owners; data should not need the evaluation runner or a particular player implementation. |
| [experiment Plan](../../../src/qi/experiments/model.py) explicitly supports search players; the [catalog](../../../src/qi/experiments/catalog.py) already records teacher, learning, data, performance and other studies. | Separate general experiment evidence/lifecycle from the search-specific executor; evolve the existing catalog. |
| [source provenance](../../../src/qi/artifacts.py) hashes Python/application sources and Python lockfiles. | A native candidate needs native source, build/toolchain and binary identity too; a Python hash cannot identify its execution. |

Prior findings: `movegen-20260915` and `movegen-layout-20260915` retained
equivalence controls and substantial Python speedups on fixed local search
workloads. The latter rejected its per-position NumPy prototype. These findings
do not establish a current end-to-end training bottleneck or a native speedup.
See [move-generation evidence](AB-EVAL-007-move-generation.md) and
[layout evidence](AB-EVAL-008-movegen-layout.md).

The proposed contribution is a replaceable execution boundary and a general
way to evaluate implementation candidates. The first native comparison would
extend those correctness controls, adding measured conversion/binding cost and
representative batch throughput. Reuse [AB-LEARN-008](AB-LEARN-008-experiment-performance.md)
for phase profiling rather than claiming teacher calls, storage or training are
already known to be dominated by the referee.

### Recommended ownership

Use one repository with uv-managed Python packages, package-owned dependency
declarations, lazy implementation/resource loading and an optional native build.
Independent development initially means independent implementation, configuration,
dependencies and tests; it does not require independent deployments or releases.

| Module responsibility | Owns | Changes independently through |
| --- | --- | --- |
| Game / referee | State, actions, legality, transitions, adjudication, replay and semantic identity | Conforming Python/native backends |
| Gameplay | Match/session progression, participant turns, trajectory recording, execution cutoffs | Players and a referee |
| Players | A participant's move-selection contract, bindings and resource lifecycle | Policy-only, search, external-engine or later LLM implementations |
| Engines / search | Search algorithms, ordering, pruning, transposition tables and heuristic evaluators | Local component interfaces and versioned recipes |
| Models / observations | Model construction, observation/action codecs, checkpoint compatibility and inference | Model implementations used by trainers and players |
| Training Data | Trajectory sources, sampling, supervision, collection and frozen selections | Source/sampler/supervision/assembly strategies |
| Training | Objectives, optimization, batching and checkpoint production | Model and frozen-dataset contracts |
| Evaluation | Frozen test cases, correctness gates, metrics and comparisons | Domain evaluators with explicit metric definitions |
| Experiments | Questions, resolved run plans, execution records, evidence links and decisions | Task adapters wrapping domain operations or a bounded script |
| Application / adapters | Resource wiring, user operations, CLI, HTTP, jobs and presentation | Domain public APIs and artifact readers |

“Game engine” currently covers several ideas. Keep **Referee** for valid moves
and outcomes, **Search** for exploring moves, **Evaluator** for estimated value,
and **Player** for the participant who chooses. A move-ordering or candidate-pruning
experiment may use the referee's legal actions; it cannot redefine legality.
Pikafish's player and teacher adapters may share UCI transport while preserving
their different roles and access permissions.

### Dependency rules

- Game contract records depend on neither players, training, transport nor a
  concrete backend. Keep these records small and Xiangqi-specific for now.
- Referee implementations implement game contracts. Native memory layouts and
  mutable search state remain private to their backend.
- Search implementations consume referee capabilities and local component
  contracts. Model implementations consume observation/game contracts.
- Player implementations compose search/model/UCI capabilities. Gameplay calls
  the player contract; it does not branch on algorithm names.
- Data consumes trajectory, observation and supervision contracts. Training
  consumes frozen data and model contracts. Evaluation consumes public game,
  gameplay/player or dataset interfaces as appropriate to its task.
- The general experiment harness depends on its own task/result contracts;
  domain task adapters depend on both. It must work for a storage benchmark that
  has no player or model at all.
- Application factories assemble implementations and own explicit registrations.
  Domain code receives dependencies; it does not resolve environment variables,
  load all implementations, or call HTTP/CLI adapters.

Each useful dependency/ownership boundary receives its own package declaration.
Small helpers need not become packages. Contracts belong beside their owning
concern, not in one expanding `common` or `interfaces` package. Shared artifact
references and identity helpers remain small. Exact package grouping is open.

Illustrative logical modules, to distribute among uv-managed packages as working
slices require them (this is not a locked physical package layout):

```text
src/qi/
  game/          # contracts, replay, reference Python backend
  gameplay/      # sessions, matches, trajectories
  players/       # participant contract and adapters
  engines/       # search recipes and components
  models/        # observation codecs, architectures, checkpoints, inference
  training_data/ # existing ownership retained
  learning/      # existing training ownership retained
  evaluation/    # search studies, correctness, benchmarks and ratings
  experiments/   # general run/evidence contracts, task adapters, catalog
  application/   # factories and shared user operations
  adapters/      # CLI and HTTP
native/          # pure native core, binding layer, native tests
studies/         # retained candidate code, plans and task-local tests
artifacts/       # ignored run outputs; isolated directory per execution
web/            # consumes application operations
```

These are proposed paths, not scaffolding to create up front. In particular,
turning `game.py` into a package or moving evaluation is a migration, not a
prerequisite for testing the first boundary.

### Small interfaces, with explicit semantics

Prefer functions and `typing.Protocol` for Python substitution; use an ABC only
where enforced inheritance or shared lifecycle behavior earns its cost. Structural
typing permits implementations without a common base class; it does not validate
their semantics. See the [Python typing specification](https://typing.python.org/en/latest/spec/protocol.html).

The initial shapes below are design sketches, not executable signatures:

| Seam | Minimal operation | Required contract detail |
| --- | --- | --- |
| Referee | Restore, inspect, legal actions, apply, export snapshot | Ruleset/history, terminal handling, invalid-action atomicity, deterministic action order and identity |
| Player session | Choose from a decision request; close resources | Root state identity, seed, supported budget units, decision and implementation identity |
| Scalar evaluator | Position → estimated value | Perspective, scale and terminal responsibility; local to a search implementation |
| Policy/value inference | Observation batch → predictions | Codec/version, shape/dtype, action mapping/masking, value perspective, model identity |
| Supervision provider | State + supervision specification → analysis | Target authority, exact state/configuration, attempts and failures |
| Experiment task | Resolve/validate config; execute in a run context → artifact references | Inputs, resources, limits, progress and explicit completion |
| Experiment evaluator | Frozen evaluation specification + artifacts → assessment | Named metric definitions, feasibility gates, denominators, comparability and uncertainty |

A small player envelope contains move, root identity, implementation/resource
identities and work usage. Optional diagnostics are namespaced, schema-versioned
and validated by their owner. Unknown diagnostic payloads may be retained/displayed
generically but must not be silently treated as verified. This replaces the need
to extend every consumer whenever an algorithm adds a statistic. Existing v1
Choice/config bytes keep their meaning; when needed, explicit artifact migration
or backfill preserves the originals and lineage. Default runtime shims are excluded.

Keep configuration typed per implementation. An experiment supplies a configured
factory or local registry entry; production discovery uses explicit registrations
with lazy resource loading. Merely listing capabilities must not load Torch,
start an engine or require a native compiler. Player sessions are scoped to one
participant/game, with explicit reset/cache policy. Immutable model resources can
be shared, while mutable engine processes need session ownership or exclusive
leases. Possible multi-client server execution must preserve these boundaries.

### Python/native boundary

Maintain a readable Python referee as a differential reference. Treat a native
backend as another implementation of the same named ruleset, not a second rules
authority. Preserve rules/history identity even when native code uses compact
boards, incremental repetition counts and make/unmake internally. An internal
search hash is not the saved state hash.

Support two paths with the same semantic contracts:

1. Python experiments use ordinary scalar calls, custom evaluators and small
   search prototypes. This path prioritizes low iteration cost.
2. Throughput workloads enter native code for a complete search, batch step,
   replay batch or supported rollout segment. Hot node expansion, legal generation,
   transitions and relevant heuristic evaluation stay together within native code.

Porting only `legal_moves` may be a useful measured first increment, but its
microbenchmark cannot stand in for end-to-end throughput. Python callbacks at
every native search leaf are an explicit experimental mode with measured overhead.
Arbitrary Python plugins do not automatically become native-speed components.
Successful scalar mechanisms can later gain native implementations under shared
fixtures. Python models remain usable through **batched** inference boundaries.

For future learned search, native work may return a batch of pending leaf
observations; Python/PyTorch evaluates them and returns predictions keyed to those
requests. Native execution then continues. Model/request identity, cancellation,
batch ordering and scheduler effects must be specified by that slice. Do not
build this scheduler before a learned-search consumer needs it.

For training environments, batch stepping carries actions for multiple games and
returns observations, legal masks, rewards with perspective, and outcomes. It
must distinguish referee termination from workload truncation and preserve final
observations before any reset. This execution API does not move data selection,
teacher provenance, leakage checks or dataset assembly into the native core.

Use an in-process extension for the first local native backend. Own buffer
lifetimes and state handles explicitly; specify action representation, array
layout, dtype and errors at that boundary. Serialized JSON remains useful for
artifacts and transport, not for each search node. Use UCI for existing external
engines. Process isolation for a long job can wrap the extension without making
the game contract an RPC protocol.

Both [pybind11](https://pybind11.readthedocs.io/en/stable/advanced/misc.html) and
[PyO3](https://pyo3.rs/main/parallelism) document execution detached from Python's
interpreter lock. Python object access/callbacks still need appropriate interpreter
attachment. This supports a coarse boundary; it proves no speedup for qi.
C++ with pybind11 is a provisional first-port option; Rust with PyO3 is viable.
Language preference remains open and does not change domain ownership.

Choose a backend explicitly in a resolved run configuration. If a requested
native backend is unavailable, fail clearly; never silently benchmark Python
under a native label. Contract inspection and ordinary Python workflows should
remain usable without building the optional native extension.

### Experiments beyond engines and models

Generalize the execution/evidence envelope, while each task owns its domain
configuration and correctness. The current catalog stays the discovery layer;
authored conclusions remain in the owning work item/report.

```text
Question + scope + baseline + candidate + frozen evaluator + limits
  → resolve exact inputs, implementation and resource identities
  → preview intended executions and cost bounds
  → isolated runs, including failed and incomplete executions
  → correctness/feasibility checks and metric assessment
  → comparison and explicit promotion decision
```

A plan must identify what may change, what is frozen, the primary metric and its
direction, constraints, selection rule, budget and stop condition. For agent work,
also name the owned paths and required checks. Store exact candidate source or a
reconstructable revision/patch, dependency locks and input identities. Native runs
also retain compiler/version, build flags, target and binary digest. Each run has
its own outputs, seeds and resource allowance; concurrent candidates must not
share writable checkpoints or stores accidentally.

The evaluator version and input fixtures stay outside candidate ownership for a
comparison. Passing its feasibility gates is a prerequisite for ranking. A smaller
runtime with changed outputs is not a performance-only win. A storage experiment
might require identical selected rows and provenance before comparing p95 query
latency; a sampler experiment might require zero leakage and exact quotas before
comparing coverage; an engine experiment might require replay conformance before
comparing search throughput.

Deterministic metric computation does not make runtime, GPU training or game
sampling deterministic. Declare repetitions, tolerances and aggregation where
needed. Keep development selection separate from frozen confirmation. “Best”
means best feasible candidate under the declared protocol; it may also be none
or inconclusive. Ranking never silently changes a production default.

Retries and resumptions preserve the existing domain runner's evidence semantics.
A shared job describes execution scheduling/progress; it is not an experiment or
a universal promise of resume support. Adapt existing runners first, preserving
their partial-result and resource-limit behavior. Add a small non-engine task to
demonstrate the general harness instead of designing a workflow DSL.

### Ergonomics and enforcement

- A candidate needs one implementation/configuration, task-local tests and a
  plan; it need not enter the global player/model catalog before comparison.
- A supported extension has a public entry point, configuration schema, clear
  resource requirements, tiny fixture and contract tests. A short module guide
  states what it can import and how it is evaluated.
- Enforce forbidden imports in CI, including package initialization effects.
  Keep fast checks scoped to the changed module and its contract consumers;
  retain the full application gate for integration changes.
- Keep inspection, preview, compare and reproduction available from structured
  Python operations and CLI output. Frontend pages project the same operations
  and artifacts; domain-specific details remain optional renderers.
- Use separate worktrees/output roots when concurrent work needs isolation.
  Contract/schema changes are explicit integration work, not incidental edits
  inside a candidate. This design does not claim arbitrary changes are independent.

### Migration and proof

| Slice | Deliverable | Exit evidence |
| --- | --- | --- |
| 1. Establish a usable seam | Extract game interchange from session/transport records; introduce a referee port around the current implementation and migrate its consumers directly. Start the package boundary required by this slice. | Golden v1 snapshots/hashes and outcomes unchanged; migrated consumers pass; game-contract imports load no players/models/adapters. |
| 2. Exercise native substitution | Implement the same ruleset in one native backend with scalar conformance plus one batch operation. | Differential trajectories, terminal/repetition cases, illegal-action atomicity, action order, hashes, batch/scalar equivalence; measured binding and end-to-end costs. |
| 3. Remove research coupling | Separate observation/model definitions from player adapters and generic UCI transport from teacher/player roles; let implementations own configs/resources. | Train and infer the existing checkpoint unchanged; add one alternate implementation without editing shared schema branches or API/FE. |
| 4. Generalize experiment execution | Extract search-specific execution under evaluation; adapt one existing runner and one non-engine task to a minimal shared run/assessment envelope. | Preview, isolated outputs, failures/partial results, reproducible comparison and catalog discoverability; no regression in old readers. |
| 5. Move the remaining measured hot loop | Port a complete selected search/rollout mechanism, or integrate batched inference when its consumer exists. | Contract checks plus representative throughput/latency/memory evidence; separate tests for any changed search or learning treatment. |
| 6. Consume through API/FE | Shared typed operations, domain routers and artifact navigation following the related design. | CLI/HTTP semantic parity, generated types, relevant browser checks and `make check`. |

Slices 3 and 4 can proceed independently once their contract ownership is settled;
they do not need to wait for a native speed result. A new native referee is judged
on state/outcome conformance. Exact player choices are required when porting the
same deterministic algorithm/order/RNG semantics, not for unrelated player recipes.
Backend changes alone must not alter semantic state fingerprints. A cross-language
seed is insufficient without matching the PRNG and ordering contract when exact
trajectory equality is required.

Freeze the native comparison protocol before timing: representative scalar
search and batch-generation workloads, isolated alternating baseline/candidate
runs, cold/warm conditions, identical outputs, memory and conversion costs.
Training-generation measurements must separate referee, teacher, persistence,
encoding and model time. Numeric adoption thresholds belong to that bounded
study after its workload/target is chosen; none is fabricated here.

### Round 1 — locked

The user accepted D1-D8 on 2026-09-21, with explicit refinements to D4/D5 and a
small-first constraint on D7. These answers must not be reopened without a new
material conflict or requirement.

| ID | Choice | Accepted decision / owner |
| --- | --- | --- |
| D1 | First native acceptance workload | Batched gameplay/trajectory production with controlled actors; ADR-0012. |
| D2 | Owned versus reused implementations | Own semantics, fixtures and reference; permit conforming accelerated implementations; retain owned research search. ADR-0012 supersedes ADR-0001. |
| D3 | Cross-language substitution | Semantic/coarse-capability substitution; successful Python components may require porting or batching for speed. ADR-0012. |
| D4 | Independence | One repository; separate package TOML declarations managed by uv; lazy loading; no independent releases/services initially. ADR-0013. |
| D5 | Compatibility | Refactor internal APIs/commands freely; no external consumers; mostly no shims. Separate explicit migrations/backfills where needed; preserve original evidence and interpretation. ADR-0013. |
| D6 | Multi-game scope | Xiangqi-specific game contracts; game-neutral experiment task boundary; generalize game contracts after a second game provides evidence. ADR-0012 and core model. |
| D7 | Experiment system | Minimal local task/evaluator/run envelope; use existing runners/catalog; start small and add machinery only after demonstrated use. Core model and experiment method. |
| D8 | Agent authority | Bounded trials, retained failures, selection and tested integration preparation; ranking alone does not change defaults. Automatic integration can be explicitly authorized per bounded experiment. Experiment method. |

### Round 2 — locked

The user accepted D9-D13 and asked that sessions and process isolation account for
a possible server mode with multiple/batch clients. This adds a design constraint,
not authorization to build or deploy a service now.

| ID | Choice | Accepted decision / owner |
| --- | --- | --- |
| D9 | Dependency resolution scope | One uv workspace/lock for supported packages; excluded separately locked study projects for incompatible dependencies; isolated package dependency checks. Project direction. |
| D10 | Reproducibility guarantee | Exact rules/replay and controlled deterministic conformance; stable per-game RNG across batching; pinned execution conditions for exact regeneration; no universal bitwise GPU/cross-hardware guarantee. Core model. |
| D11 | Player lifetime | Per-participant/game mutable state, reset between games by default; explicitly declared cache modes; reusable immutable models and owned/leased engine resources. Account for multi-client server mode. Core model. |
| D12 | Run isolation | Fresh worker process and output root per recorded trial, serial by default; direct interactive calls remain available. A future server may coordinate them without erasing run isolation. Experiment method. |
| D13 | Native platforms | Apple Silicon macOS and Linux x86_64 CPU; no referee dependency on GPU/model devices; Windows and GPU-native simulation deferred. Project direction. |

[uv's workspace documentation](https://docs.astral.sh/uv/concepts/projects/workspaces/)
confirms per-member project files share a lockfile and normally an environment.
Conflicting requirements can instead use separate projects/path dependencies.
Workspaces cannot enforce declared-import isolation. D9 is therefore distinct
from the already accepted package-owned declarations.

### Round 3 — accepted low-fidelity direction

The current [HTTP adapter](../../../src/qi/api.py) restores state from snapshots
on game requests; [TraceJobs](../../../src/qi/lab.py) owns one active trace worker.
Neither establishes the new persistent-session/shared-batch service semantics.

| ID | Choice | Accepted direction |
| --- | --- | --- |
| D14 | Serving purpose | Start conceptually with optional game/player serving for multiple/batch clients, with inference and experiment operations distinct as needed. Keep the design low fidelity; refactor around demonstrated workloads. |
| D15 | Deployment/ownership | Initially a single host and owner with trusted clients such as scripts, rollout workers and UI. This is a provisional scope, not a fixed deployment architecture. |

The user explicitly rejected high-fidelity decision/implementation detail here.
Session/resource ownership and per-trial evidence remain governing constraints.
Transports, API signatures, queues, scheduling, batching algorithms, cross-run
resource pooling and deployment topology are deliberately unspecified. Do not
treat these deferred choices as blockers or manufacture another interview round
before a workload makes a particular choice consequential.

Build a concrete server only when a consumer justifies it. Keep core execution
usable directly and transport-independent, with explicit state ownership. No new
server ADR, service implementation or detailed serving specification is needed now.

Native language/backend selection follows platform and dependency choices plus
a bounded feasibility inspection; no library or native trial has been selected
or executed. Existing ruleset/history and artifact identity constraints remain in
force. Exact package names, schemas and performance thresholds belong to the
concrete implementation/measurement proposal, not speculative framework design.

## Outcome and handoff

No unresolved owner choice blocks the first extraction. Accepted ownership,
package/migration, experiment and runtime constraints are promoted to the linked
authorities. D14/D15 intentionally remain revisable directions rather than detailed
contracts. This completes the decision task, not the runtime redesign.

[AB-ARCH-002](AB-ARCH-002-game-package-boundary.md) owns the first implementation:
extract game interchange and a used referee seam into a uv-managed package,
migrate consumers directly, and verify preserved replay/hash/outcome behavior
plus isolated dependencies. Native selection and measured workload optimization
follow that seam. Its [package guide](../../../packages/qi-game/README.md) now
documents the implemented boundary and its remaining limits.

## Status History

| Date | Actor | From | To | Reason / evidence |
| --- | --- | --- | --- | --- |
| 2026-09-21 | GPT-6 | — | wip | User requested architecture redesign; repository and related API/FE discussion inspected; proposal under discussion. |
| 2026-09-21 | GPT-6 | wip | done | All upfront choices settled or deliberately deferred; governing decisions promoted and first build slice prepared as AB-ARCH-002. |

## Implementation Ledger

- **2026-09-21 — finding:** Live import inspection identified snapshot/player,
  training/player-model, data/evaluation and search-specific experiment coupling.
  Sources are linked in the context table. Consequence: extract semantic owners
  and replaceable execution before broad API/FE restructuring. Follow-up: settle
  the decisions above. Review: pending.
- **2026-09-21 — decision proposal:** Recommend modular boundaries, coarse native
  execution and a task-neutral experiment envelope with domain-owned correctness.
  No runtime refactor or benchmark executed. Follow-up: record user choices before
  promoting architectural authority. Review: pending.
- **2026-09-21 — finding:** User endorsed the direction and requested grilling.
  Expanded the decision frontier to D1-D8, including workload priority, owned
  versus reused implementations, cross-language substitution and agent promotion
  authority. Follow-up: resolve this round before dependent design choices.
  Review: pending.
- **2026-09-21 — decision:** User accepted round 1, refined D4 to uv-managed
  per-package TOML and lazy loading, refined D5 to free refactoring with mostly
  no shims and separate migrations/backfills, and emphasized small-first D7.
  Promoted settled decisions to ADR-0012/0013, models, glossary and experiment
  method; revised implementation sketches accordingly. Follow-up: D9-D13.
  Review: ratified.
- **2026-09-21 — decision:** User accepted D9-D13 and added possible multi-client/
  batch server mode as a constraint on Player sessions and recorded-run isolation.
  Promoted dependency/platform, reproducibility/session and worker policies to
  project direction, models, glossary and experiment method. Engine processes are
  explicitly mutable resources, not shared immutable model weights. Follow-up:
  clarify server purpose and deployment scope in D14/D15. Review: ratified.
- **2026-09-21 — decision:** User accepted D14/D15 as deliberately low-fidelity
  directions, allowing future refactoring around workloads. Removed prospective
  server details from the active proposal, updated owning guidance and prepared
  AB-ARCH-002. Architecture interview complete; no runtime changes or server build.
  Follow-up: implementation under the accepted boundaries. Review: ratified.
