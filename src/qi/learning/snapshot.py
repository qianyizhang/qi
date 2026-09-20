"""Disk-backed snapshot tensors and bounded full-batch Adam updates."""

import json
import resource
import sys
from collections import defaultdict
from pathlib import Path
from time import perf_counter
from typing import Literal

import numpy as np
import torch
from pydantic import Field
from qi_game.core import GameError
from qi_game.reference import Game, legal_moves
from torch import nn

from qi.artifacts import write_json
from qi.learning.config import ModelSettings, ObjectiveSettings, OptimizerSettings, Settings
from qi.learning.provenance import source_identity
from qi.learning.train import synchronize, validate_device
from qi.players.policy.encoding import ACTIONS, INPUTS, action_id, encode
from qi.players.policy.runtime import CheckpointMetadata, load_checkpoint, make_model
from qi.teacher import digest
from qi.training_data.contracts import fingerprint
from qi.training_data.semantics import material_counts, semantic_tags
from qi.training_data.snapshots import SnapshotReader, verify_snapshot
from qi.training_data.store import Collection


class SnapshotData(Settings):
    snapshot: str


class SnapshotTraining(Settings):
    batching: Literal["snapshot-full-batch-v1"] = "snapshot-full-batch-v1"
    updates: int = Field(default=200, ge=1, le=2000)
    seed: int = Field(default=7, ge=0, lt=2**63)
    chunk_size: int = Field(default=256, ge=1, le=4096)
    precision: Literal["float32"] = "float32"


class SnapshotExecution(Settings):
    device: Literal["cpu", "mps"] = "cpu"
    threads: int = Field(default=1, ge=1, le=32)
    fit_seconds: float = Field(default=600.0, gt=0, le=600)


class SnapshotEvaluation(Settings):
    split: Literal["validation"] = "validation"


class SnapshotConfig(Settings):
    schema_version: Literal["snapshot-training-v1"] = "snapshot-training-v1"
    data: SnapshotData
    model: ModelSettings = Field(default_factory=ModelSettings)
    objective: ObjectiveSettings = Field(default_factory=ObjectiveSettings)
    optimizer: OptimizerSettings = Field(default_factory=OptimizerSettings)
    training: SnapshotTraining = Field(default_factory=SnapshotTraining)
    evaluation: SnapshotEvaluation = Field(default_factory=SnapshotEvaluation)
    execution: SnapshotExecution = Field(default_factory=SnapshotExecution)


def prepare_snapshot(snapshot: Path, output: Path, *, chunk_size=256) -> dict:
    """Verify replay once, then prepare bounded arrays without whole-data tensors."""
    if output.exists():
        raise ValueError("Choose a fresh tensor-cache directory.")
    started = perf_counter()
    verification = verify_snapshot(snapshot)
    reader = SnapshotReader(snapshot)
    output.mkdir(parents=True)
    manifest = {"version": "snapshot-tensors-v1", "status": "preparing", "verification": verification}
    write_json(output / "manifest.json", manifest, indent=2)
    n = reader.manifest["rows"]
    arrays = {
        "features": np.lib.format.open_memmap(output / "features.npy", mode="w+", dtype=np.uint8, shape=(n, INPUTS)),
        "mask": np.lib.format.open_memmap(output / "mask.npy", mode="w+", dtype=np.bool_, shape=(n, ACTIONS)),
        "targets": np.lib.format.open_memmap(output / "targets.npy", mode="w+", dtype=np.int64, shape=(n,)),
    }
    counts = defaultdict(int)
    with (output / "rows.jsonl").open("w") as stream:
        for batch in reader.batches(chunk_size):
            for row in batch.to_pylist():
                i = row["ordinal"]
                game = Game(board=row["board"], turn=row["turn"])
                moves = legal_moves(game.board, game.turn)
                if row["move"] not in moves:
                    raise ValueError("Snapshot target is not legal.")
                arrays["features"][i] = encode(game)
                arrays["mask"][i] = False
                arrays["mask"][i, [action_id(m) for m in moves]] = True
                arrays["targets"][i] = action_id(row["move"])
                row["semantic_tags"] = semantic_tags(game.board, game.turn, row["move"])
                row["material"] = material_counts(game.board)
                stream.write(json.dumps(row, sort_keys=True) + "\n")
                counts[row["split"]] += 1
    for array in arrays.values():
        array.flush()
    with Collection(snapshot / "evidence.sqlite", readonly=True) as evidence:
        spec = json.loads(
            evidence.db.execute(
                "SELECT json(payload) FROM analysis_specs WHERE identity=?", (reader.recipe.analysis_spec,)
            ).fetchone()[0]
        )["supervision"]
    manifest.update(
        status="complete",
        snapshot=str(snapshot.resolve()),
        snapshot_fingerprint=reader.manifest["fingerprint"],
        analysis_spec=reader.recipe.analysis_spec,
        supervision=spec,
        reserved_corpus_sha256=reader.recipe.reserved_corpus.digest,
        counts=dict(counts),
        rows=n,
        elapsed_seconds=perf_counter() - started,
        files={p.name: digest(p) for p in output.iterdir() if p.name != "manifest.json"},
    )
    manifest["fingerprint"] = fingerprint("snapshot-tensors-v1", manifest)
    write_json(output / "manifest.json", manifest, indent=2)
    return manifest


class SnapshotTensors:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.manifest = json.loads((self.path / "manifest.json").read_text())
        values = dict(self.manifest)
        identity = values.pop("fingerprint", None)
        if values.get("status") != "complete" or identity != fingerprint("snapshot-tensors-v1", values):
            raise ValueError("Incomplete or invalid tensor cache.")
        if set(values["files"]) != {"features.npy", "mask.npy", "targets.npy", "rows.jsonl"}:
            raise ValueError("Invalid tensor cache files.")
        for name, expected in values["files"].items():
            if digest(self.path / name) != expected:
                raise ValueError("Tensor cache hash mismatch.")
        self.arrays = {
            key: np.load(self.path / f"{key}.npy", mmap_mode="r", allow_pickle=False)
            for key in ("features", "mask", "targets")
        }
        n = values["rows"]
        expected = {"features": ((n, INPUTS), np.uint8), "mask": ((n, ACTIONS), np.bool_), "targets": ((n,), np.int64)}
        if any(
            self.arrays[k].shape != shape or self.arrays[k].dtype != dtype for k, (shape, dtype) in expected.items()
        ):
            raise ValueError("Unexpected tensor cache dimensions or dtype.")

    def rows(self, split=None):
        with (self.path / "rows.jsonl").open() as stream:
            for line in stream:
                row = json.loads(line)
                if split is None or row["split"] == split:
                    yield row

    def batches(self, split, chunk_size, device="cpu"):
        rows = []
        for row in self.rows(split):
            rows.append(row)
            if len(rows) == chunk_size:
                yield self._batch(rows, device)
                rows = []
        if rows:
            yield self._batch(rows, device)

    def _batch(self, rows, device):
        indices = [r["ordinal"] for r in rows]
        arrays = self.arrays
        return rows, (
            torch.tensor(arrays["features"][indices], dtype=torch.float32, device=device),
            torch.tensor(arrays["mask"][indices], dtype=torch.bool, device=device),
            torch.tensor(arrays["targets"][indices], dtype=torch.long, device=device),
        )


def accumulated_step(model, optimizer, batches, count, *, deadline=None, device="cpu"):
    """One full-dataset mean gradient and one Adam update, including a short last chunk."""
    optimizer.zero_grad(set_to_none=True)
    loss_sum, seen = 0.0, 0
    for _, (features, mask, targets) in batches:
        if deadline is not None and perf_counter() >= deadline:
            optimizer.zero_grad(set_to_none=True)
            return None
        loss = nn.functional.cross_entropy(model(features).masked_fill(~mask, float("-inf")), targets, reduction="sum")
        if not torch.isfinite(loss):
            raise GameError("training_failed", "Nonfinite loss; no update applied.")
        (loss / count).backward()
        loss_sum += float(loss.detach())
        seen += len(targets)
        synchronize(device)
    if seen != count:
        raise ValueError("Training pass count differs from frozen snapshot.")
    if deadline is not None and perf_counter() >= deadline:
        optimizer.zero_grad(set_to_none=True)
        return None
    optimizer.step()
    synchronize(device)
    return loss_sum / count


def evaluate(model, data: SnapshotTensors, output: Path, *, chunk_size=256):
    stats = defaultdict(lambda: {"positions": 0, "correct": 0, "loss_sum": 0.0, "legal_outputs": 0})
    model.eval()
    with output.open("x") as stream, torch.inference_mode():
        for rows, (features, mask, targets) in data.batches(None, chunk_size):
            logits = model(features).masked_fill(~mask, float("-inf"))
            losses = nn.functional.cross_entropy(logits, targets, reduction="none")
            if not torch.isfinite(losses).all():
                raise ValueError("Nonfinite evaluation loss.")
            predictions = logits.argmax(dim=1)
            for row, pred, target, loss, legal in zip(
                rows, predictions.tolist(), targets.tolist(), losses.tolist(), mask, strict=True
            ):
                names = [row["split"], f"bucket:{row['bucket']}", f"{row['split']}:phase:{row['phase']}"]
                names += [f"{row['split']}:tag:{tag}" for tag in row["semantic_tags"]]
                for name in names:
                    s = stats[name]
                    s["positions"] += 1
                    s["correct"] += int(pred == target)
                    s["loss_sum"] += loss
                    s["legal_outputs"] += int(legal[pred])
                stream.write(
                    json.dumps(
                        {
                            "input_hash": row["input_hash"],
                            "split": row["split"],
                            "bucket": row["bucket"],
                            "target": target,
                            "prediction": pred,
                            "loss": loss,
                        }
                    )
                    + "\n"
                )
    for s in stats.values():
        s["agreement"] = s["correct"] / s["positions"]
        s["cross_entropy"] = s["loss_sum"] / s["positions"]
    return dict(stats)


def train_snapshot(data: SnapshotTensors, config: SnapshotConfig, output: Path) -> dict:
    if output.exists():
        raise ValueError("Choose a fresh fit directory.")
    validate_device(config.execution.device, config.execution.threads)
    reader = SnapshotReader(Path(config.data.snapshot))
    if reader.manifest["fingerprint"] != data.manifest["snapshot_fingerprint"]:
        raise ValueError("Tensor cache belongs to a different snapshot.")
    output.mkdir(parents=True)
    write_json(output / "config.json", config.model_dump(), indent=2)
    started = perf_counter()
    deadline = started + config.execution.fit_seconds
    t, e = config.training, config.execution
    before_threads = torch.get_num_threads()
    report = {
        "status": "running",
        "requested_updates": t.updates,
        "completed_updates": 0,
        "protocol": t.batching,
        "tensor_cache_fingerprint": data.manifest["fingerprint"],
        "source": source_identity(),
        "snapshot_fingerprint": reader.manifest["fingerprint"],
    }
    write_json(output / "report.json", report, indent=2)
    try:
        torch.set_num_threads(e.threads)
        torch.manual_seed(t.seed)
        model = make_model().to(e.device)
        optimizer = torch.optim.Adam(model.parameters(), lr=config.optimizer.learning_rate)
        optimization_started = perf_counter()
        for _ in range(t.updates):
            loss = accumulated_step(
                model,
                optimizer,
                data.batches("train", t.chunk_size, e.device),
                data.manifest["counts"]["train"],
                deadline=deadline,
                device=e.device,
            )
            if loss is None:
                break
            report.setdefault("initial_loss", loss)
            report["completed_updates"] += 1
            if report["completed_updates"] % 25 == 0:
                write_json(output / "report.json", report, indent=2)
        report["optimization_seconds"] = perf_counter() - optimization_started
        if not report["completed_updates"]:
            raise GameError("training_timeout", "No complete full-batch update before deadline.")
        model.to("cpu").eval()
        torch.set_num_threads(1)
        stats = evaluate(model, data, output / "predictions.jsonl", chunk_size=t.chunk_size)
        meta = data.manifest
        metadata = CheckpointMetadata(
            dataset_sha256=digest(Path(config.data.snapshot) / "manifest.json"),
            dataset_manifest_fingerprint=meta["snapshot_fingerprint"],
            reserved_corpus_sha256=meta["reserved_corpus_sha256"],
            teacher_engine_sha256=meta["supervision"]["engine_sha256"],
            teacher_network_sha256=meta["supervision"]["network_sha256"],
            train_inputs=[r["input_hash"] for r in data.rows("train")],
            validation_inputs=[r["input_hash"] for r in data.rows("validation")],
            seed=t.seed,
            steps=report["completed_updates"],
            learning_rate=config.optimizer.learning_rate,
            torch_version=str(torch.__version__),
            training_device=e.device,
            training_threads=e.threads,
            training_protocol=t.batching,
            training_chunk_size=t.chunk_size,
        )
        checkpoint = output / "policy.pt"
        with checkpoint.open("xb") as stream:
            torch.save({"metadata": metadata.model_dump(), "state_dict": model.state_dict()}, stream)
        loaded = load_checkpoint(str(checkpoint.resolve()), digest(checkpoint))
        reloaded = evaluate(loaded.model, data, output / "reloaded-predictions.jsonl", chunk_size=t.chunk_size)
        if digest(output / "predictions.jsonl") != digest(output / "reloaded-predictions.jsonl") or stats != reloaded:
            raise GameError("checkpoint_mismatch", "Reloaded snapshot predictions or metrics differ.")
        report.update(
            status="complete" if report["completed_updates"] == t.updates else "deadline",
            stats=stats,
            checkpoint_sha256=loaded.sha256,
            reload_predictions_equal=True,
        )
    except (Exception, KeyboardInterrupt) as exc:
        report.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed", error=str(exc))
        raise
    finally:
        torch.set_num_threads(before_threads)
        report["elapsed_seconds"] = perf_counter() - started
        report["process_peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (
            1 if sys.platform == "darwin" else 1024
        )
        report["memory_scope"] = (
            "Process lifetime peak RSS; includes preparation/imports and earlier fits in this process."
        )
        write_json(output / "report.json", report, indent=2)
    return report
