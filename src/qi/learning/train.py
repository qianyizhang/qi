"""Bounded supervised move classification; no value targets or teacher calls."""

import io
import os
from pathlib import Path
from time import perf_counter
from typing import Literal

import torch
from qi_game.core import GameError
from qi_game.reference import Game, legal_moves, restore
from torch import nn

from qi.players.policy.encoding import ACTIONS, action_id, encode
from qi.players.policy.runtime import CheckpointMetadata, LoadedPolicy, load_checkpoint, make_model
from qi.training_data.assembly import TrainingDataset
from qi.training_data.loading import PreparedDataset
from qi.training_data.v1 import Label


def tensors(labels: list[Label], games: list[Game] | None = None) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    if games is None:
        games = [restore(label.analysis.snapshot) for label in labels]
    features = torch.tensor([encode(game) for game in games], dtype=torch.float32)
    mask = torch.zeros((len(games), ACTIONS), dtype=torch.bool)
    for index, game in enumerate(games):
        mask[index, [action_id(move) for move in legal_moves(game.board, game.turn)]] = True
    targets = torch.tensor([action_id(label.analysis.move) for label in labels], dtype=torch.long)
    return features, mask, targets


def measure(policy: LoadedPolicy, labels: list[Label], games: list[Game] | None = None) -> tuple[dict, list[str]]:
    if games is None:
        games = [restore(label.analysis.snapshot) for label in labels]
    predictions, timings = [], []
    for game in games:
        started = perf_counter()
        predictions.append(policy.predict(game))
        timings.append((perf_counter() - started) * 1000)
    features, mask, targets = tensors(labels, games)
    with torch.inference_mode():
        loss = nn.functional.cross_entropy(policy.model(features).masked_fill(~mask, float("-inf")), targets)
    return {
        "positions": len(labels),
        "cross_entropy": float(loss),
        "random_legal_agreement": sum(1 / len(legal_moves(game.board, game.turn)) for game in games) / len(games),
        "agreement": sum(move == label.analysis.move for move, label in zip(predictions, labels, strict=True))
        / len(labels),
        "legal_outputs": sum(
            move in legal_moves(game.board, game.turn) for move, game in zip(predictions, games, strict=True)
        ),
        "mean_inference_ms": sum(timings) / len(timings),
    }, predictions


def validate_device(device: str, threads: int) -> None:
    if device not in {"cpu", "mps"} or not 1 <= threads <= 32:
        raise GameError("invalid_device", "Use cpu or mps and 1-32 CPU threads.")
    if device == "mps" and (
        not torch.backends.mps.is_available() or os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") == "1"
    ):
        raise GameError(
            "mps_unavailable", "MPS requires GPU access with CPU fallback disabled; explicitly select cpu otherwise."
        )


def synchronize(device: str) -> None:
    if device == "mps":
        torch.mps.synchronize()


def train(
    dataset: PreparedDataset,
    checkpoint: Path,
    *,
    seed: int = 7,
    steps: int = 200,
    seconds: float = 60,
    learning_rate: float = 0.01,
    diagnostic_examples: int = 0,
    device: Literal["cpu", "mps"] = "cpu",
    threads: int = 1,
    train_inputs: list[str] | None = None,
) -> dict:
    if not 1 <= steps <= 2000 or not 0 < seconds <= 600 or not 0 < learning_rate <= 0.1 or diagnostic_examples < 0:
        raise GameError("invalid_budget", "Use 1-2000 steps, at most 600 seconds, and learning rate in (0, 0.1].")
    validate_device(device, threads)
    if checkpoint.exists():
        raise GameError("checkpoint_exists", "Choose a new checkpoint path; training never overwrites weights.")
    dataset = type(dataset).model_validate(dataset.model_dump())
    if isinstance(dataset, TrainingDataset):
        dataset.require_complete()
    train_labels = dataset.split_labels("train")
    if train_inputs is not None:
        available = {label.input_sha256: label for label in train_labels}
        if (
            diagnostic_examples
            or not train_inputs
            or len(set(train_inputs)) != len(train_inputs)
            or not set(train_inputs) <= available.keys()
        ):
            raise GameError(
                "invalid_subset", "Select distinct training inputs only; do not combine with diagnostic examples."
            )
        train_labels = [available[key] for key in train_inputs]
    if diagnostic_examples:
        if diagnostic_examples > len(train_labels):
            raise GameError("invalid_budget", "Diagnostic subset exceeds available training labels.")
        train_labels = train_labels[:diagnostic_examples]
    validation_labels = dataset.split_labels("validation")
    # Replay in source order once, then reuse immutable games through reporting/reload.
    # Nested subsets interleave sources; replaying that order repeatedly thrashes caches.
    selected = {label.input_sha256 for label in train_labels + validation_labels}
    games = {
        label.input_sha256: restore(label.analysis.snapshot)
        for label in sorted(dataset.labels, key=lambda label: label.source_id)
        if label.input_sha256 in selected
    }
    train_games = [games[label.input_sha256] for label in train_labels]
    validation_games = [games[label.input_sha256] for label in validation_labels]
    torch.set_num_threads(threads)
    torch.manual_seed(seed)
    features, mask, targets = (tensor.to(device) for tensor in tensors(train_labels, train_games))
    model = make_model().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_fn = nn.CrossEntropyLoss()
    synchronize(device)
    started = perf_counter()
    initial_loss = None
    completed = 0
    for _ in range(steps):
        if perf_counter() - started >= seconds:
            break
        optimizer.zero_grad()
        loss = loss_fn(model(features).masked_fill(~mask, float("-inf")), targets)
        if not torch.isfinite(loss):
            raise GameError("training_failed", "Training loss became nonfinite; no checkpoint emitted.")
        if initial_loss is None:
            initial_loss = float(loss.detach())
        loss.backward()
        optimizer.step()
        completed += 1
    synchronize(device)
    optimization_seconds = perf_counter() - started
    if completed == 0:
        raise GameError("training_timeout", "No optimization step completed before the deadline.")
    model.eval()
    with torch.inference_mode():
        final_loss = float(loss_fn(model(features).masked_fill(~mask, float("-inf")), targets))
    model.to("cpu")
    torch.set_num_threads(1)
    teacher = train_labels[0].analysis
    metadata = CheckpointMetadata(
        dataset_sha256=dataset.digest,
        dataset_manifest_fingerprint=dataset.manifest.fingerprint if isinstance(dataset, TrainingDataset) else None,
        reserved_corpus_sha256=dataset.reserved_corpus.digest,
        teacher_engine_sha256=teacher.engine_sha256,
        teacher_network_sha256=teacher.network_sha256,
        train_inputs=[label.input_sha256 for label in train_labels],
        validation_inputs=[label.input_sha256 for label in validation_labels],
        seed=seed,
        steps=completed,
        learning_rate=learning_rate,
        torch_version=str(torch.__version__),
        training_device=device,
        training_threads=threads,
    )
    policy = LoadedPolicy(model, metadata, "unsaved")
    train_stats, train_predictions = measure(policy, train_labels, train_games)
    validation_stats, validation_predictions = measure(policy, validation_labels, validation_games)
    buffer = io.BytesIO()
    torch.save({"metadata": metadata.model_dump(), "state_dict": model.state_dict()}, buffer)
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    with checkpoint.open("xb") as stream:
        stream.write(buffer.getvalue())
    loaded = load_checkpoint(str(checkpoint.resolve()))
    reloaded_train = [loaded.predict(game) for game in train_games]
    reloaded_validation = [loaded.predict(game) for game in validation_games]
    reload_equal = train_predictions == reloaded_train and validation_predictions == reloaded_validation
    if not reload_equal:
        raise GameError("checkpoint_mismatch", "Reloaded checkpoint predictions differ from trained weights.")
    slice_stats = {}
    if isinstance(dataset, TrainingDataset):
        labels_by_input = {label.input_sha256: label for label in train_labels + validation_labels}
        for name, keys in dataset.slice_inputs().items():
            keys = [key for key in keys if key in labels_by_input]
            slice_stats[name] = (
                measure(loaded, [labels_by_input[key] for key in keys], [games[key] for key in keys])[0]
                if keys
                else {"positions": 0, "agreement": None, "cross_entropy": None}
            )
    return {
        "slices": slice_stats,
        "status": "complete" if completed == steps else "deadline",
        "training_device": device,
        "training_threads": threads,
        "inference_device": "cpu",
        "checkpoint": str(checkpoint.resolve()),
        "checkpoint_sha256": loaded.sha256,
        "metadata": metadata.model_dump(),
        "diagnostic_examples": diagnostic_examples,
        "requested_steps": steps,
        "optimization_budget_seconds": seconds,
        "optimization_seconds": optimization_seconds,
        "completed_steps": completed,
        "initial_loss": initial_loss,
        "final_loss": final_loss,
        "train": train_stats,
        "validation": validation_stats,
        "reload_predictions_equal": reload_equal,
    }
