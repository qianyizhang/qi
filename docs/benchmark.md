---
description: Frozen local Elo benchmark conditions, durable matches, rating interpretation and test-pool lifecycle.
scope: playing-strength benchmark contract
status: experimental
last_update: 2026-09-12
document_class: coordination
---

# Local playing-strength benchmark

Implementation is owned by `src/qi/benchmark/`; the referee and shared Player
boundary retain authority. [ADR-0009](adr/0009-local-benchmark-ratings.md) owns
the accepted trade-off. Ratings compare configured entrants under one benchmark,
not human tournament Elo or equal-compute performance.

## Frozen conditions

A Benchmark series fixes a Book, six reference entrants, anchor and Rating method.
A Benchmark spec selects round-robin or candidate-versus-panel scheduling and a
predeclared ordered subset of paired starts. Each entrant freezes its player
version, settings and resource digests. A changed checkpoint or search profile
is a new entrant. Adding a candidate does not change the reference series.

Books contain replayable short human-game prefixes with source-game and family
identity. Source games and related prefixes stay in one split; duplicate board
starts are excluded, while full histories remain available to the referee.
Human source attribution does not certify benchmark representativeness or
absence from a checkpoint's unknown training corpus. Explicit evidence is needed
for a held-out claim. Standard-initial-position pairs are diagnostic and excluded
from the varied-opening rating fit.

## Execution and recovery

Persist the resolved plan before play, then save each game attempt separately.
A single writer lock resolves the output directory before acquisition. Completed
games are replay-validated; an interrupted game restarts from its original start,
and failed/interrupted attempts remain retained. A failed matchup pauses while
independent matchups may continue. No failed attempt is a draw or forfeit.
Only complete color pairs score; completion and reliability counts stay visible.

Resume pins the original entrant versions/resources. Each execution segment
records source/environment provenance, so a repaired runner is visible. Reuse
requires identical series, schedule conditions and entrant identities, validates
raw evidence, records its source digest, and never counts a game slot twice.

Locked-test books are reserved for one frozen spec before play. Progress hides
results until all planned games complete. Explicit reveal retires the book from
confirmatory use and creates its immutable report. Restarting interrupted work
continues the same reservation; a different spec cannot claim that pool. Exposed
pool data may subsequently be used for development with its status retained.

## Rating method: davidson-map-v1

Use a Davidson extension of Bradley–Terry with a fitted draw propensity and Red
advantage. For entrant difference d in log-strength units, Red adjustment c and
draw log-weight t, probabilities are the softmax of `(d/2, -d/2, t)`, where d
includes the color adjustment. One log-strength unit is `400 / ln(10)` Elo.
The frozen alpha-beta anchor is assigned 1000. The origin has no external meaning.

Fit a maximum a posteriori estimate with independent zero-centered Gaussian
priors: non-anchor strength differences have standard deviation 800 Elo, Red
advantage 400 Elo, and draw log-weight 2. Priors are explicit regularization;
finite estimates after all wins/losses do not establish a measured finite gap.
Disconnected entrants receive no rating. Retain raw matchup W/D/L, sample counts,
fit diagnostics and cost measurements alongside ratings.

Resample source families with replacement, retaining all their matchups, starts
and both colors together; refit with the same prior. Use a fixed seed and 200
replicates, and report the 2.5/97.5 percentiles as a 95% cluster-bootstrap interval
of the regularized estimator. These are approximate sampling intervals, not
Bayesian credible intervals or a certified coverage guarantee. Fewer than eight
families, one-sided results, degenerate intervals, or disconnected bootstrap
samples yield an explicit unavailable interval. Bootstrap failure counts remain
visible; thresholds and algorithm belong to the versioned method.

The single draw and color effects are modeling assumptions. Matchup results can
disagree with a scalar ranking; inspect them rather than treating Elo as a full
description of playing style. The protocol never automatically promotes a model.

Method sources: [Davidson (1970)](https://doi.org/10.1080/01621459.1970.10481082),
[Glickman's paired-comparison thesis, section 4.6](https://math.bu.edu/INDIVIDUAL/mg/research/thesis.pdf),
and [BayesElo discussion of opponent and sparse-result uncertainty](https://www.remi-coulom.fr/Bayesian-Elo/).

## Delivery and evidence

CLI builds/imports books, previews and freezes specs, runs/resumes matches, and
validates/summarizes evidence without loading players. Qi Lab displays progress,
dated ratings, intervals, matchup results and costs from the same typed summaries.
The [initial throughput pilot](../data/evaluation/benchmark-pilot-v1.json) exercises
execution and recovery with real Pikafish profiles. It is engineering evidence
and cannot establish strength, optimal sample counts or reference budgets.

## Run a benchmark

Configure an explicit Pikafish binding in `QI_PLAYERS_CONFIG` using the
[player guide](../src/qi/players/README.md#named-player-bindings). Then:

```bash
uv run qi bench template --book data/evaluation/human-openings-v1/development.json \
  --pikafish-binding pikafish-local --starts 16 --output artifacts/bench-spec.json
uv run qi bench preview --spec artifacts/bench-spec.json
uv run qi bench freeze --spec artifacts/bench-spec.json --output artifacts/bench-frozen.json
uv run qi bench run --spec artifacts/bench-frozen.json --output artifacts/benchmarks/reference-v1
uv run qi bench resume --run artifacts/benchmarks/reference-v1
uv run qi bench summarize --run artifacts/benchmarks/reference-v1
```

The template uses six reference entrants with explicit visit/node/depth caps.
These are practical, editable benchmark profiles; native depth and node caps
both apply. In the current player adapter, every Pikafish decision starts a fresh
engine process, so measured latency includes this overhead. No persistent engine
or clock-control behavior is introduced here. The default 16 paired starts plus
one standard-start pair schedules 510 games across 15 matchups.

To add a new checkpoint, write a JSON list of Entrant records (include the
predecessor when desired), then freeze a gauntlet using the same reference run:

```bash
uv run qi bench candidate --baseline artifacts/benchmarks/reference-v1 \
  --entrants artifacts/candidates.json --output artifacts/candidate-spec.json
uv run qi bench run --spec artifacts/candidate-spec.json \
  --reuse artifacts/benchmarks/reference-v1 --output artifacts/benchmarks/candidate-v1
```

A gauntlet retains completed reference-versus-reference slots as supporting
evidence; only candidate-involving games execute. Every selected reference slot
must be available for reuse. Series digests must match; repeated reuse arguments
cannot double-count a game. Candidate label/config changes never rewrite old runs.

For confirmation, pass `--book` with a fresh locked-test book to `qi bench
candidate`. This creates a new series identity, retaining the same entrant
profiles and selected-start count. Run it without `--reuse`: the entire
reference and candidate matrix executes afresh on the locked book. A locked
gauntlet never borrows development outcomes to fill reference slots.

For a milestone, use a fresh locked-test book and freeze all candidates and
conditions before play. After completion, `qi bench summarize --run DIRECTORY
--reveal` reveals results and retires the pool. The local pool registry lives in
`artifacts/benchmark-state` (`QI_BENCHMARK_STATE` overrides it). Preserve this
registry across runs: removing it loses the cross-run exposure guard. Renaming
or subsetting an already exposed book does not give it fresh-test status.

Open `/benchmarks` in Qi Lab. `QI_BENCHMARK_ROOTS` is an OS-path-separated list of
directories containing run folders (default `artifacts/benchmarks`). The API is
read-only and discovers opaque IDs; it never accepts arbitrary filesystem paths.
Current summaries revalidate raw evidence; saved snapshots are dated projections.
New snapshots use a version-2 envelope containing the summary and version-1 frozen
evidence: the manifest and an explicit attempt list for every planned slot, including
empty lists. Full attempt contents preserve running observations that later finish
in place. The reader validates identities, the complete inventory and replayed games,
checks the evidence digest, and recomputes ratings, counts and costs from those exact
inputs. Existing snapshots are never overwritten. [ADR-0011](adr/0011-verifiable-rating-snapshots.md)
owns this historical-input decision.

Each summary reports its verification status and source: live evidence, frozen
evidence or reconstructed evidence. Legacy version-1 snapshots remain unchanged.
They can be verified when the current manifest and attempts reproduce their exact
evidence digest; otherwise the API returns their original projection with an explicit
unverified status and reason. Altered projections with reconstructable inputs and
malformed version-2 evidence are rejected. Verification establishes consistency
with retained inputs, not external authenticity. Every snapshot read still checks
the current locked-test reveal guard and never loads or executes players.
Settings, source attribution, uncertainty reasons and diagnostic results remain
available alongside the rating table. No execution starts from the results page.

## Human-game opening source

The [book source and audit](../data/evaluation/human-openings-v1/README.md) retain
attribution, pinned input receipts, normalization and the deterministic partition.
The supported `qi bench book` command rebuilds partitions from normalized source
records. The source-specific `scripts/import_benchmark_book.py` normalizes CCPD
Chinese notation using legal-move matching; unsupported/ambiguous input is rejected.
