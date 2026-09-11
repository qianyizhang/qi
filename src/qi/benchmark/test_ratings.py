"""Independent numerical checks and important statistical edge cases."""

import math
from collections import Counter

import pytest

from qi.benchmark.models import RatingMethod
from qi.benchmark.ratings import Observation, fit_ratings, map_fit, objective


def test_gradient_and_hessian_match_finite_differences():
    counts = Counter({("a", "b", True, 1.0): 5, ("a", "b", False, 0.0): 3, ("a", "b", False, 0.5): 7})
    x, prior, index = [0.6, -0.2, 0.8], [0.07, 0.3, 0.25], {"b": 0}
    _, grad, hessian = objective(x, counts, index, prior)
    epsilon = 1e-5
    for i in range(3):
        plus, minus = x[:], x[:]
        plus[i] += epsilon
        minus[i] -= epsilon
        lp, gp, _ = objective(plus, counts, index, prior)
        lm, gm, _ = objective(minus, counts, index, prior)
        assert grad[i] == pytest.approx((lp - lm) / (2 * epsilon), abs=1e-7)
        for j in range(3):
            assert hessian[j][i] == pytest.approx((gp[j] - gm[j]) / (2 * epsilon), abs=1e-7)


def test_draw_aware_fit_recovers_known_decisive_odds_and_color_balance():
    observations = [
        Observation("a", "b", color, result, "family")
        for color in (True, False)
        for result, count in ((1.0, 200), (0.0, 100), (0.5, 150))
        for _ in range(count)
    ]
    ratings, color, _, _ = map_fit(["a", "b"], observations, "b", RatingMethod())
    assert ratings["a"] - ratings["b"] == pytest.approx(400 * math.log10(2), abs=1)
    assert color == pytest.approx(0, abs=1e-6)


def test_finite_regularized_saturation_is_not_presented_as_precise_strength():
    games = [Observation("a", "b", side, 1, str(family)) for family in range(12) for side in (True, False)]
    result = fit_ratings(["a", "b", "disconnected"], games, "b", RatingMethod())
    a, b, disconnected = result.ratings
    assert math.isfinite(a.elo) and a.elo > 1000
    assert a.lower is None and "One-sided" in a.interval_reason
    assert b.elo == 1000 and disconnected.elo is None


def test_empty_and_draw_only_evidence_do_not_fabricate_precision():
    assert all(r.elo is None for r in fit_ratings(["a", "b"], [], "a", RatingMethod()).ratings)
    games = [Observation("a", "b", side, 0.5, str(family)) for family in range(10) for side in (True, False)]
    result = fit_ratings(["a", "b"], games, "a", RatingMethod())
    assert all(r.elo == pytest.approx(1000) and r.lower is None for r in result.ratings)


def test_family_bootstrap_preserves_pairs_and_is_invariant_to_input_order(monkeypatch):
    from qi.benchmark import ratings

    original = ratings.map_fit
    games = [
        Observation("a", "b", side, (family % 3) / 2, str(family)) for family in range(15) for side in (True, False)
    ]
    observed = []

    def checked(ids, sample, anchor, method):
        for family in {o.family for o in sample}:
            paired = [o for o in sample if o.family == family]
            assert sum(o.red_a for o in paired) * 2 == len(paired)
        observed.append(len(sample))
        return original(ids, sample, anchor, method)

    monkeypatch.setattr(ratings, "map_fit", checked)
    first = fit_ratings(["b", "a"], games, "a", RatingMethod())
    second = fit_ratings(["a", "b"], list(reversed(games)), "a", RatingMethod())
    assert first == second and len(observed) == 402
    assert first.ratings[1].lower < first.ratings[1].elo < first.ratings[1].upper
