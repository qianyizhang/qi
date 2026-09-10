---
description: Coordinate AB-DATA-008 generation policies with concurrent AB-DATA-007 collection implementation.
scope: multi-agent coordination report
status: experimental
last_update: 2026-09-11
document_class: coordination
produced_by: "handoff@0.8.0 · agent=GPT-6 · effort=unspecified · 2026-09-10"
---

# Claim ledger — generation and collection integration

**Stop condition:** Implement and verify locked generation policies, then test
against the released collection API or leave an executable I/O handoff.
**Mode:** parallel · IMPLEMENT
**Authorized transitions:** User authorized build/test and same-checkout coordination.

| Surface | Owner | Status | Notes |
| --- | --- | --- | --- |
| `src/qi/training_data/generation_policies.py`, `test_generation_policies.py` | generation policy worker | done | Pure actor/sampler contracts; 38 focused tests passed, no storage changes. |
| `src/qi/training_data/generation_runner.py`, `generation_io.py`, generation runner tests | scaling task integrator | done | Orchestration, temporary boundary if required, collection adapter. |
| `scripts/run_generation_pilot.py`, generation recipes and owned integration tests | scaling task integrator | done | Bounded engineering/pilot runs into fresh ignored artifacts. |
| `records/work-items/items/AB-DATA-008-generation-scaling-pilot.md`, this ledger, generation guide/handoff | scaling task integrator | done | Accepted policies and measured status. |
| Existing store, snapshots, candidate evidence, collection generation, CLI, dependency files, AB-DATA-007 and shared module guides | Assess AB-DATA-007 readiness task | done | User's concurrent task owns these; coordination message sent. No edits from scaling task. |
| `.pytest_cache/`, `.ruff_cache/`, per-test temporary directories | each focused test runner | done | Independent test outputs; no tracked-fixture rewrites. |
| Full repository checks and shared generated outputs | integrators by coordination | done | Run after writers settle; no broad formatting during parallel edits. |

Same checkout avoids copying unfinished infrastructure across worktrees. No
cross-task commits are made by this integrator. The policy worker must report
its exact API, verification and release before final integration checks.

## Boundary coordination

The collection task released its initial implementation, then the user reopened
it for independent review and a scoped commit. Its owner retained store/snapshot
ownership during that review. The integrator's narrow `selected_only` snapshot
field and predicate were handed to that owner to preserve in the infrastructure
commit; the integrator stopped writing `snapshots.py`. Generation policy files,
runner, guide, recipes, tests, this ledger and AB-DATA-008 remain outside that
commit. This is shared-checkout coordination; no merge request is required.

## Closeout

Infrastructure landed as `9ab7e1a`. Generation completed 51 focused checks and the
full repository gate (545 Python passes, one MPS skip, five browser passes), then
verified six real-engine trajectories and selected-only SQL/Parquet export.
The integrator added only a guide link to the released module README after the
infrastructure commit. Generation code, recipes, guide, evidence and AB-DATA-008 are included in the
generation closeout commit. All claims are done and workers have stopped;
AB-DATA-008 owns the remaining calibration. No overnight generation was dispatched.
The final resource-guard gate passed 552 Python tests (one opt-in MPS skip) and
five browser tests, superseding the earlier 545-test engineering gate.
