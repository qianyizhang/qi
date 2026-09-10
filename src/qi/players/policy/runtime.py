"""Fixed CPU inference and validated, content-identified checkpoint loading."""

import io
from dataclasses import dataclass
from functools import cache
from hashlib import sha256
from pathlib import Path
from typing import Literal

import torch
from pydantic import BaseModel, ConfigDict, Field
from torch import nn

from qi.game import Game, GameError, legal_moves
from qi.players.policy.encoding import ACTIONS, ARCHITECTURE, ENCODING, INPUTS, action_id, encode


class CheckpointMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    ruleset: Literal["xiangqi-training-v1"] = "xiangqi-training-v1"
    encoding: Literal[ENCODING] = ENCODING
    architecture: Literal[ARCHITECTURE] = ARCHITECTURE
    objective: Literal["legal-masked-teacher-move"] = "legal-masked-teacher-move"
    dataset_sha256: str = Field(min_length=64, max_length=64)
    dataset_manifest_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    reserved_corpus_sha256: str = Field(min_length=64, max_length=64)
    teacher_engine_sha256: str = Field(min_length=64, max_length=64)
    teacher_network_sha256: str = Field(min_length=64, max_length=64)
    train_inputs: list[str] = Field(min_length=1)
    validation_inputs: list[str] = Field(min_length=1)
    seed: int
    steps: int = Field(ge=1)
    learning_rate: float = Field(gt=0)
    torch_version: str
    training_device: Literal["cpu", "mps"] = "cpu"
    training_threads: int = Field(default=1, ge=1, le=32)


def make_model() -> nn.Sequential:
    return nn.Sequential(nn.Linear(INPUTS, 64), nn.ReLU(), nn.Linear(64, ACTIONS))


@dataclass(frozen=True)
class LoadedPolicy:
    model: nn.Module
    metadata: CheckpointMetadata
    sha256: str

    def predict(self, game: Game) -> str:
        if game.outcome:
            raise GameError("game_over", "Cannot infer an action in a terminal position.")
        moves = sorted(legal_moves(game.board, game.turn), key=action_id)
        with torch.inference_mode():
            logits = self.model(torch.tensor([encode(game)], dtype=torch.float32))[0]
            scores = logits[[action_id(move) for move in moves]]
            if not torch.isfinite(scores).all():
                raise GameError("invalid_checkpoint", "Policy produced nonfinite logits.")
            return moves[int(scores.argmax())]


@cache
def load_checkpoint(path: str, expected_sha256: str | None = None) -> LoadedPolicy:
    """Cache verified model bytes; one-argument legacy loads stay process-pinned."""
    try:
        checkpoint_path = Path(path)
        if checkpoint_path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("Checkpoint exceeds the 16 MiB limit.")
        raw = checkpoint_path.read_bytes()
        if expected_sha256 is not None and sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("Checkpoint differs from the pinned content identity.")
        payload = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
        if not isinstance(payload, dict) or set(payload) != {"metadata", "state_dict"}:
            raise ValueError("Expected metadata and state_dict.")
        metadata = CheckpointMetadata.model_validate(payload["metadata"])
        train, validation = set(metadata.train_inputs), set(metadata.validation_inputs)
        if (
            train & validation
            or len(train) != len(metadata.train_inputs)
            or len(validation) != len(metadata.validation_inputs)
        ):
            raise ValueError("Checkpoint input splits overlap or contain duplicates.")
        torch.set_num_threads(1)
        model = make_model()
        state = payload["state_dict"]
        expected = model.state_dict()
        if not isinstance(state, dict) or set(state) != set(expected):
            raise ValueError("Checkpoint weights do not match the architecture.")
        for name, tensor in state.items():
            if (
                not isinstance(tensor, torch.Tensor)
                or tensor.dtype != torch.float32
                or tensor.shape != expected[name].shape
            ):
                raise ValueError("Checkpoint tensor shape or dtype is incompatible.")
            if not torch.isfinite(tensor).all():
                raise ValueError("Checkpoint weights must be finite.")
        model.load_state_dict(state, strict=True)
        model.eval()
        return LoadedPolicy(model, metadata, sha256(raw).hexdigest())
    except Exception as exc:
        # CONTRACT: Checkpoint failures are explicit; never substitute an untrained model.
        raise GameError("invalid_checkpoint", f"Cannot load policy checkpoint: {exc}") from exc
