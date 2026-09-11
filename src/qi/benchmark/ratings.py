"""Davidson MAP fitting and source-family bootstrap; no player execution."""

import math
import random
from collections import Counter
from dataclasses import dataclass

from qi.benchmark.models import RatingMethod, Record

ELO_UNIT = 400 / math.log(10)


@dataclass(frozen=True)
class Observation:
    a: str
    b: str
    red_a: bool
    result: float
    family: str


class Rating(Record):
    entrant: str
    elo: float | None = None
    lower: float | None = None
    upper: float | None = None
    games: int = 0
    families: int = 0
    interval_reason: str = "No complete pairs connected to the anchor."


class RatingFit(Record):
    method: str = "davidson-map-v1"
    ratings: list[Rating]
    red_advantage_elo: float | None = None
    draw_log_weight: float | None = None
    iterations: int = 0
    bootstrap_successes: int = 0
    bootstrap_failures: int = 0
    interval_kind: str = "95% source-family cluster-bootstrap percentile interval of the regularized estimate"


def connected(ids: list[str], observations: list[Observation], anchor: str) -> list[str]:
    reached = {anchor}
    while True:
        before = len(reached)
        for o in observations:
            if o.a in reached or o.b in reached:
                reached.update((o.a, o.b))
        if len(reached) == before:
            return sorted(set(ids) & reached)


def solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Small dense positive-definite Newton system, with pivoting."""
    rows = [[*r, v] for r, v in zip(matrix, vector, strict=True)]
    size = len(rows)
    for i in range(size):
        pivot = max(range(i, size), key=lambda j: abs(rows[j][i]))
        rows[i], rows[pivot] = rows[pivot], rows[i]
        if abs(rows[i][i]) < 1e-12:
            raise ValueError("Singular rating fit.")
        scale = rows[i][i]
        rows[i] = [x / scale for x in rows[i]]
        for j in range(i + 1, size):
            factor = rows[j][i]
            for k in range(i, size + 1):
                rows[j][k] -= factor * rows[i][k]
    answer = [0.0] * size
    for i in reversed(range(size)):
        answer[i] = rows[i][-1] - sum(rows[i][j] * answer[j] for j in range(i + 1, size))
    return answer


def objective(parameters, counts, index, precision):
    size = len(parameters)
    loss = sum(p * x * x / 2 for p, x in zip(precision, parameters, strict=True))
    grad = [p * x for p, x in zip(precision, parameters, strict=True)]
    hess = [[precision[i] if i == j else 0.0 for j in range(size)] for i in range(size)]
    color, draw = size - 2, size - 1
    for (a, b, red_a, outcome), count in counts.items():
        features = {color: 0.5 if red_a else -0.5}
        if a in index:
            features[index[a]] = 0.5
        if b in index:
            features[index[b]] = -0.5
        difference = sum(parameters[k] * v for k, v in features.items())
        logits = [difference, -difference, parameters[draw]]
        peak = max(logits)
        exps = [math.exp(x - peak) for x in logits]
        total = sum(exps)
        win, lose, tie = [x / total for x in exps]
        observed = 0 if outcome == 1 else 1 if outcome == 0 else 2
        loss += count * (peak + math.log(total) - logits[observed])
        mean = win - lose
        target = 1 if outcome == 1 else -1 if outcome == 0 else 0
        variance = win + lose - mean * mean
        for i, vi in features.items():
            grad[i] += count * vi * (mean - target)
            for j, vj in features.items():
                hess[i][j] += count * vi * vj * variance
            cross = -count * vi * mean * tie
            hess[i][draw] += cross
            hess[draw][i] += cross
        grad[draw] += count * (tie - (outcome == 0.5))
        hess[draw][draw] += count * tie * (1 - tie)
    return loss, grad, hess


def map_fit(ids: list[str], observations: list[Observation], anchor: str, method: RatingMethod):
    index = {id: i for i, id in enumerate(sorted(set(ids) - {anchor}))}
    precision = [1 / (method.strength_prior_sd / ELO_UNIT) ** 2] * len(index)
    precision += [1 / (method.red_prior_sd / ELO_UNIT) ** 2, 1 / method.draw_prior_sd**2]
    counts = Counter((o.a, o.b, o.red_a, o.result) for o in observations)
    parameters = [0.0] * len(precision)
    for iteration in range(100):
        loss, grad, hess = objective(parameters, counts, index, precision)
        if max(abs(g) for g in grad) < 1e-7:
            ratings = {anchor: float(method.anchor_elo)}
            ratings.update({id: method.anchor_elo + ELO_UNIT * parameters[i] for id, i in index.items()})
            return ratings, parameters[-2] * ELO_UNIT, parameters[-1], iteration
        step = solve(hess, grad)
        scale = 1.0
        for _ in range(30):
            trial = [x - scale * d for x, d in zip(parameters, step, strict=True)]
            if objective(trial, counts, index, precision)[0] <= loss - 1e-4 * scale * sum(
                g * d for g, d in zip(grad, step, strict=True)
            ):
                parameters = trial
                break
            scale *= 0.5
        else:
            raise ValueError("Rating optimizer line search did not converge.")
    raise ValueError("Rating optimizer did not converge.")


def quantile(values: list[float], fraction: float) -> float:
    values = sorted(values)
    pos = (len(values) - 1) * fraction
    left = int(pos)
    right = min(left + 1, len(values) - 1)
    return values[left] + (pos - left) * (values[right] - values[left])


def fit_ratings(ids: list[str], observations: list[Observation], anchor: str, method: RatingMethod) -> RatingFit:
    ids = sorted(ids)
    if len(set(ids)) != len(ids) or anchor not in ids:
        raise ValueError("Ratings need unique entrants and a known anchor.")
    for o in observations:
        if o.a not in ids or o.b not in ids or o.a == o.b or o.result not in (0, 0.5, 1):
            raise ValueError("Invalid rating observation.")
    included = connected(ids, observations, anchor)
    observations = sorted(
        [o for o in observations if o.a in included and o.b in included],
        key=lambda o: (o.family, o.a, o.b, o.red_a, o.result),
    )
    result = RatingFit(ratings=[Rating(entrant=id) for id in ids])
    if not observations:
        return result
    point, color, draw, iterations = map_fit(included, observations, anchor, method)
    result.red_advantage_elo, result.draw_log_weight, result.iterations = color, draw, iterations
    families = sorted({o.family for o in observations})
    groups = {f: [o for o in observations if o.family == f] for f in families}
    samples = {id: [] for id in included}
    if len(families) >= method.minimum_families:
        rng = random.Random(method.bootstrap_seed)
        for _ in range(method.bootstrap_replicates):
            resample = [o for f in rng.choices(families, k=len(families)) for o in groups[f]]
            if connected(included, resample, anchor) != included:
                result.bootstrap_failures += 1
                continue
            try:
                values, _, _, _ = map_fit(included, resample, anchor, method)
            except ValueError:
                result.bootstrap_failures += 1
                continue
            result.bootstrap_successes += 1
            for id in included:
                samples[id].append(values[id])
    for row in result.ratings:
        own = [o for o in observations if row.entrant in (o.a, o.b)]
        row.games, row.families = len(own), len({o.family for o in own})
        if row.entrant not in point or not own:
            continue
        row.elo = point[row.entrant]
        values = {o.result if row.entrant == o.a else 1 - o.result for o in own}
        if row.entrant == anchor:
            row.interval_reason = "Fixed coordinate anchor; 1000 is a convention, not known absolute strength."
        elif row.families < method.minimum_families:
            row.interval_reason = f"Fewer than {method.minimum_families} source families; provisional estimate."
        elif len(values) == 1:
            row.interval_reason = "One-sided or identical outcomes; the prior determines a finite estimate."
        elif result.bootstrap_failures:
            row.interval_reason = "Some bootstrap fits disconnected or failed; interval unavailable."
        else:
            lower, upper = quantile(samples[row.entrant], 0.025), quantile(samples[row.entrant], 0.975)
            if upper - lower < 1e-6:
                row.interval_reason = "Degenerate family bootstrap; uncertainty unavailable."
            else:
                row.lower, row.upper, row.interval_reason = lower, upper, ""
    return result
