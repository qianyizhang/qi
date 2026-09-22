---
description: Supported two-worker generation retains a 1.70x throughput gain including validated collection publication.
scope: policy generation integration and bounded throughput evidence
status: stable
last_update: 2026-09-22
document_class: report
report_outcome: promoted
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-22"
---

# Opt-in parallel generation

The supported policy runner now accepts `--workers 2`. It retains independent
source shards, stops the pool on failure, resumes completed work explicitly and
publishes one validated SQLite collection. Serial remains default. The
[guide](../../docs/data-generation.md#opt-in-parallel-generation) owns behavior;
[AB-DATA-010](../work-items/items/AB-DATA-010-parallel-generation.md) owns the build
and predeclared comparison.

The [previous isolated-worker experiment](2026-09-21-generation-optimization.md)
measured 1.770x throughput without production combination. The integrated path
retains **1.704x median paired throughput**, including CLI startup, source archive,
generation and combined publication. Every paired repeat improves; all six runs
have identical normalized results.

| Round | Serial wall | Two-worker wall | Paired throughput |
| --- | ---: | ---: | ---: |
| 1 | 27.979 s | 16.070 s | 1.741x |
| 2 | 24.925 s | 14.909 s | 1.672x |
| 3 | 27.071 s | 15.888 s | 1.704x |

Median wall time falls from **27.071 to 15.888 seconds**. Bounded replay validation
and combination take **0.550 seconds** median. Sampled process-tree RSS rises from
**652.8 to 1,241.7 MiB**. It sums resident sets, potentially double-counting shared
pages and missing brief peaks; it is not unique physical memory or a hard limit.
The sampler includes the study coordinator and CLI/worker/teacher descendants.

Each execution uses the prior pinned one-thread Pikafish/NNUE, seed 17, four
development sources with four games each, 96 additional plies, a 10k-node plausible
actor and 10k/100k supervision. Complete CLI invocations alternate serial/parallel,
parallel/serial, serial/parallel. There are no overlapping builds or tests, no
discarded repeats and no teacher-budget changes. Independent post-timing auditing
finds **16 games, 1,402 additional plies, 169 selected occurrences and 545 retained
analysis records** in every cell. The analysis count includes actor evidence;
it is not a count of distinct training labels.

The portable normalized digest is
`ab90ed83f25ed29f0b2569cd5faeffbcf5b29379488a3a4610f768b2239a25c6`,
also matching the preceding serial/sharded study. An actual completed parallel
output resumes with all 16 games reused and an unchanged combined-file SHA-256.
That reuse creates a new execution receipt and makes no teacher calls.

## Correctness and recovery

Each source has one process/collection writer and independent persistent teachers.
The two slots preserve original source/game identities and deterministic RNG
streams. Combination validates replay, outcomes, occurrence indexes, actor keys,
analysis specifications/requests and retained candidate evidence. It preserves
portable attempts, remaps local SQL IDs, and retains first-success ordering within
an occurrence/specification. Failed/interrupted evidence remains inspectable.

A new combined file is published only after all sources complete and validation
passes. A cross-shard family/start/trajectory split conflict leaves it unpublished.
The coordinator stops dispatch on failure, interrupts/reaps active workers and
teachers, and retains shard prefixes. Explicit resume reuses completed games and
restarts incomplete games. Published output is reused without rewriting rows;
external modifications are detected and never overwritten.

Fifteen focused integration tests pass, covering exact serial parity, portable
attempts and first-success ordering, snapshot export/verification, two active
workers with queued work, SIGINT/SIGTERM, child cleanup, failure/resume, preserved
completed games, publication interruption, modified outputs, corrupt occurrences,
cross-split conflicts, deadlines, locks, preview and unavailable resource guards.
`make check` passes **837 Python tests with one optional MPS skip**, five frontend
tests, lint/docs/API/type checks and production builds. Three additional focused
checks were added afterward; production source stayed unchanged. The study
controller subsequently gained an explicit error for unavailable RSS sampling;
all recorded cells have available nonzero measurements and retain the exact
executed controller.

## Decision and limits

The 1.3x predeclared advancement threshold passes with exact output agreement.
Adopt the opt-in two-worker path. This is one local macOS machine and a fixed
source workload, with three timing repetitions, not a population estimate,
playing-strength result or proof that two workers are optimal. No Linux execution
or large overnight run was performed.

The first supported boundary requires independent whole sources and a fresh owned
output. External collections, generated parents, implementation-repair
continuations and the OS-write guard remain serial. Parallel resume requires the
same frozen implementation/runtime/configuration. Pool RSS and free-space stops
are sampled; abrupt SIGKILL/host failure cannot execute process cleanup. Retaining
shards and a combined collection costs additional disk space. Larger worker counts,
aggregate OS-write accounting and broader workload scaling remain separate work.

[Compact results](../../data/evaluation/parallel-generation-20260922.json) retain
all cells and evidence hashes. [Reproduction](../../data/experiments/parallel_generation_v1/README.md)
owns commands. Raw runs, the executed controller, package/application archives,
logs and resume evidence remain under `artifacts/parallel-generation-20260922`;
1,177 archived files were checked against their recorded hashes.
