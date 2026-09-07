---
description: Local UCI teacher contract, pinned Pikafish setup, and validation limits.
scope: external teacher interface
status: stable
last_update: 2026-09-08
document_class: coordination
---

# Local teacher

`src/qi/teacher.py` owns read-only local teacher analysis. `qi teach` accepts a
replay snapshot and explicit engine/network paths. The external process proposes
a move; qi verifies legality. The teacher never replaces referee outcomes or
becomes accessible to baseline evaluation players. No training pipeline is added.

## Pinned local setup

The adopted local smoke target is the official Apple Silicon Pikafish 2026-01-02
release. `data/teachers/pikafish-2026-01-02.json` pins archive, binary, and network
SHA-256 values; the archive digest also matches GitHub release-asset metadata.
The [release](https://github.com/official-pikafish/Pikafish/releases/tag/Pikafish-2026-01-02)
and [source](https://github.com/official-pikafish/Pikafish/tree/Pikafish-2026-01-02)
identify its provenance. Other local engines can use the same adapter if they
support the required UCI options; changing binaries is explicit and recorded.

```bash
curl -fL https://github.com/official-pikafish/Pikafish/releases/download/Pikafish-2026-01-02/Pikafish.2026-01-02.7z -o /tmp/pikafish.7z
uv run python scripts/install_teacher.py --archive /tmp/pikafish.7z
uv run qi new > artifacts/teacher-input.json
uv run qi teach --state artifacts/teacher-input.json \
  --engine artifacts/teachers/pikafish-2026-01-02/MacOS/pikafish-apple-silicon \
  --network artifacts/teachers/pikafish-2026-01-02/pikafish.nnue \
  --nodes 1000 --depth 3 > artifacts/teacher-analysis.json
```

Installation verifies the archive before extracting named files, then verifies
the binary and network. These files and original license texts remain in ignored
local artifacts. No engine executable, weights, or copied source is distributed
with qi. The installer currently targets Apple Silicon macOS; the pipe adapter
uses POSIX selectors and is not a Windows implementation.

## Protocol and records

Following the [upstream UCI contract](https://github.com/official-pikafish/Pikafish/wiki/UCI-%26-Commands),
each analysis launches a fresh process, waits for `uciok`, requires a named engine
and Threads/Hash/MultiPV/Ponder/EvalFile options, sets one thread, 16 MiB hash,
MultiPV 1, no pondering, and an explicit network path. It sends `ucinewgame`, waits
for `readyok`, then sends `position startpos moves ...` with the entire history.
Terminal or unreconstructible qi states are rejected before launch.

`go nodes N depth D` provides engine-native stopping limits. Reported node counts
may exceed the request; these are not qi alpha-beta nodes or a shared compute
measure. The timeout covers process startup and protocol execution (default 10 s,
maximum 120 s), excluding prelaunch file hashing and final process cleanup.
Output is capped at 1 MiB. Processes are killed/reaped on completion or failure.
There is no retry or substitute move. Timeout, crash, unsupported options,
malformed diagnostics, and illegal best moves fail with structured CLI stderr.

Analysis includes snapshot/hash, engine identity, binary/network hashes, effective
settings, requested budget, engine-reported nodes/depth, elapsed time, raw search
info, and a score when reported. Score type is cp or mate, preserves bound flags,
and is explicitly engine-native from the side to move. A best move can be applied
through the normal guarded `qi apply` command. Engine scores and search lines do
not certify qi outcomes; only the returned best move is checked against qi.
Pikafish's repetition/chasing adjudication differs from `xiangqi-training-v1`.

## Licensing and evidence boundary

The upstream engine is GPL-3.0. Its bundled `NNUE-License.md` separately restricts
commercial use of weights without permission. Preserve both upstream texts;
this slice validates personal, local, noncommercial use, matching project scope.
Any redistribution, commercial use, or future training-data publication requires
its own license review. No claim about unrestricted teacher-label rights is made.

Default tests use a small fake executable and require no engine, network, or
service. `scripts/check_teacher.py --engine PATH --network PATH` runs twelve queries
over six replayable states, verifies each best
move with qi, and records engine/network hashes. This is integration evidence,
not a claim of tournament-rule equivalence, label accuracy, or playing strength.
