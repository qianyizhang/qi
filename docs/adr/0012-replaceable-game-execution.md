---
description: Own game semantics and reference behavior while allowing replaceable accelerated execution.
scope: architecture decision
status: stable
last_update: 2026-09-21
document_class: coordination
---

# ADR-0012: Own semantics; allow replaceable game execution

- **Status**: accepted
- **Last Update**: 2026-09-21
- **Serves**: Referee ownership and implementation substitution in [the core model](../models.md).
- **Supersedes**: [ADR-0001](0001-own-referee-and-search-use-external-teachers.md).

Qi owns its named rules, conformance fixtures and readable reference referee.
Accelerated implementations may be authored locally or reused when they conform
to those semantics. Python remains the experimentation and ML environment;
native execution may own complete hot loops behind coarse capabilities.

## Context

The earlier decision deliberately kept the referee and search in Python for
learning. The user now wants independently developed experiments and native
throughput for training trajectories. Requiring every acceleration component to
be authored in qi would make infrastructure construction a prerequisite for that
research. The decision interview is recorded in
[AB-ARCH-001](../../records/work-items/items/AB-ARCH-001-modular-runtime.md).

## Considered Options

- **Require qi-authored Python execution** — preserves the original implementation
  approach but constrains backend experimentation and throughput work.
- **Require every native component to be qi-authored** — provides control and
  learning opportunities at the cost of making them mandatory.
- **Own semantics and permit conforming implementations** — selected; retains
  educational reference/search work while allowing acceleration to evolve separately.

## Consequences

The referee still owns legality, transitions and outcomes. Backend selection
does not change ruleset identity or permit history-dependent adjudication to be
replaced with board-only reasoning. Game interfaces remain Xiangqi-specific until
a second game establishes the need for generalization.

Python component experiments remain first-class. Shared semantics do not promise
that arbitrary Python per-node callbacks achieve native throughput; a successful
prototype may require porting or batching. Batched gameplay and trajectory
production with controlled actors is the first native acceptance workload.
No native implementation, language or measured speedup is selected by this ADR.

Qi-authored search remains a learning surface. External teachers and explicit
external-engine players retain distinct roles; generation-time teacher access
does not grant evaluated players tools. Teacher bootstrapping remains available
without requiring from-scratch learning. Conformance and performance evidence
are prerequisites to adopting a backend, not consequences of this decision.
