---
description: Retain PyTorch with explicit Metal training and portable CPU tests and inference.
scope: architecture decision
status: stable
last_update: 2026-09-08
document_class: coordination
---

# ADR-0003: PyTorch with MPS training and CPU verification

- **Status**: accepted
- **Last Update**: 2026-09-08

Keep the pinned PyTorch 2.10 learning implementation. Use explicit `mps` for
local Mac training and `cpu` for portable tests and checkpoint-backed inference.
Keep one trainer; device selection changes execution, not the model or objective.
An unavailable requested GPU fails explicitly. CPU fallback must be selected.

## Evidence and alternatives

On the local M5 Pro (18 CPU cores, 20 GPU cores, 64 GiB), three warm trials of
200 full-batch Adam updates gave these median optimization times:

| Backend | 96 positions | 768 positions |
| --- | ---: | ---: |
| PyTorch 2.10 / MPS | 0.168 s | 0.587 s |
| PyTorch 2.14 / MPS | 0.178 s | 0.579 s |
| MLX 0.32.2 / full float32 | 0.183 s | 0.654 s |
| MLX / compiled, full float32 | 0.141 s | 0.493 s |

Shared initial weights, masks, inputs and Adam settings controlled the comparison.
The larger batch repeated 96 examples; timings excluded startup/compilation and
labeling. PyTorch compilation was not tested. MLX required explicit Adam bias
correction and disabling its default reduced-precision matmul. Initial numerical
checks and CPU prediction transfer passed; PyTorch 2.14 passed 21 focused tests.
Local scripts and raw evidence remain in ignored `artifacts/learning/framework-benchmark/`.

The PyTorch upgrade offered no material gain for this workload. Compiled MLX saved
27–95 ms per fit, insufficient to justify a second framework and checkpoint path.
The user accepted retaining PyTorch after this comparison. Revisit the decision
when model size, batch regime, or measured training cost changes substantially.

## Consequences

Default tests need no GPU. An explicit MPS test lane verifies training and CPU
checkpoint reload. Save training device/thread provenance and actual work;
synchronize GPU timing and retain partial-run status. CPU inference stays pinned
to an explicitly chosen checkpoint. Numerical equivalence across devices is
approximate; exact reload predictions are checked on the CPU deployment path.
See the [trainer contract](../../src/qi/learning/README.md).
