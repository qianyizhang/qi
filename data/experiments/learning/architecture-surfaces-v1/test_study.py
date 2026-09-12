"""Referee-backed canonical mapping and the study model-specific constraints."""

import pytest
import torch
from models import CASES, PAIR_DIM, Canonical, PairCNN, canonical_features, make_case, pair_scores
from torch import nn

from qi.game import Game, legal_moves
from qi.players.policy.encoding import action_id, encode
from qi.players.policy.runtime import make_model


def positions():
    game = Game()
    yield game
    for index in range(14):
        moves = legal_moves(game.board, game.turn)
        game = game.apply(moves[(index * 11 + 3) % len(moves)])
        yield game


def test_canonical_mapping_matches_referee_and_original_action_support():
    games = list(positions())
    features = torch.tensor([encode(game) for game in games])
    canonical = canonical_features(features)
    assert set(game.turn for game in games) == {"red", "black"}
    assert not canonical[:, -1].any()
    for game, encoded in zip(games, canonical, strict=True):
        relative = Game(board=game.board[::-1].swapcase() if game.turn == "black" else game.board, turn="red")
        assert encoded.tolist() == encode(relative)
        original = {action_id(move) for move in legal_moves(game.board, game.turn)}
        expected = {8099 - move if game.turn == "black" else move for move in original}
        assert expected == {action_id(move) for move in legal_moves(relative.board, relative.turn)}

    class IndexedLogits(nn.Module):
        def forward(self, features):
            return torch.arange(8100, dtype=features.dtype).repeat(len(features), 1)

    scores = Canonical(IndexedLogits())(features)
    for game, logits in zip(games, scores, strict=True):
        expected = torch.arange(8100, dtype=features.dtype)
        assert torch.equal(logits, expected.flip(0) if game.turn == "black" else expected)


@pytest.mark.parametrize("case", CASES)
def test_case_returns_finite_original_logits_and_masked_legal_predictions(case):
    torch.set_num_threads(1)
    games = list(positions())[:4]
    features = torch.tensor([encode(game) for game in games])
    model = make_case(case)
    logits = model(features)
    assert logits.shape == (len(games), 8100)
    assert torch.isfinite(logits).all()
    mask = torch.zeros_like(logits, dtype=torch.bool)
    for i, game in enumerate(games):
        mask[i, [action_id(move) for move in legal_moves(game.board, game.turn)]] = True
    predictions = logits.masked_fill(~mask, -torch.inf).argmax(1)
    assert mask[torch.arange(len(games)), predictions].all()
    logits.masked_fill(~mask, -torch.inf).log_softmax(1)[torch.arange(len(games)), predictions].sum().backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())


def test_baseline_is_exact_production_initialization():
    torch.manual_seed(7)
    baseline = make_case("absolute_mlp64")
    torch.manual_seed(7)
    production = make_model()
    assert baseline.state_dict().keys() == production.state_dict().keys()
    assert all(torch.equal(value, production.state_dict()[key]) for key, value in baseline.state_dict().items())


def test_pair_head_has_bounded_rank_interactions_beyond_additive_bias():
    torch.manual_seed(81)
    embeddings = torch.randn(2, 90, 2 * PAIR_DIM + 2, dtype=torch.float64)
    scores = pair_scores(embeddings).reshape(-1, 90, 90)
    query, key = embeddings[:, :, :PAIR_DIM], embeddings[:, :, PAIR_DIM : 2 * PAIR_DIM]
    explicit = query @ key.transpose(1, 2) / PAIR_DIM**0.5
    explicit += embeddings[:, :, -2:-1] + embeddings[:, :, -1:].transpose(1, 2)
    torch.testing.assert_close(scores, explicit)
    centered = scores - scores.mean(1, keepdim=True) - scores.mean(2, keepdim=True) + scores.mean((1, 2), keepdim=True)
    assert torch.linalg.matrix_rank(centered).tolist() == [PAIR_DIM, PAIR_DIM]


def test_cnn_square_embeddings_cannot_see_beyond_three_squares():
    torch.manual_seed(19)
    cnn = PairCNN()
    original = torch.zeros(1, 14, 10, 9)
    perturbed = original.clone()
    perturbed[0, 0, 0, 0] = 1
    before = cnn.head(cnn.trunk(original))
    after = cnn.head(cnn.trunk(perturbed))
    assert torch.equal(before[:, :, 4:, :], after[:, :, 4:, :])
    assert torch.equal(before[:, :, :, 4:], after[:, :, :, 4:])
    assert not torch.equal(before[:, :, :4, :4], after[:, :, :4, :4])
