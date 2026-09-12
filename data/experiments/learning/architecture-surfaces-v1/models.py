"""Study-only architectures; every public model accepts/returns the production layout.

Canonicalization turns the mover into red at the bottom of the board. The CNN
has a 7-by-7 per-square receptive field, so it cannot see arbitrary ray blockers.
The external referee mask supplies legality to every case equally.
"""

import math

import torch
from torch import nn

from qi.players.policy.encoding import ACTIONS, INPUTS
from qi.players.policy.runtime import make_model

CASES = (
    "absolute_mlp64",
    "absolute_mlp128",
    "canonical_mlp64",
    "canonical_pair64",
    "canonical_conv32",
)
PAIR_DIM = 16


def canonical_features(features):
    """Return mover-relative one-hot planes plus a constant-zero turn feature."""
    board = features[:, :-1].reshape(-1, 14, 90)
    rotated = torch.cat((board[:, 7:], board[:, :7]), dim=1).flip(dims=(2,))
    canonical = torch.where(features[:, -1:].unsqueeze(-1).bool(), rotated, board)
    return torch.cat((canonical.flatten(1), torch.zeros_like(features[:, -1:])), dim=1)


def pair_scores(embeddings):
    """Shared head algebra for MLP and CNN: bilinear pair interaction plus biases."""
    query, key, source, target = torch.split(embeddings, (PAIR_DIM, PAIR_DIM, 1, 1), dim=-1)
    scores = torch.bmm(query, key.transpose(1, 2)) / math.sqrt(PAIR_DIM)
    return (scores + source + target.transpose(1, 2)).flatten(1)


class Canonical(nn.Module):
    def __init__(self, inner):
        super().__init__()
        self.inner = inner

    def forward(self, features):
        logits = self.inner(canonical_features(features))
        # Rotating both source and target gives action_id -> 8099 - action_id.
        return torch.where(features[:, -1:].bool(), logits.flip(dims=(1,)), logits)


class PairMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.trunk = nn.Sequential(nn.Linear(INPUTS, 64), nn.ReLU())
        self.head = nn.Linear(64, 90 * (2 * PAIR_DIM + 2))

    def forward(self, features):
        return pair_scores(self.head(self.trunk(features)).reshape(-1, 90, 2 * PAIR_DIM + 2))


class PairCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.trunk = nn.Sequential(
            nn.Conv2d(14, 32, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 32, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 32, 3, padding=1),
            nn.ReLU(),
        )
        self.head = nn.Conv2d(32, 2 * PAIR_DIM + 2, 1)

    def forward(self, features):
        board = features[:, :-1].reshape(-1, 14, 10, 9)
        embeddings = self.head(self.trunk(board)).flatten(2).transpose(1, 2)
        return pair_scores(embeddings)


def make_case(name):
    if name == "absolute_mlp64":
        return make_model()
    if name == "absolute_mlp128":
        return nn.Sequential(nn.Linear(INPUTS, 128), nn.ReLU(), nn.Linear(128, ACTIONS))
    if name == "canonical_mlp64":
        return Canonical(make_model())
    if name == "canonical_pair64":
        return Canonical(PairMLP())
    if name == "canonical_conv32":
        return Canonical(PairCNN())
    raise ValueError(f"Unknown study case: {name}")


def model_description(name):
    model = make_case(name)
    return {
        "parameters": sum(p.numel() for p in model.parameters()),
        "canonical": name.startswith("canonical_"),
        "pair_dimension": PAIR_DIM if name in ("canonical_pair64", "canonical_conv32") else None,
        "square_receptive_field": [7, 7] if name == "canonical_conv32" else "global",
        "production_compatible_checkpoint": False,
    }
