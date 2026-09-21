---
description: Safe scalar stepping removes native copy overhead; two isolated workers improve matched teacher generation.
scope: native stepping and bounded generation concurrency
status: stable
last_update: 2026-09-21
document_class: report
report_outcome: promoted
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# Safe native stepping and two-worker generation

The [profile's two next steps](2026-09-21-generation-bottlenecks.md) have separate
results. Removing native scalar state copying gives **1.882x** identical-action
throughput and **1.086x** controlled-generation throughput over the previous native
implementation. Two isolated Python-reference teacher/game workers give **1.770x**
verified generation throughput over identical serial work.

[AB-ARCH-008](../work-items/items/AB-ARCH-008-atomic-native-step.md) owns the native
implementation; [AB-DATA-009](../work-items/items/AB-DATA-009-two-worker-generation.md)
owns the concurrency experiment. [Compact results](../../data/evaluation/generation-optimization-20260921.json)
retain every cell, paired ratio and raw evidence hash. The
[study guide](../../data/experiments/generation_optimization_v1/README.md) owns commands.

## Native change and matched results

Scalar stepping previously copied the whole history and repetition map, advanced
that copy, then destroyed the previous state. It now prepares a fixed-size next
board/key, reserves history capacity geometrically and prepares one repetition
entry. Only after the final potentially throwing operation succeeds does it update
the board, history and counters. Logical state survives allocation failure; private
capacity/cache changes do not represent a move. No whole-state copy remains in
scalar stepping. Batch execution retains its all-or-nothing full-state staging.

The baseline is archived commit `b1eff30` with its original installed extension;
the candidate uses a separate frozen runtime and rebuilt binary. Three alternating
fresh-process rounds per workload, on the same local Apple Silicon Mac:

| Workload | Old native median | New native median | Python median | Paired new/old native throughput |
| --- | ---: | ---: | ---: | ---: |
| Full observations for 17,169 fixed actions | 0.2804 s | 0.1490 s | 0.4129 s | **1.882x** |
| Controlled generation: 64 games, 417 selected positions | 2.2874 s | 2.1119 s | 2.4828 s | **1.086x** |
| Teacher generation: 16 games, 169 selected positions | 28.7913 s | 29.1871 s | 29.1303 s | **0.986x** |

The action comparison uses three cold-reference repetitions per cell, inspecting
every position and independently checking history hashes after timing. New native
throughput is **2.757x Python** at that matched boundary. This clears the predeclared
20% component-improvement gate; controlled generation improves in all three pairs.

There is **no teacher-pipeline speedup**. Its median paired throughput is 1.4%
lower than old native, within the predeclared 5% median-regression flag. One retained
candidate round takes 32.255 s versus baseline 28.962 s; waited-child CPU rises
from 25.706 s to 28.863 s despite identical trajectories, labels and node counts.
This coincides with variable external search cost; the data do not isolate a
referee-caused teacher regression. No repeat is discarded. The previous profile
already showed that this workload spends about 90% of its time waiting for search.

All nine controlled cells match 17,169 plies/417 selections; all nine teacher cells
match 1,402 additional plies/169 selections/338 supervision calls. Actor decisions,
outcomes and normalized labels match, as do all nine action cells. Native remains
explicit: the measured full pipelines do not establish the existing 1.2x threshold
over Python. The optimization does not change defaults, teacher budgets or WAL/FULL.

## Two-worker result and resource cost

This uses the production Python-reference path. Four development families are
partitioned alternately into two eight-game collections. Source IDs and per-source
game indices remain unchanged. Each schedule executes the same two shard configs:
serially with one active worker, or concurrently with two. Both retain one-thread
Pikafish, seed 17, 96 additional plies, a 10k-node three-candidate actor and
10k/100k-node supervision. No sealed test source or training export is involved.

| Metric, median of three rounds | Serial shards | Two workers |
| --- | ---: | ---: |
| Complete worker-job wall time | 29.949 s | 16.923 s |
| Selected positions per second | 5.643 | 9.986 |
| Generation worker + waited-child CPU | 28.016 s | 30.069 s |
| Sampled summed process-tree RSS | 650.9 MiB | 1,210.1 MiB |

Paired throughput ratios are **1.815x, 1.765x and 1.770x**: all pass the declared
1.3x advancement gate. The median gain is 77%, with about 44% less elapsed time.
Generation CPU rises about 7%; parallelism spends more simultaneous resources.

The primary wall interval includes worker startup, generation and each worker's
independent replay/label/SQLite verification. A separate post-timing combined audit
maps local row IDs to portable source/position identities. Every schedule matches
the full serial workload: **16 games, 1,402 plies, 169 selections, 545 retained
analysis records** including actor evidence and supervision. This does not claim
that all 545 records are selected training labels.

RSS is sampled with `ps` at roughly 100 ms and sums coordinator, workers and teacher
descendants. It can double-count shared pages and miss brief peaks; it is not unique
physical memory. Sampling also costs CPU. Total waited process-tree CPU, including
sampling/provenance processes, is separately retained: medians 33.390/33.491 s.
The table's generation CPU excludes coordinator probes by summing worker counters.
These measurements use approved process-table access on macOS.

## Recovery and verification

A separate real-teacher check interrupts one shard after one completed game and
five durable moves in the second. Reopening preserves the completed row and the
interrupted attempt, completes all eight games, and matches the clean shard's
744 plies, 87 selections and 282 analysis records. Another identical execution
reuses all eight games without adding collection rows. This tests the existing
worker recovery contract; no combined scheduler recovery contract is claimed.

The native sanitizer injects failure at every actual allocation on fresh, growing
and repeated-position scalar paths (5, 5 and 4 failure points on this build), checks
unchanged logical state, and retries successfully. It also exercises 128 complete
random games, repetition, terminal precedence and invalid moves under ASan/UBSan.
`make test-native` includes these probes, isolated native sdist/wheel conformance
and ten generation/HTTP integration tests. `make check` passes 824 Python tests
(one optional MPS skip), five frontend tests, lint/docs/API/type checks and both
production builds. Seven focused study tests pass after cleanup, covering worker
limits, concurrent starts, failure/timeout cleanup, source partitions and portable
comparisons.

## Decision and limits

Adopt the native scalar optimization with its existing atomicity and package gates.
The two-worker result supports designing **opt-in production parallel generation**
next, with explicit collection combination and recovery ownership. This authorized
slice stops at the bounded experiment; it introduces no production worker pool.
Per-move durability and Python's default status remain unchanged.

All source/binary manifests and raw executions are retained under
`artifacts/generation-optimization-20260921`; historical profiling evidence is
unchanged. These are timing replications on one machine and fixed source families,
not population samples or a playing-strength result. No CPU affinity/clock control
or local Linux execution was used, and two is not an established optimal worker
count. Future runs should preserve these comparability and recovery checks.
