---
description: Matched native-step optimization and bounded generation concurrency studies.
scope: AB-ARCH-008 and AB-DATA-009 reproduction
status: experimental
last_update: 2026-09-21
document_class: artifact
---

# Generation optimization comparisons

[Native stepping](../../../records/work-items/items/AB-ARCH-008-atomic-native-step.md)
and [two workers](../../../records/work-items/items/AB-DATA-009-two-worker-generation.md)
own separate predeclared protocols and decisions. This directory contains study
drivers, not a production scheduler. They invoke the existing
[profiling workers](../generation_profile_v1/README.md), which use `qi.profiling`.

Before editing the backend, archive the baseline Git revision and copy its installed
native extension into that tree; retain its SHA-256. Use the same project Python
environment and lock for both runtimes. `freeze` captures the candidate's runtime
sources, lock, worker driver and extension. Comparisons explicitly select and check
each application/referee import root; native identity includes the binary hash.

```bash
.venv/bin/python data/experiments/generation_profile_v1/study.py prepare \
  --output artifacts/my-optimization/inputs
.venv/bin/python data/experiments/generation_optimization_v1/study.py freeze \
  --output artifacts/my-optimization/candidate
.venv/bin/python data/experiments/generation_optimization_v1/study.py native \
  --baseline artifacts/my-optimization/baseline \
  --candidate artifacts/my-optimization/candidate \
  --inputs artifacts/my-optimization/inputs \
  --output artifacts/my-optimization/native
.venv/bin/python data/experiments/generation_optimization_v1/study.py workers \
  --candidate artifacts/my-optimization/candidate \
  --inputs artifacts/my-optimization/inputs \
  --reference artifacts/my-optimization/native/teacher-1-candidate-python/collection.sqlite \
  --output artifacts/my-optimization/workers
```

All output directories must be fresh. Inputs require pinned local teacher assets.
Workers have a 180-second allowance inside each comparison's 20-minute limit.
Failure stops remaining worker process groups and preserves logs/partial evidence.
`native` compares old native, candidate native and candidate Python in three
alternating rounds for controlled generation, teacher generation and identical
actions. The action arm inspects every position, with three repeats per cell.

`workers` splits whole sources alternately into two collections, preserving source
IDs, game indices, seeds and budgets. Each of three alternating pairs schedules
the exact same shards with one or two active Python-reference workers. The primary
wall boundary includes worker startup, generation and each worker's independent
verification. A separate combined audit compares portable identities against the
full serial collection; local SQL IDs and timing metadata are not identities.
Cross-shard training selection, collection merging and general scheduling are
outside this experiment. The fixed workload uses independent training sources.

The coordinator samples `ps` at roughly 100 ms for summed process-tree RSS. On this
Mac, run that comparison with approved process-table access outside the restricted
sandbox. This sum can double-count shared pages and miss short peaks; it is not
unique physical memory. CPU counts include waited worker descendants and small
sampling/provenance subprocesses. Worker results also retain separate worker and
teacher-child counters.

`recovery.py --config SHARD.json --reference CLEAN_SHARD.sqlite --output FRESH_DIR`
injects interruption after one completed game and five durable moves in the next.
It checks retained completed data, interrupted-attempt evidence, reopened execution,
identical completed outputs and no-op reuse. Run it with the same frozen runtime
selected through `study.command`; changing implementation fingerprints changes run
identity. Recovery is verified outside throughput timing.

Checks: `pytest tests/test_generation_optimization.py`, explicit Ruff checks for
this directory, and the package/application gates recorded by the owning items.
Historical results retain their own frozen trees and controller copies; a rerun
on new source is a new measurement.
