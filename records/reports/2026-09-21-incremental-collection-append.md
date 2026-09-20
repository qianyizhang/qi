---
description: Guarded incremental collection writes improve controlled Python throughput by 1.136x and native throughput by 1.104x without changing durability.
scope: collection append performance and integrity
status: stable
last_update: 2026-09-21
document_class: report
report_outcome: promoted
produced_by: "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-21"
---

# Incremental collection append

Guarded incremental writes achieved **1.136x previous Python throughput and
1.104x previous native throughput**, preserving exact generated outputs. Both
improve in every controlled round and meet the predeclared retention rule. Native
is 1.093x current Python, below the separate 1.2x backend advancement threshold;
Python remains the default and native remains explicitly selected.

[AB-ARCH-007](../work-items/items/AB-ARCH-007-incremental-collection-append.md)
owns the protocol and decision. [Compact results](../../data/evaluation/incremental-append-20260921.json)
retain all 16 comparison cells. Full collections, configs, sources, profiles and
logs remain local under `artifacts/incremental-append-20260921`. This extends
[compact native observations](2026-09-21-compact-native-observations.md) by
addressing repeated collection payload conversion, which affected both backends.

## Implemented behavior

The collection retains one private immutable append state: exact persisted JSONB
bytes, indexed game identity, history and actor counters. Each append rereads
SQLite. Only an exact byte/identity match can reuse validation; other data receives
full schema and identity validation, including normalization of omitted defaults.
Public game reads always validate. Caller mutation cannot alter the cached state.

SQLite appends one move and patches the three counters. The update checks the
observed payload and identity again, along with running status, so a competing
SQL change cannot be overwritten. The cache advances only after commit succeeds.
Same-prefix accounting still works. Invalid counter sums and unsupported snapshot
metadata now fail before writing. Valid payloads, public formats, semantic hashes,
family/split rules, recovery and every-move WAL/FULL commits retain their meaning.

Schema version 1 needs no migration. The cache holds only one game's payload and
prefix; its size still grows with that game's history. JSONB is still read,
copied and written by SQLite. This removes repeated Python conversion from the
warm path; it does not reduce commit frequency or make storage zero-copy.
The [module guide](../../src/qi/training_data/README.md) owns the current behavior.

## Controlled comparison

On the local macOS ARM64/Python 3.12.13 environment, three alternating four-arm
rounds compare the complete archived `c44e08d` runtime against the new runtime.
Both use the same native binary. Fresh serial processes and collections, cleared
reference caches, checked import roots and no concurrent tests/builds isolate
the intended change. Seed 29, 64 random-actor games, the 300-ply cap, phase quotas
and deterministic legal fixture supervision match the previous studies.

All 12 cells match **64 trajectories, 17,169 plies and 417 fixture labels**,
including actor decisions, occurrences and outcomes. The semantic SHA-256 remains
`b6d7618788cdf804327fb003d055ff288927006dfb246a307edd76a083adc519`.
There are 18 checkmates and 46 ply-limit draws; opening/endgame quota shortfalls
remain 52/43. Independent Python replay, occurrence and legal-label checks run
after timing; SQLite integrity and foreign-key checks pass. Fixture supervision
tests equivalence, without establishing teacher quality or playing strength.

| Execution | Median wall time | Plies/s | Selected examples/s |
| --- | ---: | ---: | ---: |
| Previous Python | 2.557 s | 6,715 | 163.1 |
| Previous native | 2.329 s | 7,372 | 179.0 |
| Incremental Python | 2.249 s | 7,633 | 185.4 |
| Incremental native | 2.096 s | 8,192 | 199.0 |

The decision uses the median of within-round throughput ratios. Python gains
are 1.028, 1.256 and 1.136x; native gains are 1.101, 1.141 and 1.104x. Both meet
the retention rule: at least 1.1x median improvement in one backend and no greater
than 5% regression in the other. Current native/Python ratios are 1.149, 1.093
and 1.073x, winning every round but missing the separate 1.2x advancement rule.
These short local windows show timing variation; repeating the same trajectories
does not provide independent workload diversity.

Median append-phase time falls from 1.495 to 1.202 s for Python and from 1.352
to 1.086 s for native. Native referee-phase time is 0.323 versus 0.319 s. Native
still records one initial-position Python legal-move cache miss, versus 17,131
in Python. The gain follows the collection change, not another rules-engine
change. Phase timers cover named blocks and do not exhaust wall time.

## Teacher pilot and remaining costs

Two alternating current Python/native pairs retain four plausible-actor games,
32 plies, pinned Pikafish/NNUE, one thread and 1,000 nodes. All four cells match
128 plies and 20 selections; all games stop at the cap. Median wall time is
0.681 s for Python and 0.673 s for native, with a 1.011x median paired ratio.
This short pilot supports integration parity. It neither measures the incremental
write gain against historical teacher arms nor establishes a general native gain
on expensive teacher workloads. Only existing runtime/provenance fields, answer
elapsed time, UCI `time`/`nps` and the network locator are excluded from semantic
comparison; raw records retain them.

A separate native profile preserves semantic parity. Collection append accounts
for 1.231 s cumulative, append-state lookup for 0.071 s and all public stored-game
reads for 0.082 s. SQLite transaction exits account for 0.732 s. Categories overlap;
these are diagnostic costs, not independent contributions or isolated fsync times.
The inherited profiler has inconsistent scalar native-call counts, so no per-step
native timing conclusion is drawn. Paired unprofiled timings determine the result.
Worker CPU/RSS exclude the teacher child process; peak RSS includes verification.

Retain the collection optimization. Further work should start from a representative
target workload and a new profile; reducing commit frequency would require an
explicit recovery-contract decision. This experiment does not authorize that
change or promote native to the default.

## Evidence and reproduction

The development four-arm parity trial passed before confirmation. No timed
attempt failed. Each comparison retains a 304-file manifest; all frozen hashes
and executed current/baseline source bytes verify. The unchanged native binary is
`b43ae54af624de35e263aede76614c9dd524509786645dcfdce551c7b9d04f8f`.
Historical study scripts, reports and catalog evidence remain unchanged.

Focused store, native-generation, export and training-consumer tests pass all
57 cases. New regressions cover repeated and same-prefix writes, caller mutation,
game switching, valid SQL metadata changes, corrupt payload/identity fields,
missing defaults, large counters, invalid sums, competing writes, failed commit,
retry, finalization and reopening. The deferred-foreign-key test exercises a true
commit failure, beyond statement rejection.

`make check` passes 803 Python tests (one skipped), five browser unit tests,
lint/format, documentation/catalog, OpenAPI/types and the production browser build.
Optional catalog hash verification still reports the pre-existing AB-EVAL-005
digest mismatch for `scripts/import_benchmark_book.py`; this study's evidence
verifies and the unrelated historical discrepancy is unchanged.

Recorded-result reproduction requires the frozen source, lock and binary. The
complete previous runtime is retained at
`artifacts/incremental-append-20260921/baseline-c44e08d`. For a new comparison with
current source and fresh outputs:

```bash
uv sync --locked --extra native
uv run --locked --extra native python scripts/benchmark_incremental_append.py prepare \
  --output artifacts/incremental-append-new/inputs
uv run --locked --extra native python scripts/benchmark_incremental_append.py compare \
  --config artifacts/incremental-append-new/inputs/controlled.json \
  --baseline artifacts/incremental-append-20260921/baseline-c44e08d \
  --output artifacts/incremental-append-new/confirmation --rounds 3
```

Preparation accepts `--teacher-config` with pinned local assets; compare the emitted
`teacher.json` using `--workload teacher --rounds 2`. The standalone worker supports
`--arm native --profile` in a separate output directory. Existing outputs are not
overwritten. Git retains the runner, compact cells, implementation and findings;
full local artifacts are ignored by Git. No native package or binary changed in
this slice, so package isolation and sanitizer evidence remain the prior study's
results rather than newly executed checks.
