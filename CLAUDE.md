---
description: System rules, invariants, and guidelines for developer agents.
scope: system guidelines
status: stable
last_update: 2026-09-08
document_class: coordination
---

# CLAUDE.md

This file is the repository binding for developer agents. Keep project-specific
identity, invariants, authority, and commands here. Portable doctrine lives in
`docs/rules/` and is updated through the governance kit.

## What this project is

A personal game-learning laboratory for Xiangqi, neural search, and LLM post-training.

The learning destination and staged stack live in `docs/project.md`. Current
implementation supports local browser pass-and-play and baseline opponents, structured CLI operations,
and deterministic replay under `docs/xiangqi-training-v1.md`.

## Core model and governing invariant

The referee owns rules and outcomes; players choose actions; trainers update
weights. Replay must reproduce results under an explicit ruleset and history.
See `docs/project.md` for the implementation constraints.

## Authority map

`docs/index.md` routes authority by concern and owns the human-facing flow map.
Name repository-specific contracts, schemas, ADRs, and module authorities here
or link them from that index. `README.md` owns human setup and usage.

## Working principles

- **Concise is the key.**
- **Full means full.** When asked to complete, extend, or verify coverage, do the
  actual work — never relabel a partial run as "full".
- **Before claiming done, verify.** Run the repository checks below and
  re-derive numeric claims from current evidence.
- **Symlinks are load-bearing** (see below). Before `rm` or bulk file ops near
  symlinks, verify their targets.

## Agent assets

`.codex/` holds the real shared agent assets. `.agents` and `.claude/skills` are
relative symlinks into it, declared in `[tool.doc_governance.symlinks]` and
created by `scripts/bootstrap_agents.py`. Edit skills only under
`.codex/skills/`; resolve symlink targets before deleting anything nearby.

## Commands

```bash
make install   # sync Python/web deps and bootstrap agent symlinks
make lint      # Ruff lint/format checks and docs (check_docs.py)
make test      # test suite
make test-learning # optional CPU policy-training integration checks
make check     # lint, tests, and production browser build
make format    # auto-format and auto-fix
make play      # build and serve the local browser board
```

## Architecture rules

Keep `src/qi/game.py` independent of training, UI, and model SDKs.
`src/qi/protocol.py` owns validated interchange; CLI and HTTP are adapters.
The React board consumes legal moves; it does not implement rules. Boundary
contracts arrive with behavior; avoid speculative packages. Vocabulary authority:
`docs/glossary/ddd.md`. Automated players live in `src/qi/players/`, each with a
README and tests. Register implementations once in its catalog; adapters discover
metadata and dispatch through the shared `choose` boundary.
The optional trainer lives in `src/qi/learning/`; checkpoint-backed inference
lives in its player module. `QI_POLICY_CHECKPOINT` selects an explicit local file,
loaded and pinned per process. HTTP does not accept checkpoint paths.

`src/qi/experiments/` owns local search plans, execution evidence, validation,
and report generation. Reports are projections; players/referee remain outcome
authorities. Optional recording is observational and separate from benchmark
timing. See its README for run and trace completeness semantics.

## Testing

Portable doctrine: `docs/rules/testing.md`.

`make test` covers referee rules, replay, and CLI/HTTP parity. Colocated rule
tests live in `src/qi/test_game.py`; central `tests/` owns integration checks.
Default checks require no engine, GPU, network, or service after dependency
installation. Browser builds, type checks, and request-lifecycle unit tests run
in `make check`. The optional `npm run test:e2e --prefix web` lane starts a local
server and Chromium; see README for setup.

## Skills

Portable doctrine: `docs/rules/skill.md`. `docs/index.md` §Main flows is the
human-facing router.

Invocation policy:

- **Explicit-user only:** `explain-layman` and `grill-with-docs`. Their
  `disable-model-invocation` and `agents/openai.yaml` policy fields enforce this
  for Claude and Codex. An agent may suggest either, but does not invoke it.
- **Shared grill loop:** model-invoked `grilling` (composed by
  `grill-with-docs`, `show-gap`, and any local planner that needs the loop).
- **Bounded automatic audit:** `show-gap` may be selected for an ambiguous
  readiness/fit question because its first phase is read-only repo grounding.
  Extending it into a decision interview or writing a specification requires
  clear user intent.

## Housekeeping (after a task)

- Keep repository bindings here and promote portable refinements to the kit.
- Route precise unfinished work through `records/work-items/backlog.md`; use an
  optional Campaign only at the threshold in `docs/rules/governance.md`.
- Follow `docs/rules/doc.md` for documentation lifecycle and frontmatter.
