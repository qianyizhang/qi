---
description: Matched production serial/two-worker generation confirmation including publication cost.
scope: bounded generation integration experiment
status: stable
last_update: 2026-09-22
document_class: artifact
---

# Parallel generation confirmation

[AB-DATA-010](../../../records/work-items/items/AB-DATA-010-parallel-generation.md)
predeclares the comparison. The independent canonical audit is adapted without
semantic changes from `generation_optimization_v1/checks.py`; historical evidence
and controllers remain unchanged.

```bash
.venv/bin/python data/experiments/parallel_generation_v1/study.py \
  --config artifacts/generation-optimization-20260921/inputs/teacher.json \
  --output artifacts/parallel-generation-20260922/confirmation-01
```

Requires the locally retained pinned teacher assets and original development
recipe. Each invocation archives current package/application source and dependency
files, plus this controller and audit. Run from the repository root. Three
alternating fresh serial/two-worker CLI pairs include archive/startup, generation
and combined publication. Independent audit follows timing. All six results must
match normalized trajectories, decisions, outcomes, selections and labels; only
elapsed/time/nps and the network's local locator are excluded, as in the prior
study. Attempt and row identities are checked by production integration tests;
random attempt IDs differ between fresh runs.

The external coordinator samples summed coordinator/CLI/worker/teacher RSS at
roughly 100 ms with `ps`. Shared pages can be double-counted and short peaks missed.
Allow process-table access for the measurement; unavailable sampling is not zero
memory use. Each command has a 180-second limit; the comparison stops at 20 minutes
or any failure/mismatch, retaining every log and partial summary. Do not overlap
builds/tests or source edits with timing. Use fresh output directories for retries.
