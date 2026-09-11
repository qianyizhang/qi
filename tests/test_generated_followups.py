"""Selection controls and decision boundaries for the generated-data follow-ups."""

import json
from collections import Counter

import pytest

from qi.training_data.followups import concentration, replacement_pairs, scaling_plans


def row(key, trajectories, *, tagged=False, policy="plausible", phase="middlegame"):
    return {
        "input": key,
        "trajectories": trajectories,
        "tags": ["in-check"] if tagged else [],
        "policy": policy,
        "phase": phase,
    }


def test_replacements_preserve_every_contributing_trajectory():
    pool = [
        row("old", ["a", "b"]),
        row("wrong", ["a"], tagged=True),
        row("new", ["a", "b"], tagged=True),
        row("kept", ["c"], tagged=True),
    ]
    pairs = replacement_pairs(pool, {"old", "kept"}, 7)
    assert pairs == [("old", "new")]
    assert replacement_pairs(list(reversed(pool)), {"old", "kept"}, 7) == pairs
    assert concentration([pool[0], pool[3]]) == concentration([pool[2], pool[3]])
    assert replacement_pairs([pool[0], pool[1]], {"old"}, 7) == []


def test_scaling_is_nested_with_exact_policy_phase_quotas_and_cap(tmp_path):
    parent, output = tmp_path / "parent", tmp_path / "plan"
    (parent / "plan").mkdir(parents=True)
    (parent / "plan/block-0-both.json").write_text(json.dumps({"seed": 7, "buckets": []}))
    pool = []
    for policy, count in (("plausible", 8000), ("intervention", 800), ("random", 800)):
        for phase in ("middlegame", "endgame"):
            for i in range(count):
                pool.append(row(f"{policy}-{phase}-{i}", [f"{policy}-{i // 2}"], policy=policy, phase=phase))
    result = scaling_plans(pool, parent, output)
    assert len(result["plans"]) == 6
    for case in ("plausible", "mixed"):
        previous = set()
        for size in (1000, 4000, 16000):
            recipe = json.loads((output / f"{case}-{size}.json").read_text())
            keys = {k for b in recipe["buckets"] for k in b["inputs"]}
            assert len(keys) == size and previous < keys
            previous = keys
            counts = Counter((r["policy"], r["phase"]) for r in pool if r["input"] in keys)
            expected = {("plausible", p): size // 2 for p in ("middlegame", "endgame")}
            if case == "mixed":
                expected = {
                    (c, p): size * w // 20
                    for c, w in (("plausible", 8), ("intervention", 1), ("random", 1))
                    for p in ("middlegame", "endgame")
                }
            assert counts == expected
            assert concentration([r for r in pool if r["input"] in keys])["max_inputs_per_trajectory"] <= 8


def test_trial_reuse_and_decision_rules():
    pytest.importorskip("torch")
    from scripts.run_generated_followups import assess, trial_plan

    plans = {
        "plans": [
            {"name": f"{case}-{n}", "case": case, "size": n, "train_inputs": n}
            for case in ("plausible", "mixed")
            for n in (1000, 4000, 16000)
        ]
    }
    trials = trial_plan({"seeds": [7, 17, 27], "scaling": {"presentations": 800000}}, plans, "scaling")
    assert len(trials) == len({t["name"] for t in trials}) == 30
    assert Counter(t["updates"] for t in trials) == {200: 18, 800: 6, 50: 6}
    assert len([t for t in trials if t["size"] == 4000]) == 6
    semantic = [
        {"case": c, "block": b, "primary": 0.10 if c == "natural" else [0.13, 0.13, 0.09][b]}
        for c in ("natural", "enriched")
        for b in range(3)
    ]
    assert assess(semantic, "semantic")["advance"] == "natural"
    for t in trials:
        t["primary"] = {1000: 0.10, 4000: 0.12, 16000: 0.20}[t["size"]]
        if t["size"] == 16000 and t["seed"] == 7:
            t["primary"] = 0.09
    result = assess(trials, "scaling")
    assert not result["curves"]["passes"]["mixed"]["supported"]


def test_trial_dataset_locations_and_prior_attempt_charges(tmp_path):
    pytest.importorskip("torch")
    from scripts.run_generated_followups import locations, prior_attempts

    cfg = {"parent": "artifacts/parent"}
    trial = {"case": "enriched", "name": "block-0-enriched-updates-200-seed-7", "dataset": "block-0-enriched"}
    snapshot, cache = locations(cfg, tmp_path, "semantic", trial)
    assert snapshot == tmp_path / "semantic/snapshots/block-0-enriched"
    assert cache == tmp_path / "semantic/tensors/block-0-enriched"
    trial.update(case="mixed", name="mixed-16000-updates-50-seed-7", dataset="mixed-16000")
    assert locations(cfg, tmp_path, "scaling", trial)[0] == tmp_path / "scaling/snapshots/mixed-16000"
    for name, elapsed in (("study", 100), ("study-retry-1", 50)):
        path = tmp_path / "semantic" / name
        path.mkdir(parents=True)
        (path / "summary.json").write_text(
            json.dumps({"status": "failed", "elapsed_seconds": elapsed, "prior_attempt_seconds": 900, "trials": []})
        )
    assert sum(a["elapsed_seconds"] for a in prior_attempts(tmp_path, "semantic")) == 150
    path = tmp_path / "semantic/study-retry-1/summary.json"
    path.write_text(json.dumps({"status": "running", "elapsed_seconds": 50, "trials": []}))
    with pytest.raises(ValueError, match="not terminal"):
        prior_attempts(tmp_path, "semantic")
