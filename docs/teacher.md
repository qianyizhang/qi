---
description: Local UCI teacher contract, pinned Pikafish setup, and validation limits.
scope: external teacher interface
status: stable
last_update: 2026-09-09
document_class: coordination
---

# Local teacher

`src/qi/teacher.py` owns read-only local teacher analysis. `qi teach` accepts a
replay snapshot and explicit engine/network paths. The external process proposes
a move; qi verifies legality. The teacher never replaces referee outcomes or
becomes accessible to baseline evaluation players.
[Training Data](../src/qi/training_data/README.md) owns its use for dataset preparation.

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

`go nodes N depth D` provides engine-native stopping limits. For example,
`go nodes 10000 depth 6` requests at most roughly 10,000 engine nodes and an
ordinary depth of six plies (three move pairs); either limit can stop the search.
It does not request exactly 10,000 nodes or guarantee every branch reaches depth 6.
Reported node counts may exceed the request; these are not qi alpha-beta nodes
or a shared compute measure. The timeout covers process startup and protocol execution (default 10 s,
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

## Search settings and query speed

The [glossary](glossary/ddd.md#learning-track) defines teacher queries, node/depth
limits, hash memory, workers, threads and query throughput. These search concepts
are not exclusive to Pikafish; its UCI options supply the concrete settings here.

| Setting | Effect on work and queries per second |
| :-- | :-- |
| Nodes | Raising the limit permits more search and usually reduces throughput when this limit binds. It may have little effect when depth stops the query first. |
| Depth | Raising depth can expand search work sharply, reducing throughput. The node cap can prevent the requested depth from completing. More search can change labels; it does not certify their correctness. |
| Hash (MiB) | A larger transposition table can save repeated search in longer queries, but costs RAM and initialization/reset work. It need not speed up short queries. With four workers, Hash=16 reserves 64 MiB for tables plus network and other process memory. |
| Workers / Threads | More workers analyze independent positions; more threads cooperate on each position. Both compete for CPU and memory. Tune aggregate throughput at fixed query limits rather than assuming more threads are faster. |
| Persistent process | Reusing the process and loaded network amortizes startup. Reset search state between independent queries when comparing against fresh-process labels. This remains a benchmark prototype in qi. |

Measure successful queries divided by total wall time, including setup and
validation when reporting end-to-end query throughput. Engine nodes per second
omits adapter overhead. Dataset preparation also spends time on trajectories,
sampling, validation and assembly, and can retain fewer examples than queries.
See the [preparation advisory](../src/qi/training_data/README.md#dataset-generation-advisory-non-conclusive)
for non-conclusive generation guidance and the supporting experiments.

## Candidate output and observational limits

A principal variation (PV) is a candidate move followed by an analyzed continuation.
Pikafish's MultiPV option requests several leading variations **and changes search
allocation**; it is not a display-only limit. A complete update has up to K candidate
lines, with further updates as search progresses. At fixed nodes, more candidates
can reduce depth; at fixed depth, they can require substantially more nodes.

Upstream `UCI_ShowWDL` adds three integers per candidate line: win, draw and loss
estimates summing to 1000, from the root side-to-move's perspective. For example,
`wdl 76 913 11` means 7.6% / 91.3% / 1.1% conditional on choosing that line's
first move. This is an engine-calibrated outcome distribution, not a probability
of selecting that move or a validated win rate for qi's student/ruleset.
WDL distributions across different moves do not sum to one.

The current adapter fixes MultiPV=1 and does not parse WDL. Multi-candidate
analysis exists only in local experiment scripts. Those comparisons use complete,
unique candidate sets with exact scores at a common reported depth; an incomplete
final update must not silently mix estimates from different depths.

A normal MultiPV=1 search can establish only bounds for many alternatives and
can discard their scores. The local instrumented prototype captures completed
root returns without additional searches, including their bound and depth and
any older exact-window score. An exact-window score is a search estimate, not a
proof. Bounds at one selective horizon need not bound a deeper search's estimate.
Unknown/stale/bounded evidence cannot supply a precise top-five ranking or a full
WDL distribution. The [pilot report](../records/reports/2026-09-09-teacher-generation-advisory.md)
records what the prototype preserved and what remains untested.

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
