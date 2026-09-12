---
description: Run a bounded local teacher-imitation experiment and interpret its evidence.
scope: supervised policy learning
status: stable
last_update: 2026-09-12
document_class: coordination
---

# Teacher imitation

The trainer updates weights; the [policy player](../players/policy/README.md)
only uses them. This first experiment predicts a teacher's chosen legal move.
[ADR-0003](../../../docs/adr/0003-pytorch-mps-training.md) records the PyTorch/MPS decision.
The accepted [Training Data model](../../../docs/models.md) and
[ADR-0004](../../../docs/adr/0004-training-data-bounded-context.md) describe the
implemented extraction and composition boundary; see the
[Training Data guide](../training_data/README.md) for new mixture commands. The
v1 dataset commands below retain their existing generator and artifact format.
There is no value head, engine-score regression, self-play improvement loop,
PUCT, or GPU requirement.

Choose the entry point for the retained input:

| Input | Command | Contract |
| --- | --- | --- |
| Prepared JSON dataset | `qi learn run` | [Declarative experiments](#declarative-experiments) |
| Frozen Parquet snapshot | `qi learn snapshot` | [Bounded snapshot training](#bounded-snapshot-training) |
| Synthetic reference fixture | `qi learn reference` | [Reference reproduction](#reference-reproduction) |

## Declarative experiments

Use `qi learn run --config <recipe.json> --preview` before a single fit or comparison.
Execution adds `--output <fresh-directory>`; scientific settings cannot be
overridden on this command line. This runner consumes prepared JSON datasets.
The flag-based `qi learn train` and `qi learn experiment` commands were removed
under [AB-LEARN-011](../../../records/work-items/items/AB-LEARN-011-curve-adapter-retirement.md).
Migrate single fits with `data.selection: "source-order"`; use `data.train_size`
for a diagnostic subset. Curves use `source-interleaved` (the Recipe default).
Existing datasets, checkpoints, historical reports and copied trial configs remain readable.

Recipes use seven sections, validated in `config.py`:

| Section | Current settings |
| --- | --- |
| `data` | Prepared dataset path, training size, source-order or source-interleaved selection, subset seed |
| `model` | Existing architecture and encoding identifiers; unsupported alternatives fail |
| `objective` | Existing legal-masked teacher-move objective |
| `optimizer` | Adam and learning rate |
| `training` | Full-batch updates, initialization seed, float32 |
| `evaluation` | Dataset validation split; agreement and cross-entropy |
| `execution` | CPU/MPS, threads, per-fit and total elapsed allowances |

Omitted settings resolve to schema-v1 defaults. Saved configs include all seven
sections and all declared settings. Library implementation details remain governed
by code and the dependency lock; this is not a dump of every PyTorch parameter.
Dataset generation, split construction and teacher labeling happen before this
runner. The dataset's embedded reserved corpus is authoritative; its digest is saved
in the manifest and checkpoint. There is no separate corpus option or expected-corpus
field. Existing dataset validation, including leakage checks, remains in force.
Use the separate `qi data prepare --config` command for
[configured preparation](../training_data/README.md#commands-and-partial-work),
then set `data.dataset` to its frozen output. Training configs do not trigger generation.
Config mode accepts the original v1 dataset, explicit historical selections, or
a complete frozen Training Data dataset. Incomplete mixtures fail before execution;
per-slice diagnostics from the shared trainer remain in each trial report.

A recipe optionally adds named `cases` and a `seeds` list:

```json
{
  "schema_version": 1,
  "name": "data-size",
  "data": {"dataset": "dataset.json"},
  "cases": [
    {"name": "small", "overrides": {"data": {"train_size": 96}}},
    {"name": "larger", "overrides": {"data": {"train_size": 192}}}
  ],
  "seeds": [7, 17, 27]
}
```

Cases apply one level of section-field overrides, then run in listed case/seed
order. Case names must be distinct ignoring capitalization, including on macOS.
A missing case list means one case; a missing seed list uses the base
training seed. Dataset, total allowance and initialization seed cannot be
overridden inside a case. Use the shared dataset/allowance and `seeds` instead.
Up to 16 cases and eight distinct seeds are supported. This initial comparison
shape is provisional. It does not automatically certify comparability or perform
adaptive selection. No checkpoint is selected by validation.

Paths resolve relative to the config file, not the shell working directory.
`runs.py` preserves `dataset.json`, a fully resolved `config.json`, `manifest.json`
and `summary.json`. Every new run uses the same Recipe format, including single fits:
the manifest lists concrete trials and exact inputs, and the summary groups `cases`.
There are no legacy `plan`, `curve`, or per-trial `size` aliases; the size is in each
trial config's `data.train_size`. Each started trial saves `<case>-seed-N.config.json`
with concrete training size and the effective fit allowance. A fit that finishes or
reaches its optimization deadline after completing updates also saves
`<case>-seed-N.json` and a CPU checkpoint, `<case>-seed-N.pt`. A failure before that
can leave only the trial config. Pending trials remain in the manifest; failures
retain the active trial name and config.

Atomic `summary.json` updates retain per-trial reports and case aggregates:
train/validation agreement and cross-entropy means and population standard deviations,
plus expected random-legal agreement. Only seed groups in which every fit completes
receive aggregates; deadline-limited fits are excluded from comparison.

The total elapsed deadline is checked between trials; each fit receives at most
the remaining allowance for its optimization loop. Setup, reporting, saving and a
bounded step can overrun that allowance. Failed or interrupted runs retain prior
trials; the CLI exits nonzero for incomplete runs. There is no resume or overwrite.
Abrupt process termination can leave a `running` summary and an orphan checkpoint;
use a fresh run path rather than inferring completion.

Copy either the whole saved recipe or a single trial config, edit a parameter,
and pass the copy to the same command. Saved configs carry `origin_config`; the
new run records that origin as `derived_from` automatically. Preserve that field
when copying. These are local file links, not additional content fingerprints.
Saved configured runs reference their preserved dataset by absolute local path,
so moving a copied config within this machine does not change its input. Moving
the dataset to another machine requires updating that path. Reusing a config
starts training from its seed; it does not resume checkpoint weights.
Historical single-fit `<checkpoint-filename>.config.json` sidecars remain accepted;
their dataset paths still point to the original files.

Historical settings and limits are in the [experiment index](../../../data/experiments/learning/README.md).
Use the [experiment method](../../../docs/experiments.md) to record expectations,
selection versus confirmation, conclusions and revisit triggers.

For comparable fixed-label experiments with the current small policy and shallow
teacher on early random play, prefer broader source coverage. The
[fresh confirmation](../../../records/work-items/items/AB-LEARN-007-fresh-source-confirmation.md)
supports this working choice; four labels per game is not a general optimum or
a changed generator default. Revisit it when teacher, phase distribution, label
budget or representation changes. The [campaign](../../../records/campaigns/policy-generalization.md)
owns the current evidence synthesis and remaining questions.

## Reference reproduction

After installing the learning extra, run a tiny synthetic experiment without a
teacher, network access, GPU or source checkout:

```bash
qi learn reference --preview
qi learn reference --output reference-run
```

In the checkout, prefix these commands with `uv run --locked --extra learning`.
The output directory must be fresh. The packaged `reference_data/` bundle contains
a frozen Training Data mixture (8 training and 4 validation positions), a resolved
recipe (seed 7, CPU, one thread, 100 updates), and `expected.json`.
Random trajectories have disjoint source games; targets are the lexicographically
first legal move. Teacher-shaped metadata explicitly names a synthetic labeler;
engine/network hashes identify text markers, not real teacher binaries. This proves
workflow behavior, with no move-quality or generalization claim.

The existing runner saves the dataset, configs, manifest, summary, trial report and
CPU checkpoint. The wrapper adds `verification.json` with checks, observed/expected
metrics and runtime provenance. Checks cover input/scientific-config identities
(excluding paths/lineage), completed updates, checkpoint hash/metadata, splits,
legal outputs and prediction-preserving reload. The saved checkpoint is remeasured.
Failure exits nonzero and retains available artifacts; existing runs are preserved.

The baseline is three macOS arm64 CPU runs with PyTorch 2.10.0. All eight training
labels must match, with final loss below one tenth of initial loss. Loss comparisons
allow the larger of 0.01 absolute error and 5% relative error. Validation agreement
allows one position (0.25) away from the baseline 3/4. These are practical allowances:
cross-platform suitability is assumed, not calibrated. Weights and timings need not
match across runs. Investigate failures before changing expectations.
[AB-REPRO-001](../../../records/work-items/items/AB-REPRO-001-reference-experiment.md)
records calibration and verification evidence.

Reconstruct the fixture into a fresh file without the learning extra or a teacher:

```bash
uv run --locked python scripts/build_reference_fixture.py --output artifacts/reference-fixture.json
```

The ordinary tests compare the generator with the frozen dataset. This tiny fixture
is an explicit exception to the local-only dataset policy; checkpoints and run
outputs remain ignored.

For a clean distribution check:

```bash
uv run --locked python scripts/check_reference_package.py --output artifacts/reference-package
```

This builds an sdist, builds its wheel, installs locked learning dependencies and
the wheel in a temporary virtual environment, and runs outside the checkout.
Network access is needed only for dependency/build-tool installation. Checkout
provenance must be unavailable (`null`); package/runtime metadata remains recorded.
GitHub Actions runs repository checks and a separate learning/package lane on Linux
with Python 3.12, hard job timeouts, and failure-artifact retention. The installed
package lane uses the same Mac-derived tolerances.

## Run the small experiment

Install the optional learning extra and the [local teacher](../../../docs/teacher.md).
Keep labels and weights local under ignored `artifacts/`; the teacher's license
and network-use conditions still apply. These commands do not publish artifacts.

```bash
uv sync --extra learning
uv run --extra learning qi learn dataset \
  --corpus data/evaluation/search-positions-v1.json \
  --engine artifacts/teachers/pikafish-2026-01-02/MacOS/pikafish-apple-silicon \
  --network artifacts/teachers/pikafish-2026-01-02/pikafish.nnue \
  --output artifacts/learning/smoke-v1.json

cat > artifacts/learning/smoke-fit.json <<'JSON'
{
  "name": "policy",
  "data": {"dataset": "smoke-v1.json", "selection": "source-order"}
}
JSON

uv run --extra learning qi learn run --config artifacts/learning/smoke-fit.json --preview
uv run --extra learning qi learn run --config artifacts/learning/smoke-fit.json \
  --output artifacts/learning/smoke-fit

QI_POLICY_CHECKPOINT=artifacts/learning/smoke-fit/policy-seed-7.pt \
  uv run --extra learning qi evaluate --corpus data/evaluation/search-positions-v1.json \
  --player-a policy --player-b alphabeta --seed 7 \
  > artifacts/learning/policy-vs-alphabeta.json
```

For a tiny overfit, copy this config, add `"train_size": 8` inside `data`, and use a
fresh output directory. The saved trial config and input list record the subset.
Existing run directories and checkpoints are never overwritten. Run summaries are
JSON on stdout; full per-fit reports are saved in the run directory; errors go to stderr.

## Legacy dataset generation (`training_data/v1.py`)

The default generator makes 16 seeded random legal trajectories of up to 32 plies,
assigns four whole source games to validation before sampling, and queries up to
8 positions per game. Each label embeds a replay snapshot and the complete teacher
analysis, including binary/network hashes and query settings. Teacher scores are
retained only as raw provenance, never used as targets.

For new datasets, use the expanded `data/evaluation/search-positions-v1.json`
corpus; older datasets/checkpoints do not automatically exclude its new positions.
The dataset embeds the reserved evaluation corpus. Its opening positions and all
history-prefix inputs are excluded. Deduplication across both splits uses the
exact board-and-turn model input, so transpositions cannot leak through different
full-history state hashes. Loading revalidates source prefixes, legality, identity,
split membership, exclusions, and one consistent teacher/search configuration.
The initial board is consequently never a training label in this corpus.

Defaults request 1000 teacher nodes and depth 3 per query, with a 300-second total
generation deadline. Timeout fails without emitting a dataset. These low-budget
labels from random trajectories are sufficient to exercise the pipeline, not a
representative teaching curriculum. New evaluation corpora must also be excluded
when constructing their training datasets; exclusions describe the embedded corpus.

For a larger data-size study, generation accepts up to 2048 source games and
32768 labels, with an explicit deadline up to 7200 seconds. `--workers 1` remains
the default; `--workers 4` runs at most four independent single-threaded teacher
processes concurrently. Each query still starts a fresh engine with the same
settings. Parallel completion does not change seeded sampling, source splits or
label order. The total deadline also covers queued queries; an error waits for
in-flight queries to finish or reach their own deadlines and emits no dataset.

## Optimization (`train.py`)

The network predicts 8100 logits. Illegal logits are masked before cross-entropy:
loss is minus the log probability assigned to the teacher move among legal moves.
Adam updates weights on the training split only. The fixed final checkpoint is
measured on validation; validation does not select steps or tune parameters.
Each fit validates the dataset, replays selected positions in source-game order,
and reuses those immutable game objects for tensors, scoring and reload checks.
This avoids repeatedly replaying interleaved source histories at larger sizes.

Defaults: seed 7, 200 full-batch steps, learning rate 0.01, CPU, one thread.
The 60-second budget covers the optimization loop, checked between steps; setup,
replay, reporting and serialization are outside it. One bounded step may finish
past the deadline. MPS timing synchronizes completed GPU work at the loop boundaries.
The report records actual steps, elapsed optimization time and `complete`/`deadline` status.
For a diagnostic fit, `data.selection: "source-order"` with `data.train_size: N`
uses only the first N training labels and records their identities.
Set `execution.device` to `mps` for Mac GPU training, or use `cpu` and
`execution.threads: 4` for a threaded CPU fit. MPS must be available and CPU fallback
disabled; selection never silently changes devices. Model/data use float32. Final
weights move to CPU for validation, serialization, and exact reload checks; inference
timings describe CPU play, not GPU training. Checkpoints record training device and
thread count.

A successful tiny overfit proves the loss/gradient path works. Equal predictions
before and after checkpoint reload prove serialization consistency. Held-out
agreement asks whether imitation generalizes to unseen source games. Legal outputs
prove the mask works. Paired-color replayable matches exercise the player boundary;
the small fixed corpus does not establish general strength.

## Data-size experiment

Generate a fresh dataset once, then preview and execute the fixed comparison:

```bash
uv run --extra learning qi learn dataset \
  --corpus data/evaluation/search-positions-v1.json \
  --engine artifacts/teachers/pikafish-2026-01-02/MacOS/pikafish-apple-silicon \
  --network artifacts/teachers/pikafish-2026-01-02/pikafish.nnue \
  --games 64 --samples 16 --plies 32 --seed 7 --nodes 1000 --depth 3 --seconds 600 \
  --output artifacts/learning/generalization-v1-data.json

cat > artifacts/learning/generalization-recipe.json <<'JSON'
{
  "name": "generalization",
  "data": {"dataset": "generalization-v1-data.json", "selection": "source-interleaved", "subset_seed": 7},
  "training": {"updates": 200},
  "execution": {"device": "mps", "fit_seconds": 60, "total_seconds": 600},
  "cases": [
    {"name": "size-96", "overrides": {"data": {"train_size": 96}}},
    {"name": "size-192", "overrides": {"data": {"train_size": 192}}},
    {"name": "size-384", "overrides": {"data": {"train_size": 384}}},
    {"name": "size-768", "overrides": {"data": {"train_size": 768}}}
  ],
  "seeds": [7, 17, 27]
}
JSON

uv run --extra learning qi learn run --config artifacts/learning/generalization-recipe.json --preview
uv run --extra learning qi learn run --config artifacts/learning/generalization-recipe.json \
  --output artifacts/learning/generalization-v1
```

The recipe declares the size/seed matrix and allowances. The model, Adam settings,
teacher and whole-game validation split stay fixed. `data.subset_seed` shuffles
source games and their labels, then interleaves them. Every size takes a prefix of
that training-only order; different initialization seeds receive identical inputs.
Insufficient labels or invalid dataset evidence fail before output is created.
Preview requires no torch import and writes nothing.

The shared [Recipe artifact and deadline semantics](#declarative-experiments) apply.
Exact teacher agreement is an imitation measure, not a move-quality oracle.

## Recorded results

Durable conditions, measurements, limits and decisions remain in the owning
[initial generalization](../../../records/work-items/items/AB-LEARN-002-policy-generalization.md),
[tuning](../../../records/work-items/items/AB-LEARN-003-local-policy-tuning.md) and
[data-scaling](../../../records/work-items/items/AB-LEARN-004-dataset-scaling.md)
records; the [experiment index](../../../data/experiments/learning/README.md)
routes their recipes and retained evidence. The two data-size records support
scaling within their separate measured teacher-imitation setups; the tested tuning
alternatives did not improve the already inspected fresh test. These results do
not establish playing strength or authorize adaptive reuse of that test. The
[policy-generalization campaign](../../../records/campaigns/policy-generalization.md)
owns the current cross-study synthesis and revisit triggers.

## Scale the dataset with the model fixed

```bash
uv run --extra learning qi learn dataset \
  --corpus data/evaluation/search-positions-v1.json \
  --engine artifacts/teachers/pikafish-2026-01-02/MacOS/pikafish-apple-silicon \
  --network artifacts/teachers/pikafish-2026-01-02/pikafish.nnue \
  --output artifacts/learning/scaled-data.json \
  --seed 211 --games 1056 --samples 16 --workers 4 --seconds 7200
```

Copy the preceding recipe to `artifacts/learning/scaled-recipe.json`, set
`data.dataset` to `scaled-data.json`, and declare cases with `data.train_size`
768, 3072 and 12288. Set `execution.fit_seconds` to 600 and `execution.total_seconds`
to 7200, keeping the model, optimizer, initialization seeds and 200 updates fixed.
Preview with `qi learn run --config artifacts/learning/scaled-recipe.json --preview`,
then execute with a fresh `--output artifacts/learning/scaled-curve`.

Recipe accepts sizes through 32768, at most 600 seconds per fit and
7200 seconds for the matrix. Training is still full
batch: every update sees the entire chosen subset, so larger sizes also use more
compute. This measures the benefit of more data with the same number of passes
and optimizer updates, not equal compute. Full-batch tensor memory grows with
dataset size; the supported cap is a bound, not a memory guarantee on every host.
Games can end early and duplicate inputs are removed, so the generator does not
guarantee a requested training count. Preview rejects insufficient data.

## Fixed-input teacher-quality study

`teacher_quality.py` runs the locked [AB-LEARN-009](../../../records/work-items/items/AB-LEARN-009-teacher-quality.md)
comparison. Its study config is separate from a training `Recipe`: it pins parent
dataset bytes, teacher assets, source/position counts, seeds and the total allowance.
Paths resolve from the repository root. Invalid or equivalent PyTorch seeds are
rejected before teacher preparation. The study writes complete per-fit recipes.

```bash
uv run python scripts/run_teacher_quality.py \
  --config data/experiments/learning/teacher-quality-v1.json \
  --output artifacts/learning/teacher-quality-v1
uv run python scripts/run_teacher_quality.py --verify \
  --output artifacts/learning/teacher-quality-v1
```

Use a fresh output directory. Data selection precedes teacher queries and all
reference preparation precedes fitting. Both treatments use identical training
inputs and a separate shared single-PV reference for comparison. Internal dataset
validation scores use each treatment's own labels and are diagnostic only.
All-legal MultiPV/WDL supplies separate common-depth move assessments; missing
support stays unknown. The verifier reloads checkpoints and recomputes reference
metrics and paired summaries without querying a teacher or training again.
Raw answers, source copies, file receipts, failures and planned denominators
remain in the evidence directory. Study completion does not imply an improvement.

Choose exactly one of `--config` (run) or `--verify` (inspect saved evidence).
Verification uses one CPU thread and restores the caller's setting afterward;
progress messages go to stderr and its JSON result goes to stdout. Missing files,
invalid configs and receipt mismatches report concise errors. A failed preflight
with no queries or fits can verify its retained receipts with scope
`preflight-failure-receipts`; this does not certify dataset or checkpoint evidence.

## Checks

`make check` covers encoding and dataset contracts without requiring torch.
`make test-learning` explicitly installs/uses the locked learning extra and runs
hermetic optimization, checkpoint corruption, masking, CLI/HTTP and arena tests.
When the extra is already installed, these integration tests also run in the
ordinary pytest suite. Neither test lane needs an installed teacher.

`make test-learning-mps` explicitly requires Metal access and checks a real GPU
fit plus CPU deployment/reload. Ordinary tests skip that lane.

For two independently selectable checkpoints in Play or paired evaluation, use
[named player bindings](../players/README.md#named-player-bindings). Each binding
pins its own verified model bytes; it does not replace the process-wide
QI_POLICY_CHECKPOINT convenience entry or activate checkpoints discovered among
experiment artifacts.

## Bounded snapshot training

`qi learn snapshot --config snapshot-training.json --output artifacts/fit` uses
the explicit `snapshot-training-v1` seven-section configuration. Set
`data.snapshot` to a frozen directory; `model`, `objective`, `optimizer`,
`training`, `evaluation`, and `execution` retain separate responsibilities.
`--preview` reads the config/manifest without creating output. Existing JSON
`Recipe.data.dataset` interpretation is unchanged.

`snapshot.py` verifies replay and recipe selection, then prepares a hash-pinned
disk-backed cache of uint8 features, boolean masks and int64 targets. Only bounded
chunks become float32 tensors. Evaluation, semantic slices and checkpoint reload
comparison also use bounded batches. Cache and checkpoint metadata retain the
snapshot fingerprint and teacher specification. Per-input predictions are saved.

`training.batching` is `snapshot-full-batch-v1`: sum each chunk's masked
cross-entropy divided by total training count, accumulate all gradients, and
apply one Adam update per complete pass. Defaults are 256-row chunks, fixed
snapshot order, 200 updates, seed 7 and Adam .01. Device and CPU thread count
are explicit. Uneven final chunks retain sample weighting. Float32 reduction
order may differ from whole-tensor training; tests compare losses, gradients
and updates within declared tolerances.

Deadlines are checked between chunks; an incomplete pass contributes no update.
Completed updates can produce a terminal checkpoint and `deadline` report.
Zero completed updates, nonfinite values and unexpected errors retain failure
reports. Evaluation/checkpoint finalization can extend past the optimization
deadline and its full elapsed time is reported. Optimizer-state resume is not
implemented. Preparation time is separate; process peak RSS is a lifetime
high-water mark, not isolated per-fit memory.

[ADR-0010](../../../docs/adr/0010-frozen-selection-and-bounded-full-batch-training.md)
owns the trade-off; [AB-LEARN-010](../../../records/work-items/items/AB-LEARN-010-snapshot-training-protocol.md)
retains build evidence, and [AB-LEARN-012](../../../records/work-items/items/AB-LEARN-012-generated-source-mixing.md)
owns the source comparison. Its bounded runner is `scripts/run_generated_mixing.py`:
pass `--config data/experiments/learning/generated-source-mixing-v1-amended.json`,
a fresh `--output`, and `--stage prepare`, `run`, or `verify` in sequence.

The subsequent frozen semantic and scaling protocols use
`scripts/run_generated_followups.py --config data/experiments/learning/generated-followups-v1.json
--output artifacts/learning/generated-followups-v1 --study semantic|scaling
--stage prepare|run|verify`. Replace each choice with one value. The config pins
the existing candidate pool and plans at that output root; use its exact paths.
Reconstruction starts with `prepare_pool`, `semantic_plans` and `scaling_plans`
in `qi.training_data.followups`, followed by a new explicitly frozen config.

Both natural and enriched semantic cases are freshly fitted. Verification reloads
every checkpoint and checks historical natural-control prediction equality.
Scaling runs 30 unique fits: its six 4k/200-update fits are shared by the fixed-pass
and fixed-presentation views. Its plan uses natural tag frequencies independently
of the semantic result. The two owning work items fix the decision rules and
shared budget; these study scripts do not change general trainer defaults.
For a repaired failed execution, `--attempt study-retry-1` selects a fresh
operational output directory. It does not resume weights or replace the earlier
attempt. Earlier terminal-attempt durations are charged to the original shared
allowance; a nonterminal attempt prevents another writer from starting.
