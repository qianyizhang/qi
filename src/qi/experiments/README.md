---
description: Recall and record experiments across kinds, and execute or inspect bounded search runs.
scope: shared experiment catalog and search evidence
status: experimental
last_update: 2026-09-21
document_class: coordination
---

# Experiments

Experiments configure comparisons and preserve evidence. Players choose moves;
the referee owns legality and outcomes; reports are derived views. This module
provides the [shared catalog and recording](#shared-catalog-and-recording) for
all registered experiment kinds. Its execution runner is local, synchronous and
limited to search comparisons.

## Run and inspect

From the repository root:

```bash
uv run qi experiment preview --plan data/experiments/search-components-v1.json
uv run qi experiment run --plan data/experiments/search-components-v1.json \
  --output artifacts/experiments/search-v1 --seconds 600
uv run qi experiment verify --run artifacts/experiments/search-v1
uv run qi experiment report --run artifacts/experiments/search-v1 \
  --output artifacts/experiments/search-v1/report.html
```

Open the HTML locally: no server, network, or external assets. Filter recipes and
budgets, inspect boards and move diagnostics, and read the plan/provenance. The
report provides a command for tracing the selected saved decision:

```bash
uv run qi experiment inspect --run artifacts/experiments/search-v1 \
  --unit unit-00007 --turn 0 \
  --output artifacts/experiments/search-v1/traces/combined.json
uv run qi experiment report --run artifacts/experiments/search-v1 \
  --output artifacts/experiments/search-v1/report.html
```

Runs and traces require fresh paths; reports may be regenerated. There is no
resume, scheduling, database, or publication. A deadline is an incomplete result;
errors/interrupts save available evidence and produce a nonzero CLI exit.

## Present authored research reports

`qi experiment present` builds a single offline HTML file from an existing
Markdown report. It retains the full narrative, adds section navigation and
embedded evidence previews, and supports print/save PDF. Use it for previous
reports without preparing chart data:

```bash
npm run build --prefix web
uv run qi experiment present \
  --owner records/reports/2026-09-09-teacher-generation-advisory.md \
  --output artifacts/reports/teacher-generation-advisory.html
```

For a report with comparisons, pass a presentation specification. The
[architecture example](../../../data/experiments/learning/architecture-surfaces-v1/report-view.json)
adds authored takeaways and two interactive tables to the
[source report](../../../records/reports/2026-09-12-architecture-surfaces.md):

```bash
uv run qi experiment present \
  --owner records/reports/2026-09-12-architecture-surfaces.md \
  --view data/experiments/learning/architecture-surfaces-v1/report-view.json \
  --output artifacts/reports/architecture-surfaces-v1.html
```

For the next report, write Markdown with an H1 title and H2 sections. Frontmatter
`description`, `last_update` and `report_outcome` supply the masthead; ordinary
Markdown also works. An optional view uses `version: "research-view-v1"` and:

| Field | Purpose |
| --- | --- |
| `summary`, `takeaways` | Authored reading guidance; never inferred from the largest metric |
| `data_sources` | Named repository-relative JSON paths with exact SHA-256 identities |
| `stats` | Label, value reference (`source` + JSON `pointer`), display format and context |
| `explorers` | Named source, `rows_pointer`, `label_pointer`, optional label mapping, facets and metrics |
| `section_notes` | Explicit presentation annotations keyed by generated section ID; source prose stays intact |

Each explorer metric selects a JSON Pointer, display format (`percent`, `decimal`
or `integer`), unit, explanatory note and optional `denominator_pointer` with
`denominator_unit` (default: positions). `precision` sets decimal places (default
2, up to 6); use enough precision to preserve meaningful measured differences.
Percentages are stored as fractions, so `0.2` displays as `20.00%`. Facets select
recorded rows, such as checkpoint 50 or 200; they do not recompute statistics.
Label-map insertion order controls the display order. Explicit null displays as
unknown, zero remains zero, and absent pointers, non-finite measurements, duplicate
row/facet identities and changed source hashes fail the build. The schema lives
in `research.py` (`ResearchView`); the example contains the complete supported
shape. Prepare or recompute statistics in the experiment's evidence-owning code,
then pin that output in the view.

Inputs resolve against the repository (or `QI_WORKSPACE`). The export embeds
first-level local Markdown, JSON, text and Python references plus raster figures;
each text preview retains its source path and hash. Text is limited to 2 MiB per
file, images to 8 MiB, and attachments to 16 MiB total. Missing, oversized,
unsupported or outside-workspace files have explicit unavailable receipts.
Nested evidence graphs are not recursively bundled. External images become
links, and raw HTML is not executed. The generated HTML can move outside the
checkout and requires no server, fonts, network or additional files to read its
embedded content. JavaScript must be enabled for this viewer.

The CLI prints the source and HTML hashes, section/explorer counts and attachment
availability. Exporting reads only these presentation inputs; it does not run a
teacher, train a model, validate scientific conclusions or change the catalog.
Keep source Markdown, the view specification and pinned measurements in version
control. HTML under `artifacts/` is a regeneratable local projection. Rebuild after
viewer changes. Search-run reports continue to use `qi experiment report --run`.

## Plans and persistence

`model.py` owns schema v1: embedded corpus, recipes, visit budgets, seeds, depth,
rollout length, matchups/openings, and optional immediate-win targets. Targets
must list every legal immediate win, exhaustively checked by the referee.
The first tracked plan embeds a frozen copy of the reserved corpus; a test checks
their agreement. Its 12 positions, 10 recipes, three budgets, and one seed produce
360 probes and 24 paired games. Six midgame prefixes and two immediate-win
positions come from earlier local matches; four original openings are retained.
This is selected engineering coverage, not representative strength evidence.

Future training must use `data/evaluation/search-positions-v1.json` as its reserved
corpus, including all history-prefix board/turn inputs. Older datasets do not
automatically reserve these new positions. This module changes no training data
or weights.

| Run file | Meaning |
| --- | --- |
| `manifest.json` | Immutable plan/digests, player versions, source digest, Git state, Python/package/platform identity, allowance |
| `units/unit-NNNNN.json` | Exact job, recorded turns, final snapshot, status; outcome only for a completed game |
| `status.json` | Observed run state; completion counts are re-derived from units |
| `traces/*.json` | Optional inspected decisions linked by source/unit digests |
| `report.html` | Regeneratable offline projection |

`runner.py` atomically saves each started unit and every decision. The allowance
starts after preflight and is checked before decisions; one bounded search can
finish past it. It is elapsed wall time, not a hard CPU quota. A crashed process
may leave `running` status; the report still shows partial evidence. Incomplete
games never receive an inferred draw. Temporary unfinished writes are ignored.

`evidence.py` replays every turn and checks state, side, seed, version, budgets,
diagnostics, snapshots, and outcomes. It calls the shared
[player validator](../players/validation.py) for legality, common budgets and
optional MCTS/search accounting; search-only inference restrictions stay here.
`report.py` recomputes comparisons from raw
units. Code identity hashes Python/report assets under `src/qi`, plus project and
lock files; Git state is additional context. Hashes identify content, not
authorship or tamper-proof signatures. Replay cannot reproduce measured timing.

## Reading results

- Probe counts show the planned denominator. Partial matrices may sample uneven
  positions: inspect matching positions before inferring a gain. Only the named
  immediate-win targets have best-move ground truth; changed scores are not proof.
- Outcome totals use complete color pairs with identical opening/configurations.
  Missing partners and incomplete games remain outside these totals. There is no
  universal winner ranking, Elo estimate, or general strength claim.
  The shared [evaluation scorer](../../../docs/evaluation.md) adds A's score rate,
  completed/planned pairs, and failed games, including rows with no score yet.
- Latency surrounds untraced `choose`, including validation, excluding file writes.
  Recipes run in fixed order with shared referee caches; these observations are
  not isolated speedup measurements. Equal visits are not equal compute. Depth is ordinary alpha-beta depth, not an
  MCTS metric. Static score breakdowns describe the position before the move.
- Score timelines show one player's side-to-move values at a time. MCTS estimates
  are not calibrated win probabilities. Work columns are not additive: quiescence
  frontiers can overlap MCTS tree/rollout work. Its disjoint accounting remains
  tree visits + rollout steps + extra leaf visits.

## Optional explored-tree recording

`players/trace.py` is an observational, context-local recorder. Small hooks emit
event kinds and parent references from the existing algorithms. There is no
alternate search engine or persistent global trace.

Alpha-beta records iterations, bounds, ordering, pruning, cache use, extensions,
quiescence, and exchange analysis. MCTS records simulation selection/expansion,
rollouts, leaves, backups, and its final retained tree with visits, values, and
unexpanded moves. Repeated visits are separate execution events; the retained
MCTS tree has its own view. Exchange analysis is board-only heuristic work,
not a referee-adjudicated trajectory. Unsearched branches get no invented score.

The default capacity is 100000 events, configurable up to 1000000. Capacity stops
recording only; search remains unchanged. Omitted events make the recording
explicitly incomplete. An interrupted search can have a complete recording of
everything it actually explored. The viewer expands lazily and pages siblings.

Inspection requires a known original source digest and Python/package versions, then
checks the move and every deterministic diagnostic against the saved untraced
choice. Trace timing stays separate. Validation checks parent ordering and all
charged visits; it does not independently prove each heuristic score.
An installed package without checkout sources and the dependency lockfile records
`null` source/Git identity and cannot establish inspection parity.

## Beginner guide and glossary

The offline report includes a reading guide, dotted-underlined term explanations
(hover, keyboard focus, or tap), and a searchable English/Chinese glossary.
Escape or a click outside dismisses help. Raw JSON stays copyable; look up its
field names in Reference. Visits in MCTS node records remain distinct from
charged-work visits.

Definitions and field aliases come from `docs/glossary/ddd.md`, the vocabulary
authority, read from this checkout when generating the report. Add new report
terms there. The embedded glossary records its own digest independently of the
original run's provenance. Regenerating an existing report updates its help
without changing saved experiment evidence or rerunning searches.

## Checks

`make check` covers trace parity/accounting, deadlines, failures, altered evidence,
corpus/plan boundaries, HTML escaping, and existing player/adaptor behavior.
`npm run test:e2e --prefix web` also checks report controls, board/tree inspection,
and mobile layout using temporary hermetic runs. Those report cases need no
teacher or learning dependency.


## Shared app and report projections

The local app's Experiments page uses the shared catalog for finding studies.
Its Recorded search runs section discovers runs under the configured roots and
provides the same views as the standalone HTML renderer. Run discovery also shows
incomplete, invalid and unsupported entries without loading models.
See [interface configuration](../../../docs/interface.md#experiment-readers-and-trace-jobs)
for `QI_EXPERIMENT_ROOTS`, job storage and server deadlines.

`presentation.py` owns version-1 ReportData/ReportBundle DTOs and recomputes them
from verified raw evidence. The HTTP adapter returns overview metadata, selected
units and paginated trace children separately. `web/src/report.tsx` is the shared
React renderer; `web/src/offline.tsx` provides its in-memory data source for
self-contained HTML. Build both app and report assets with `make web-build` before
using HTML export.

Narrative is an optional UTF-8 `narrative.md` sidecar (up to 1 MiB), authored in
an ordinary editor. It supports Markdown/GFM text, tables and links; active HTML
and executable MDX are excluded from rendered views. Local references must name
JSON or Markdown evidence files inside the same run; unsupported references are
reported explicitly. Images are represented as references, not fetched content.
Narrative/glossary/presentation identity is separate from raw evidence identity.
Presentation identity also includes validated traces, so refreshing changed
recordings invalidates cached event views without changing benchmark identity.
Editing commentary cannot change raw unit hashes or recomputed statistics.

The existing report command accepts either `.html` or `.md` output. Markdown
contains authored narrative, static comparison tables, counts, provenance and
links to unit evidence; it references interactive-only sections. Keep Markdown
beside its run to preserve relative evidence links. Exports cannot overwrite raw
JSON, narrative, source, units or traces. Native and HTML filters preserve nulls,
partial counts, paired denominators and the original untraced timing.

Explicit UI trace jobs reproduce one saved decision under the original source,
Python and package identity. They survive browser navigation and closure, but
never server restart. Cancel, failure and timeout publish no trace; capacity
limits may produce a parity-validated recording marked incomplete. Valid traces
remain readable even when trace generation is incompatible. Invalid traces are
reported separately from valid base evidence. Refresh evidence after a job to
include its new trace in native views and subsequent exports. Benchmark units and
untraced timings remain unchanged.

## Opt-in cost profiling

[`qi.profiling`](../profiling.py) provides nested wall spans, interval wall/CPU
accounting, POSIX resource counters and optional cProfile export:

```python
from pathlib import Path
from qi.profiling import Measurement

with Measurement(functions=True) as measurement:
    with measurement.timings.span("work"):
        run_workload()
result = measurement.result
measurement.export_functions(Path("artifacts/new-profile"))
```

Each measurement is single-use and freezes results on exit, including exceptions;
later validation cannot change them. Spans track inclusive and exclusive wall
time on one synchronous call stack. `Timings.wrap(owner, method, label)` temporarily
instruments a callable attribute and restores it on exit; shared class/module
patches require an exclusively owned worker. This is not concurrent task profiling.
Child CPU includes all waited children. RSS values are lifetime maxima for the
worker and children separately, not a combined peak or interval delta.

Use fresh isolated workers and separate unprofiled timings for speed claims.
The [generation study](../../../data/experiments/generation_profile_v1/README.md)
owns its fixed workloads, instrumentation and diagnostic modes; they are not
part of the reusable package API or the search runner.

## Shared catalog and recording

The dashboard `/experiments`, `GET /api/experiment-catalog?q=...` and the CLI read
one catalog from JSON fenced blocks labeled `experiment` in Markdown files directly
under `records/work-items/items/` and `records/reports/`. It covers registered
studies of any supported catalog kind, independently of raw run manifests. Native
search run views still use `QI_EXPERIMENT_ROOTS`; the catalog uses `QI_WORKSPACE`
(default: checkout root). Rebuild the web bundle and restart an older server to
pick up new routes; Refresh catalog rereads owner files thereafter.

```bash
uv run qi experiment search "teacher quality"
uv run qi experiment show teacher-budget-20260909
uv run qi experiment owner records/work-items/items/AB-LEARN-009-teacher-quality.md
uv run qi experiment template my-study "Study title" "Question?" > /tmp/my-study.json
# Fill the scaffold, read the owner, then use its returned owner_sha256:
uv run qi experiment record --owner records/work-items/items/AB-LEARN-009-teacher-quality.md \
  --entry /tmp/my-study.json --expected-sha256 <owner_sha256>
uv run qi experiment check-catalog
uv run qi experiment check-catalog --verify-evidence
```

`template` intentionally emits unfinished fields: fill topics, conditions and
novelty before recording. `show` also returns the current owner hash. To revise,
copy the entry fields (not projection fields owner/owner_sha256/revision/
evidence_locations) into the JSON payload. `record` validates and appends a new
block to the existing owner, requiring its current SHA-256. It preserves prior
bytes; a stale hash fails without writing. Create a normal work item or report
first; the command does not invent an owner or run an experiment.

[`catalog.py`](catalog.py) owns schema version 1. Fields:

| Field | Meaning |
| --- | --- |
| `id`, `title`, `question`, `kind`, `topics` | Stable study identity and discovery terms, including useful aliases. |
| `execution` | `planned`, `running`, `complete`, `incomplete`, `failed`, or `unknown`; work-item completion is separate. |
| `conclusion` | `unassessed`, `supported`, `not-supported`, `mixed`, or `inconclusive`, relative to the stated question and conditions. |
| `finding`, `conditions`, `limitations` | Authored observation with denominators and scope; do not infer it from metrics. |
| `decision`, `revisit` | What follows and what evidence would justify reconsideration. |
| `evidence` | Repository-relative path, role (`report/results/config/data/source/run`), optional SHA-256; raw source manifests retain detailed lineage. |
| `prior_work`, `novelty` | Prior ID, relationship (`extends/reproduces/challenges/uses`) and specific contribution; explain empty prior work rather than asserting novelty without recall. |

Last valid revision in the same owner supplies the current view; old blocks remain
readable in the owner. Duplicate IDs across owners, malformed blocks and unresolved
prior IDs appear as catalog issues and fail `check-catalog`. Register a predecessor
before recording its follow-up. Missing local evidence remains visible and does not
fail portable checks. Optional verification checks supplied hashes of available
files; presence alone is not verification. Evidence paths cannot escape the
workspace. HTTP only previews registered text files up to 4 MiB and owning records
up to 2 MiB, as plain text; other paths remain visible for local inspection.

Search matches all whitespace-separated terms, case-insensitively, across identity,
question, topics, finding, conditions, limits, decision and contribution. It does
not establish scientific comparability or infer synonyms. Keep important aliases
in topics and use several searches plus owner/index fallback from the
[method](../../../docs/experiments.md). The catalog explicitly reports its coverage;
raw artifacts that have never been registered are outside it.
