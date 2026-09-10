---
description: Configurable generation policies, incremental SQLite execution and bounded engineering pilots.
scope: training data generation module guide
status: experimental
last_update: 2026-09-11
document_class: coordination
---

# Policy generation

The [runner](../src/qi/training_data/generation_runner.py) implements the accepted generation policies
from [AB-DATA-008](../records/work-items/items/AB-DATA-008-generation-scaling-pilot.md).
It writes directly into the [SQLite collection](../src/qi/training_data/README.md), with separate game
trajectories, selected occurrences and reusable analysis attempts. The generator
never assembles a full in-memory dataset. Its working set is one bounded trajectory
(up to 300 absolute plies), with raw actor answers in a temporary per-game spool.

## Execute a recipe

Install the data extra (`uv sync --extra data`), make the pinned teacher assets
available, then run from the repository root:

```bash
uv run python scripts/run_generation_pilot.py \
  --config data/experiments/learning/generation-policy-engineering-v1.json \
  --output artifacts/learning/my-generation-pilot \
  --preview
```

Remove `--preview` to execute. It checks asset hashes, freezes resolved paths and
configuration, archives executed Python sources and dependency files, and records
an execution journal plus summary. Asset paths resolve relative to the recipe.
Recipes remain small JSON configuration files; samples and analyses live in SQLite.
No engine assets are copied into the source bundle. The command does not schedule
an overnight run. This example's numbers are provisional engineering settings.
Generation can finish with an explicit phase shortfall. Optional `--export-recipe`
adds export and replay checks; its quotas and exclusions must be frozen explicitly.
The original pilot export recipe is retained as failure evidence: it rejected a
shared train/validation observation. The audited export recipe is specific to the
recorded engineering collection, not a generally valid production holdout.

Reuse the identical command with `--resume` to retain completed games. Every
invocation gets a new execution directory. An unfinished game stays as a separate
failed/interrupted attempt and is regenerated from its frozen start; completed
games from the same implementation are reused without teacher calls. A changed
implementation source hash creates a separate logical run in the collection.
This is resume at game boundaries, not
restoration of a live engine search or partially labeled game's temporary spool.
Changing the frozen config, export recipe or collection path requires a new output
folder. Each resumed invocation has the same configured time allowance, recorded
as a separate execution; it does not extend an existing invocation invisibly.

## Independent policies

`PolicyGenerationConfig` contains the embedded reserved corpus, named pinned
teachers, `actor_teacher`, one or more `supervision` names, audit stride, seed,
wall-time allowance and source list. Each source declares its split, number of
games, starting snapshot/family, additional plies, actor and sampler.

- `plausible`: request `candidate_count` MultiPV roots; choose uniformly among
  candidates within `max_cp_gap` engine-native centipawn units. Only compatible
  exact cp scores at a common depth qualify. Mate, missing/incomplete candidates
  and incompatible support produce a named best-move fallback. Malformed evidence
  and illegal actions stop the run. These scores are teacher preferences.
- `intervention`: teacher-best play with one seeded eligible absolute ply and one
  uniformly sampled non-best legal move, followed by teacher-best continuation.
  It records whether the intervention actually occurred. Early termination or
  no alternative at the chosen ply can leave it unapplied; it is never silently
  moved elsewhere. An intervention is not proof of a serious mistake.
- `random`: uniformly choose a legal move without actor queries; independently
  budgeted teachers still label the selected states.

Actor, intervention and sampler RNG streams are separated per source/game.
Changing requested game count or sampling quotas does not change earlier actor
trajectories. Exact engine reproduction still depends on the frozen engine,
settings and execution environment. Continuation length is independent of retained
sample count. `ply` is the exact number of half-moves in the replay prefix; repeated
boards can occur at different plies. Computed game phase is a separate property.

The sampler takes phase quotas, an absolute ply window and minimum spacing. It
uses seeded greedy selection with spacing across phases, excludes reserved inputs,
and deduplicates board-and-turn observations within that trajectory. A greedy
shortfall is not a proof that no alternative selection could fill the quota.
Every result records requested/available/selected/shortfall counts and excluded/
duplicate counts. It never redistributes an unfilled quota to another phase.
Across-game duplicates remain evidence in the collection; snapshot selection
performs global deduplication and enforces split isolation.

## Replay-backed children

Use `CollectionIO.generated_start(game_id, ply)` to obtain a `StartingPosition`
and portable parent trajectory digest from a completed game. Freeze these as the
child source's `start` and `parent_trajectory` before generating the child. Set
`--collection` to the parent's collection and use a fresh output folder. The
adapter verifies prefix, completion, family, split and exclusion eligibility.
Parents and children must remain in the same source family and split. External
replay-backed starts can declare their family directly; curated phase/objective
annotations are currently rejected by this runner rather than being ignored.

## Retention, failure and export

Full trajectories, actor settings, decision reasons and aggregate actor work are
stored per game. Full raw actor analyses persist only for selected occurrences,
fixed audit points and failures; the temporary spool disappears after each game.
An occurrence may be both selected and audited; metadata is merged without changing
its board or replay identity. Each selected occurrence can retain several teacher
specifications, including actor MultiPV and separate single-PV supervision.

One explicit retry is allowed for `teacher_timeout` or `teacher_exit`, with a fresh
session. A second transient failure stops the run; all identity, legality and
integrity failures stop immediately. Failed attempts remain queryable. A search
starts only if its full pinned timeout fits the remaining allowance; requested
nodes/depth/timeout are never reduced to fit. Missing reported nodes contribute
zero to reported-node totals; these are not requested-node or FLOP measurements.
The summary separates actual query attempts/successes, reported nodes, measured
actor/label time, completed/reused games and phase shortfalls.

A successful generation can have `status: shortfall` while every planned game is
complete. Snapshot quotas are a separate requirement: export fails and preserves
pending evidence when they are unavailable. Generation export recipes must set
`selected_only: true` and carry the same frozen reserved corpus; otherwise actor
audits could be eligible when their analysis settings match the desired label.
Snapshots use explicit analysis-spec identity, first committed success (or a
pinned override), source/input isolation and immutable Parquet plus replay evidence.
`SnapshotReader.batches()` provides bounded reads. Production optimizer migration
remains [AB-LEARN-010](../records/work-items/items/AB-LEARN-010-snapshot-training-protocol.md).

The [integration tests](../src/qi/training_data/test_generation_runner.py) exercise actual SQLite and
Parquet with hermetic teachers. The [policy tests](../src/qi/training_data/test_generation_policies.py)
exercise candidate evidence and sampler counterexamples. Run:

```bash
uv run --extra data pytest src/qi/training_data/test_generation_policies.py \
  src/qi/training_data/test_generation_runner.py
```

The larger scientific calibration and any overnight size decision remain with
AB-DATA-008; successful unit tests and this tiny pilot do not establish scale
readiness or optimal data-mixture weights.

## Resource-calibrated overnight profile

The latest [operator handoff](../records/reports/session-handoff-overnight-generation-20260911.md)
authorizes the next session to run sequential roughly one-hour batches until the
user stops it or a safety boundary requires a decision. It derives numbered
1,000-game recipes from the profile below and accounts writes across all batches
and resumes. The original 9,000-game file remains frozen calibration evidence;
do not launch it as one monolithic job for that newer request.

The [resource pilot evidence](../data/experiments/learning/history/generation-resource-v1.json)
covers 512 games in seven fresh SQLite collections, including 300-ply trajectories.
The [prepared overnight plan](../data/experiments/learning/generation-resource-v1/overnight-plan-v1.json)
chooses 9,000 games in 100-game blocks: 80% plausible, 10% intervention and 10%
random; every tenth block is validation. Teacher assets remain pinned, actors use
10k nodes, and selected occurrences receive both 10k and 100k supervision.
This is a measured starting configuration, not an optimal sampling policy.

Preview the exact resolved configuration and resource limits:

```bash
uv run python scripts/run_generation_pilot.py \
  --config data/experiments/learning/generation-resource-v1/overnight-long-play-v1.json \
  --output artifacts/learning/overnight-long-play-v1 \
  --max-write-gb 150 --max-rss-mb 1500 --min-free-gb 30 \
  --preview
```

The prepared profile has not been launched. Its 10-hour generation cap leaves
planning room within a 12-hour allowance for checks/export. The small-pool linear
scenario is about six hours of generation, 6GB of SQLite files and 118GB of
OS-attributed writes; allow 8–10 hours and 10–20GB for working artifacts. Roughly
60k–100k unique inputs is a conservative planning range, not a guaranteed quota.
Greater duplicate saturation, slower searches or a guard cutoff can reduce yield.

Resource options use decimal GB/MB and are frozen with the invocation. The
runner checks write/RSS limits and free space at startup and game boundaries,
preserves completed games on stop, and records `progress.json` plus final resource
counters per execution. These are sampled guards, not kernel-enforced memory or
write caps; one game's work can cross a threshold before the next check. An
explicit requested counter that is unavailable fails closed. Limits apply per
invocation, including a separately recorded manual resume. These guards do not
change SQLite durability (`WAL`, `synchronous=FULL`) or teacher search budgets.

The pilot did not show runaway I/O growth up to 128 games at a fixed horizon,
but writes were approximately 17–27 times the closed database size. Per-ply
transactions and page/log churn therefore matter when budgeting an overnight run.
Keep OS-attributed writes distinct from disk-space consumption and physical SSD
wear. `benchmark_generation.py` also records SQL trace callback traffic; callbacks
can repeat outer statements for triggers, so they are not physical-I/O counters.

Before training from the overnight collection, freeze the predeclared exclusions
for shared train/validation observations, audit label ambiguity, check quotas and
export a selected-only snapshot. Keep original records and exclusion evidence;
do not tune exclusions using model results. Full-game Elo evaluation has a separate
[methodology owner](../records/work-items/items/AB-EVAL-004-heldout-methodology.md).
