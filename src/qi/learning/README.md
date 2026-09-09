---
description: Run a bounded local teacher-imitation experiment and interpret its evidence.
scope: supervised policy learning
status: stable
last_update: 2026-09-09
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

## Declarative experiments

Use `qi learn run --config <recipe.json> --preview` before a new comparison.
Execution adds `--output <fresh-directory>`; scientific settings cannot be
overridden on this command line. Existing `train` and `experiment` commands
remain supported and save config artifacts. `qi learn train` accepts both v1
datasets and complete frozen mixtures, and saves `<checkpoint>.report.json` with
its metrics. The duplicate `qi data train` command has been removed.

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
runner. The embedded reserved corpus and existing dataset validation remain in force.
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
adaptive selection. All trial metrics remain available; means/seed standard
deviations require a complete seed group. Additional diagnostic metrics in the
training report remain unchanged.

Paths resolve relative to the config file, not the shell working directory.
`runs.py` preserves `dataset.json`, a fully resolved `config.json`, the existing
style of manifest, and `summary.json`. Each started trial additionally saves
`<case>-seed-N.config.json`, its result JSON and CPU checkpoint. The trial config
records concrete training size and the effective fit allowance after the remaining
total budget is applied. Pending trials remain in the manifest; failures retain
the active trial name and config. Deadline semantics match the existing elapsed
allowances: setup/reporting and a bounded step can overrun them.

Copy either the whole saved recipe or a single trial config, edit a parameter,
and pass the copy to the same command. Saved configs carry `origin_config`; the
new run records that origin as `derived_from` automatically. Preserve that field
when copying. These are local file links, not additional content fingerprints.
Saved configured runs reference their preserved dataset by absolute local path,
so moving a copied config within this machine does not change its input. Moving
the dataset to another machine requires updating that path. Reusing a config
starts training from its seed; it does not resume checkpoint weights.
The legacy single-fit command saves `<checkpoint-filename>.config.json` and references
its original dataset path; the legacy matrix also preserves its dataset copy.

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

uv run --extra learning qi learn train \
  --data artifacts/learning/smoke-v1.json \
  --checkpoint artifacts/learning/diagnostic-v1.pt --diagnostic-examples 8 \
  > artifacts/learning/diagnostic-v1-report.json

uv run --extra learning qi learn train \
  --data artifacts/learning/smoke-v1.json \
  --checkpoint artifacts/learning/policy-v1.pt \
  > artifacts/learning/policy-v1-report.json

QI_POLICY_CHECKPOINT=artifacts/learning/policy-v1.pt \
  uv run --extra learning qi evaluate --corpus data/evaluation/search-positions-v1.json \
  --player-a policy --player-b alphabeta --seed 7 \
  > artifacts/learning/policy-vs-alphabeta.json
```

Use fresh output paths for new experiments. Existing datasets and checkpoints
are never overwritten. Reports are JSON on stdout; errors go to stderr.

## Data boundary (`data.py`)

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
past the deadline. MPS timing synchronizes completed GPU work at the loop boundaries. The report
records actual steps, elapsed optimization time and `complete`/`deadline` status.
The diagnostic option uses only the first N training labels and records that fact.
Pass `--device mps` for Mac GPU training or `--device cpu --threads 4` for a
threaded CPU fit. MPS must be available and CPU fallback disabled; selection never
silently changes devices. Model/data use float32. Final weights move to CPU for
validation, serialization, and exact reload checks; inference timings describe CPU
play, not GPU training. Checkpoints record training device and thread count.

A successful tiny overfit proves the loss/gradient path works. Equal predictions
before and after checkpoint reload prove serialization consistency. Held-out
agreement asks whether imitation generalizes to unseen source games. Legal outputs
prove the mask works. Paired-color replayable matches exercise the player boundary;
the small fixed corpus does not establish general strength.

## Data-size experiment (`experiment.py`)

Generate a fresh dataset once, then preview and execute the fixed comparison:

```bash
uv run --extra learning qi learn dataset \
  --corpus data/evaluation/search-positions-v1.json \
  --engine artifacts/teachers/pikafish-2026-01-02/MacOS/pikafish-apple-silicon \
  --network artifacts/teachers/pikafish-2026-01-02/pikafish.nnue \
  --games 64 --samples 16 --plies 32 --seed 7 --nodes 1000 --depth 3 --seconds 600 \
  --output artifacts/learning/generalization-v1-data.json

uv run --extra learning qi learn experiment \
  --data artifacts/learning/generalization-v1-data.json \
  --corpus data/evaluation/search-positions-v1.json \
  --output artifacts/learning/generalization-v1 --device mps --preview

uv run --extra learning qi learn experiment \
  --data artifacts/learning/generalization-v1-data.json \
  --corpus data/evaluation/search-positions-v1.json \
  --output artifacts/learning/generalization-v1 --device mps \
  > artifacts/learning/generalization-v1-report.json
```

Defaults compare `--sizes 96,192,384,768` using `--seeds 7,17,27`, 200 updates,
60 seconds per fit, and `--total-seconds 600`. The existing model, Adam settings,
teacher and whole-game validation split stay fixed. One `--subset-seed 7` shuffles
source games and their labels, then interleaves them. Every size takes a prefix of
that training-only order; different initialization seeds receive identical inputs.
Insufficient labels or a mismatched reserved-corpus digest fail before output is
created. Preview requires no torch import and writes nothing.

The fresh run directory contains `manifest.json` (configuration, code/data hashes,
exact input order and validation identities), `dataset.json`, each trial's JSON and
CPU checkpoint, and atomic `summary.json` updates. The summary reports train and
validation agreement, cross-entropy, expected random-legal agreement, and mean and
population standard deviation across completed seeds. Only fully completed seed
groups receive comparison metrics; no checkpoint is selected by validation.
Exact teacher agreement is an imitation measure, not a move-quality oracle.

The total elapsed deadline is checked between trials; each fit receives at most
the remaining allowance for its optimization loop. Setup, CPU reporting and saving
can overrun that allowance. A deadline is not a hard process limit. Failed or
interrupted runs retain prior trials; an incomplete fit retains its checkpoint and
actual steps but is excluded from comparison. CLI exits nonzero for incomplete
runs. There is no resume or overwrite. Abrupt process termination can leave a
`running` summary and an orphan checkpoint; use a fresh run path rather than
inferring completion. This is separate from the search-only experiment module.

## Recorded results

[AB-LEARN-002](../../../records/work-items/items/AB-LEARN-002-policy-generalization.md)
records the completed data-size experiment: more examples improved held-out
imitation within its fixed split, with substantial overfitting remaining.
[AB-LEARN-003](../../../records/work-items/items/AB-LEARN-003-local-policy-tuning.md)
records learning-rate, duration, regularization, width and orientation experiments.
Their selected alternatives did not improve fresh-test move agreement, so the
production model and training defaults remain unchanged. That final test has
been inspected and should not be reused for adaptive configuration selection.
[AB-LEARN-004](../../../records/work-items/items/AB-LEARN-004-dataset-scaling.md)
records the larger fixed-policy curve: 768 / 3072 / 12288 training positions
achieved 16.74% / 21.27% / 25.70% teacher agreement on one fresh 4219-position
holdout, averaged over three seeds. Data scaling helped while substantial
overfitting remained; these results do not establish playing strength.

## Scale the dataset with the model fixed

```bash
uv run --extra learning qi learn dataset \
  --corpus data/evaluation/search-positions-v1.json \
  --engine artifacts/teachers/pikafish-2026-01-02/MacOS/pikafish-apple-silicon \
  --network artifacts/teachers/pikafish-2026-01-02/pikafish.nnue \
  --output artifacts/learning/scaled-data.json \
  --seed 211 --games 1056 --samples 16 --workers 4 --seconds 7200

uv run --extra learning qi learn experiment \
  --data artifacts/learning/scaled-data.json \
  --corpus data/evaluation/search-positions-v1.json \
  --output artifacts/learning/scaled-curve \
  --sizes 768,3072,12288 --device mps --fit-seconds 600 --total-seconds 7200
```

The experiment accepts sizes through 32768, at most 600 seconds per fit and
7200 seconds for the matrix; defaults remain unchanged. Training is still full
batch: every update sees the entire chosen subset, so larger sizes also use more
compute. This measures the benefit of more data with the same number of passes
and optimizer updates, not equal compute. Full-batch tensor memory grows with
dataset size; the supported cap is a bound, not a memory guarantee on every host.
Games can end early and duplicate inputs are removed, so the generator does not
guarantee a requested training count. Preview rejects insufficient data.

## Checks

`make check` covers encoding and dataset contracts without requiring torch.
`make test-learning` explicitly installs/uses the locked learning extra and runs
hermetic optimization, checkpoint corruption, masking, CLI/HTTP and arena tests.
When the extra is already installed, these integration tests also run in the
ordinary pytest suite. Neither test lane needs an installed teacher.

`make test-learning-mps` explicitly requires Metal access and checks a real GPU
fit plus CPU deployment/reload. Ordinary tests skip that lane.
