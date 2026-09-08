"""Bounded supervised move classification; no value targets or teacher calls."""

import io
from pathlib import Path
from time import perf_counter

import torch
from torch import nn

from qi.game import GameError, legal_moves
from qi.learning.data import Dataset, Label
from qi.players.policy.encoding import ACTIONS, action_id, encode
from qi.players.policy.runtime import CheckpointMetadata, LoadedPolicy, load_checkpoint, make_model


def tensors(labels: list[Label]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    games = [label.analysis.snapshot.game() for label in labels]
    features = torch.tensor([encode(game) for game in games], dtype=torch.float32)
    mask = torch.zeros((len(games), ACTIONS), dtype=torch.bool)
    for index, game in enumerate(games):
        mask[index, [action_id(move) for move in legal_moves(game.board, game.turn)]] = True
    targets = torch.tensor([action_id(label.analysis.move) for label in labels], dtype=torch.long)
    return features, mask, targets


def measure(policy: LoadedPolicy, labels: list[Label]) -> tuple[dict, list[str]]:
    games = [label.analysis.snapshot.game() for label in labels]
    predictions, timings = [], []
    for game in games:
        started = perf_counter()
        predictions.append(policy.predict(game))
        timings.append((perf_counter() - started) * 1000)
    return {
        "positions": len(labels),
        "agreement": sum(move == label.analysis.move for move, label in zip(predictions, labels, strict=True))
        / len(labels),
        "legal_outputs": sum(
            move in legal_moves(game.board, game.turn) for move, game in zip(predictions, games, strict=True)
        ),
        "mean_inference_ms": sum(timings) / len(timings),
    }, predictions


def train(
    dataset: Dataset,
    checkpoint: Path,
    *,
    seed: int = 7,
    steps: int = 200,
    seconds: float = 60,
    learning_rate: float = 0.01,
    diagnostic_examples: int = 0,
) -> dict:
    if not 1 <= steps <= 2000 or not 0 < seconds <= 120 or not 0 < learning_rate <= 0.1 or diagnostic_examples < 0:
        raise GameError("invalid_budget", "Use 1-2000 steps, at most 120 seconds, and learning rate in (0, 0.1].")
    if checkpoint.exists():
        raise GameError("checkpoint_exists", "Choose a new checkpoint path; training never overwrites weights.")
    dataset = Dataset.model_validate(dataset.model_dump())
    train_labels = dataset.split_labels("train")
    if diagnostic_examples:
        if diagnostic_examples > len(train_labels):
            raise GameError("invalid_budget", "Diagnostic subset exceeds available training labels.")
        train_labels = train_labels[:diagnostic_examples]
    validation_labels = dataset.split_labels("validation")
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    features, mask, targets = tensors(train_labels)
    model = make_model()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_fn = nn.CrossEntropyLoss()
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
    optimization_seconds = perf_counter() - started
    if completed == 0:
        raise GameError("training_timeout", "No optimization step completed before the deadline.")
    model.eval()
    with torch.inference_mode():
        final_loss = float(loss_fn(model(features).masked_fill(~mask, float("-inf")), targets))
    teacher = train_labels[0].analysis
    metadata = CheckpointMetadata(
        dataset_sha256=dataset.digest,
        reserved_corpus_sha256=dataset.reserved_corpus.digest,
        teacher_engine_sha256=teacher.engine_sha256,
        teacher_network_sha256=teacher.network_sha256,
        train_inputs=[label.input_sha256 for label in train_labels],
        validation_inputs=[label.input_sha256 for label in validation_labels],
        seed=seed,
        steps=completed,
        learning_rate=learning_rate,
        torch_version=str(torch.__version__),
    )
    policy = LoadedPolicy(model, metadata, "unsaved")
    train_stats, train_predictions = measure(policy, train_labels)
    validation_stats, validation_predictions = measure(policy, validation_labels)
    buffer = io.BytesIO()
    torch.save({"metadata": metadata.model_dump(), "state_dict": model.state_dict()}, buffer)
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    with checkpoint.open("xb") as stream:
        stream.write(buffer.getvalue())
    loaded = load_checkpoint(str(checkpoint.resolve()))
    reloaded_train = [loaded.predict(label.analysis.snapshot.game()) for label in train_labels]
    reloaded_validation = [loaded.predict(label.analysis.snapshot.game()) for label in validation_labels]
    reload_equal = train_predictions == reloaded_train and validation_predictions == reloaded_validation
    if not reload_equal:
        raise GameError("checkpoint_mismatch", "Reloaded checkpoint predictions differ from trained weights.")
    return {
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
