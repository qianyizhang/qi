"""Frozen, game-balanced input plans for the generated-source composition study."""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from qi.artifacts import write_json
from qi.teacher import digest
from qi.training_data.contracts import fingerprint

POLICIES = ("plausible", "intervention", "random")
PHASES = ("middlegame", "endgame")


def rank(seed, value):
    return fingerprint("generated-mixing-order-v1", [seed, value])


def prior_inputs(root: Path, output: Path):
    inputs, receipts = set(), []
    for path in sorted((root / "artifacts/learning").rglob("*.json")):
        if path.is_relative_to(output) or "overnight-" in str(path) or "generated-sample-audit" in str(path):
            continue
        if "/source/" in str(path) or "/training-source/" in str(path) or "/generation-source/" in str(path):
            continue
        raw = path.read_bytes()
        found = set(re.findall(rb'"input_sha256"\s*:\s*"([a-f0-9]{64})"', raw))
        if found:
            inputs.update(v.decode() for v in found)
            receipts.append({"path": str(path.relative_to(root)), "sha256": digest(path), "inputs": len(found)})
    return inputs, receipts


def choose(rows, policy, phase, count, used, seed, cap, *, allow_shortfall=False):
    groups = defaultdict(list)
    for row in rows:
        if row["policy"] == policy and row["phase"] == phase:
            groups[min(row["trajectories"])].append(row)
    for values in groups.values():
        values.sort(key=lambda r: rank(seed, r["input"]))
    ordered = sorted(groups, key=lambda t: rank(seed, t))
    selected = []
    for turn in range(max((len(v) for v in groups.values()), default=0)):
        for trajectory in ordered:
            if turn >= len(groups[trajectory]):
                continue
            row = groups[trajectory][turn]
            if any(used[t] >= cap for t in row["trajectories"]):
                continue
            selected.append(row["input"])
            used.update(row["trajectories"])
            if len(selected) == count:
                return selected
    if allow_shortfall:
        return selected
    raise ValueError(f"Quota shortfall: {policy}/{phase}, requested {count}, available under cap {len(selected)}")


def plan_mixing(db, config, root: Path, output: Path):
    if config["development_quota_policy"] != "cap-aware-up-to-limit-scarce-first-v1":
        raise ValueError("Unsupported development quota policy; use the explicit pre-fit amendment.")
    if output.exists():
        raise ValueError("Choose a fresh plan directory.")
    output.mkdir(parents=True)
    seed = config["selection_seed"]
    old, receipts = prior_inputs(root, output.parent)
    games = {}
    for row in db.execute(
        "SELECT id,split,trajectory,json_extract(payload,'$.actor.policy.mode') policy "
        "FROM games WHERE status='complete'"
    ):
        group = (
            f"train-{int(rank(seed, row['trajectory']), 16) % config['blocks']}"
            if row["split"] == "train"
            else "development"
            if int(rank(seed, row["trajectory"]), 16) % 2 == 0
            else "sealed-test"
        )
        games[row["id"]] = {
            "split": row["split"],
            "trajectory": row["trajectory"],
            "policy": row["policy"],
            "group": group,
        }
    all_groups, splits = defaultdict(set), defaultdict(set)
    for _oid, gid, key in db.execute("SELECT id,game_id,input_hash FROM position_occurrences"):
        if gid in games:
            all_groups[key].add(games[gid]["group"])
            splits[key].add(games[gid]["split"])
    exclusions = {key: "previous-dataset-input" for key in old}
    for key, groups in all_groups.items():
        if len(groups) > 1:
            exclusions[key] = "cross-split-lineage" if len(splits[key]) > 1 else "cross-experimental-group-input"
    rows = defaultdict(list)
    for row in db.execute(
        """
        SELECT o.input_hash,o.game_id,o.phase,o.identity,a.move
        FROM position_occurrences o JOIN games g ON g.id=o.game_id
        JOIN analysis_specs s ON s.identity=?
        JOIN analyses a ON a.occurrence_id=o.id AND a.spec_id=s.id
        WHERE g.status='complete' AND json_extract(o.payload,'$.metadata.selected')=1
        AND a.status='success' AND a.id=(SELECT a2.id FROM analyses a2
            WHERE a2.occurrence_id=o.id AND a2.spec_id=s.id AND a2.status='success'
            ORDER BY a2.success_order LIMIT 1)
        ORDER BY o.id
    """,
        (config["analysis_spec"],),
    ):
        rows[row["input_hash"]].append(dict(row))
    eligible = []
    for key, occurrences in rows.items():
        if len({r["move"] for r in occurrences}) > 1:
            exclusions[key] = "conflicting-target-under-selected-spec"
        if key in exclusions:
            continue
        policies = {games[r["game_id"]]["policy"] for r in occurrences}
        if len(policies) > 1:
            exclusions[key] = "cross-policy-observation"
            continue
        row = occurrences[0]
        if row["phase"] not in PHASES:
            continue
        g = games[row["game_id"]]
        eligible.append(
            {
                "input": key,
                "policy": g["policy"],
                "phase": row["phase"],
                "group": g["group"],
                "trajectories": sorted({games[r["game_id"]]["trajectory"] for r in occurrences}),
            }
        )
    census = Counter(f"{r['group']}:{r['policy']}:{r['phase']}" for r in eligible)
    write_json(
        output / "eligibility.json",
        {
            "counts": dict(census),
            "exclusion_reasons": dict(Counter(exclusions.values())),
            "excluded_inputs": exclusions,
            "prior_inputs": receipts,
        },
        indent=2,
    )
    corpus = json.loads(
        db.execute("SELECT json_extract(payload,'$.config.recipe.corpus') FROM generation_runs LIMIT 1").fetchone()[0]
    )
    development = [r for r in eligible if r["group"] == "development"]
    used = Counter()
    validation = []
    for policy in POLICIES:
        for phase in sorted(PHASES, key=lambda ph: census[f"development:{policy}:{ph}"]):
            count = min(config["development_max_per_cell"], census[f"development:{policy}:{phase}"])
            if count < 20:
                raise ValueError(f"Too little development support for {policy}/{phase}: {count}")
            keys = choose(development, policy, phase, count, used, seed, config["trajectory_cap"], allow_shortfall=True)
            if len(keys) < 20:
                raise ValueError(f"Too little capped development support for {policy}/{phase}: {len(keys)}")
            validation.append(
                {
                    "id": f"development-{policy}-{phase}",
                    "split": "validation",
                    "count": len(keys),
                    "themes": [f"policy:{policy}"],
                    "phases": [phase],
                    "inputs": keys,
                }
            )
    write_json(output / "sealed-test-inputs.json", [r for r in eligible if r["group"] == "sealed-test"], indent=2)
    plans = []
    selections = {}
    for block in range(config["blocks"]):
        candidates = [r for r in eligible if r["group"] == f"train-{block}"]
        for case, mix in config["cases"].items():
            used = Counter()
            buckets = []
            for policy in POLICIES:
                for phase in sorted(PHASES, key=lambda ph: census[f"train-{block}:{policy}:{ph}"]):
                    count = int(config["train_size"] * mix[policy] * config["phase_weights"][phase])
                    if not count:
                        continue
                    keys = choose(candidates, policy, phase, count, used, seed, config["trajectory_cap"])
                    buckets.append(
                        {
                            "id": f"train-{policy}-{phase}",
                            "split": "train",
                            "count": count,
                            "themes": [f"policy:{policy}"],
                            "phases": [phase],
                            "inputs": keys,
                        }
                    )
            name = f"block-{block}-{case}"
            recipe = {
                "version": "sql-selection-v2",
                "analysis_spec": config["analysis_spec"],
                "reserved_corpus": corpus,
                "seed": seed,
                "selected_only": True,
                "excluded_inputs": exclusions,
                "buckets": buckets + validation,
            }
            write_json(output / f"{name}.json", recipe, indent=2)
            selections[name] = {key for b in buckets for key in b["inputs"]}
            plans.append(
                {
                    "name": name,
                    "block": block,
                    "case": case,
                    "recipe": f"{name}.json",
                    "train_inputs": sum(b["count"] for b in buckets),
                    "trajectories": len(used),
                    "max_inputs_per_trajectory": max(used.values()),
                    "concentration": dict(Counter(used.values())),
                }
            )
    for a in plans:
        for b in plans:
            if a["block"] != b["block"] and selections[a["name"]] & selections[b["name"]]:
                raise ValueError("Training blocks share selected inputs.")
    valkeys = {key for b in validation for key in b["inputs"]}
    sealed = {r["input"] for r in eligible if r["group"] == "sealed-test"}
    if valkeys & sealed or any(v & (valkeys | sealed) for v in selections.values()):
        raise ValueError("Training, development and sealed inputs overlap.")
    result = {
        "status": "complete",
        "plans": plans,
        "development_buckets": validation,
        "development_inputs_sha256": fingerprint("development-inputs-v1", sorted(valkeys)),
        "sealed_test_inputs": len(sealed),
        "excluded_inputs": len(exclusions),
        "selection_seed": seed,
        "cross_group_inputs_disjoint": True,
    }
    write_json(output / "manifest.json", result, indent=2)
    return result
