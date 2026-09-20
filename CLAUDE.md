---
description: System rules, invariants, and guidelines for developer agents.
scope: system guidelines
status: stable
last_update: 2026-09-21
document_class: coordination
---

# CLAUDE.md

This file is the repository binding for developer agents. Keep project-specific
identity, invariants, authority, and commands here. Portable doctrine lives in
`docs/rules/` and is updated through the governance kit.

## What this project is

A personal game-learning laboratory for Xiangqi, neural search, and LLM post-training.

The learning destination and staged stack live in `docs/project.md`. Current
implementation supports a shared local frontend with configurable players,
experiment reports and trace jobs, structured CLI operations,
and deterministic replay under `docs/xiangqi-training-v1.md`.

## Core model and governing invariant

The referee owns rules and outcomes; players choose actions; Training Data owns
example selection, supervision provenance and dataset composition; trainers
prepare model inputs and update weights. Replay must reproduce results under an
explicit ruleset and history. `docs/models.md` owns the accepted relationships
and routes the Training Data implementation; `docs/project.md` owns
project direction and constraints.

## Authority map

Use `docs/index.md` to find the authorities relevant to the task; it owns the
human-facing flow map. Read other areas when their contracts or evidence affect
the work.
Name repository-specific contracts, schemas, ADRs, and module authorities here
or link them from that index. `README.md` owns human setup and usage.

## Working principles

- **Concise is the key.**
- **Reinforce vocabulary in context.** When wording suggests uncertainty or a
  forgotten distinction, connect it to `docs/glossary/ddd.md` with a brief plain
  explanation or example, then reuse the term naturally. State the interpretation
  and continue unless ambiguity changes the work. Preserve the user's intended
  meaning and settled decisions; familiar terms must not constrain a new idea.
  `domain-modeling` records accepted terminology; `glossary-drill` handles
  deliberate recall practice when requested. Ordinary work needs no quiz.
- **Full means full.** When asked to complete, extend, or verify coverage, do the
  actual work — never relabel a partial run as "full".
- Complete the requested deliverable, applicable verification, and necessary
  documentation within the authorized scope. Reuse authorization already given;
  ask again only for material unresolved choices or actions outside that scope.
- Choose verification by changed surface under `docs/rules/testing.md` and the
  commands below. Preserve required gates and re-derive numeric claims from
  current evidence.
- **Symlinks are load-bearing** (see below). Before `rm` or bulk file ops near
  symlinks, verify their targets.

## Agent assets

`.codex/` holds the real shared agent assets. `.agents` and `.claude/skills` are
relative symlinks into it, declared in `[tool.doc_governance.symlinks]` and
created by `scripts/bootstrap_agents.py`. Edit skills only under
`.codex/skills/`; resolve symlink targets before deleting anything nearby.

## Experiment recall

For experiment ideas, previous-result questions, and authorized trials, use the
local [`experiment` skill](.codex/skills/experiment/SKILL.md) for catalog recall
and evidence recording. [ADR-0007](docs/adr/0007-experiment-recall-and-evidence.md)
fixes ownership; [the method](docs/experiments.md) owns the workflow.

## Commands

```bash
make install   # sync Python/web deps and bootstrap agent symlinks
make lint      # Ruff lint/format checks and docs (check_docs.py)
make test      # test suite
make test-game # isolated game sdist/wheel and declared-dependency checks
make test-native # optional native wheel isolation and generation/HTTP conformance
make test-learning # optional CPU policy-training integration checks
make test-learning-mps # opt-in Metal training and CPU checkpoint reload
make check     # lint, tests, and production browser build
make format    # auto-format and auto-fix
make play      # build and serve the local browser board
```

## Architecture rules

Accepted redesign: [replaceable execution](docs/adr/0012-replaceable-game-execution.md)
and [uv-managed packages with direct migration](docs/adr/0013-modular-packages-and-direct-migration.md).
Use lazy implementation/resource loading and package-owned dependencies. Refactor
internal consumers directly, without default compatibility shims; preserve evidence
and use explicit migrations/backfills when needed. The [decision work item](records/work-items/items/AB-ARCH-001-modular-runtime.md)
routes the migration slices and deferred workload choices. The first game package
boundary is implemented. Possible server mode remains low fidelity;
do not turn it into a detailed framework before a workload needs one.

Keep `packages/qi-game/` independent of application, player, training, UI and model
SDKs. Its [guide](packages/qi-game/README.md) owns `qi_game` contracts, the referee
protocol, explicit Python reference use and isolated package checks.
`src/qi/protocol.py` owns application requests and player/session evidence;
CLI and HTTP consume the game package. Supported packages share the root uv lock.
The optional [native package](packages/qi-game-native/README.md) owns C++ build
dependencies and persistent trajectory execution; policy generation accepts it
explicitly. Default setup and backend selection remain Python.
The React board consumes legal moves; it does not implement rules. Boundary
contracts arrive with behavior; avoid speculative packages. Vocabulary authority:
`docs/glossary/ddd.md`. Automated players live in `src/qi/players/`, each with a
README and tests. Register implementations once in its catalog; adapters discover
metadata and dispatch through the shared `choose` boundary.
Implemented architecture: [shared frontend](docs/adr/0005-shared-local-frontend.md)
and [independent player bindings](docs/adr/0006-independent-player-bindings.md).
The [interface guide](docs/interface.md) owns implemented app behavior; the
[frontend work item](records/work-items/items/AB-UI-002-consolidated-lab.md)
retains delivery acceptance and verification evidence.
Training data generation and frozen mixtures live in `src/qi/training_data/`; its
README owns formats, phase policies, quotas and compatibility. The optional
trainer lives in `src/qi/learning/`; checkpoint-backed inference
lives in its player module. `QI_POLICY_CHECKPOINT` selects an explicit local file,
loaded and pinned per process. HTTP does not accept checkpoint paths.
[ADR-0003](docs/adr/0003-pytorch-mps-training.md) fixes PyTorch with explicit CPU/MPS
training, CPU inference, and an optional GPU test lane. The trainer guide owns
nested-data learning curves and their partial-run semantics.

`src/qi/experiments/` owns local search plans, execution evidence, validation,
and report generation. Reports are projections; players/referee remain outcome
authorities. Optional recording is observational and separate from benchmark
timing. See its README for run and trace completeness semantics.

## Testing

Portable doctrine: `docs/rules/testing.md`.

`make test` covers referee rules, replay, and CLI/HTTP parity. Colocated rule
tests live in `packages/qi-game/src/qi_game/`; central `tests/` owns integration checks.
Default checks require no engine, GPU, network, or service after dependency
installation. Browser builds, type checks, and request-lifecycle unit tests run
in `make check`. The optional `npm run test:e2e --prefix web` lane starts a local
server and Chromium; see README for setup.

For prose and skill guidance, run `.venv/bin/python scripts/check_docs.py`; check
changed skill references and invocation metadata as applicable. For a standalone
explainer, use its binding and validator plus visual inspection. For runnable
Python behavior, run affected tests with `uv run pytest <paths>`; include shared
consumers when contracts change. Use `make check` for cross-cutting application or
build changes and required integration gates. Optional engine, learning, MPS, and
browser E2E lanes apply when the requested scope needs them.

Local tests use disposable fixtures and require no external service by default.
Run the applicable checks, fix failures caused by this change, and rerun affected
checks within the authorized task. Preserve failures outside that scope separately.

## Skills

Portable doctrine: `docs/rules/skill.md`. `docs/index.md` §Main flows is the
human-facing router.

Invocation policy:

- **Explicit-user only:** `explain-layman` and `grill-with-docs`. Their
  `disable-model-invocation` and `agents/openai.yaml` policy fields enforce this
  for Claude and Codex. An agent may suggest either, but does not invoke it.
- **Shared grill loop:** model-invoked `grilling` (composed by
  `grill-with-docs`, `show-gap`, and any local planner that needs the loop).
- **Bounded automatic audit:** `show-gap` answers feature-fit questions or
  grounds a larger authorized change. Use `next-slice` for readiness and priority.
  Return to the parent task after a supporting audit; preserve explicit review-only
  requests. Decision interviews and durable specifications need matching user intent.

## Housekeeping (after a task)

- Keep repository bindings here and promote portable refinements to the kit.
- Route precise unfinished work through `records/work-items/backlog.md`; use an
  optional Campaign only at the threshold in `docs/rules/governance.md`.
- Follow `docs/rules/doc.md` for documentation lifecycle and frontmatter.
- For documentation hygiene involving experiments, follow `docs/experiments.md`
  for evidence and correction rules. Check the linked module guide for executable
  semantics and the cited work record or run evidence for measured claims; keep
  imitation agreement distinct from playing strength.
