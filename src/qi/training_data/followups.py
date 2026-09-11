"""Training-only selection for the locked generated-data follow-up studies."""

import json
from collections import Counter, defaultdict
from pathlib import Path

from qi.artifacts import write_json
from qi.teacher import digest
from qi.training_data.contracts import fingerprint
from qi.training_data.mixing import PHASES, POLICIES, choose, rank
from qi.training_data.semantics import SEMANTIC_VERSION, semantic_tags
from qi.training_data.store import Collection


def load_pool(path):
    manifest = json.loads((path / "manifest.json").read_text())
    if digest(path / "rows.jsonl") != manifest["rows_sha256"]:
        raise ValueError("Training candidate pool changed.")
    with (path / "rows.jsonl").open() as stream:
        return [json.loads(line) for line in stream]


def prepare_pool(parent: Path, collection: Path, output: Path):
    """Reuse the parent's reasoned exclusions, never scan development predictions."""
    if output.exists():
        raise ValueError("Choose a fresh candidate pool.")
    cfg = json.loads((parent / "config.json").read_text())
    if digest(collection) != cfg["collection_sha256"]:
        raise ValueError("Raw collection differs from the completed screen.")
    eligibility = json.loads((parent / "plan/eligibility.json").read_text())
    excluded = eligibility["excluded_inputs"]
    seed = cfg["selection_seed"]
    rows = {}
    with Collection(collection, readonly=True) as store:
        for r in store.db.execute(
            """SELECT o.input_hash,o.phase,o.board,o.turn,a.move,g.trajectory,
            json_extract(g.payload,'$.actor.policy.mode') policy
            FROM position_occurrences o JOIN games g ON g.id=o.game_id
            JOIN analysis_specs s ON s.identity=?
            JOIN analyses a ON a.occurrence_id=o.id AND a.spec_id=s.id
            WHERE g.status='complete' AND g.split='train'
            AND json_extract(o.payload,'$.metadata.selected')=1
            AND a.status='success' AND a.id=(SELECT a2.id FROM analyses a2
                WHERE a2.occurrence_id=o.id AND a2.spec_id=s.id AND a2.status='success'
                ORDER BY a2.success_order LIMIT 1)
            ORDER BY o.id""",
            (cfg["analysis_spec"],),
        ):
            key = r["input_hash"]
            if key in excluded or r["phase"] not in PHASES:
                continue
            block = int(rank(seed, r["trajectory"]), 16) % cfg["blocks"]
            value = {
                "input": key,
                "policy": r["policy"],
                "phase": r["phase"],
                "block": block,
                "board": r["board"],
                "turn": r["turn"],
                "move": r["move"],
            }
            if key in rows:
                if any(rows[key][k] != v for k, v in value.items()):
                    raise ValueError("Parent exclusions left conflicting training evidence.")
                rows[key]["trajectories"].add(r["trajectory"])
            else:
                rows[key] = {**value, "trajectories": {r["trajectory"]}}
    counts = Counter(f"train-{r['block']}:{r['policy']}:{r['phase']}" for r in rows.values())
    if dict(counts) != {k: v for k, v in eligibility["counts"].items() if k.startswith("train-")}:
        raise ValueError("Candidate pool does not reproduce the parent training census.")
    output.mkdir(parents=True)
    with (output / "rows.jsonl").open("x") as stream:
        for key in sorted(rows):
            row = rows[key]
            row["trajectories"] = sorted(row["trajectories"])
            row["tags"] = semantic_tags(row["board"], row["turn"], row["move"])
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    manifest = {
        "version": "generated-followup-pool-v1",
        "collection_sha256": cfg["collection_sha256"],
        "parent": str(parent.resolve()),
        "parent_eligibility_sha256": digest(parent / "plan/eligibility.json"),
        "parent_plan_sha256": digest(parent / "plan/manifest.json"),
        "semantic_version": SEMANTIC_VERSION,
        "rows": len(rows),
        "counts": dict(counts),
        "rows_sha256": digest(output / "rows.jsonl"),
        "scope": "Parent-eligible training inputs only; no development or sealed predictions.",
    }
    write_json(output / "manifest.json", manifest, indent=2)
    return manifest


def replacement_pairs(candidates, selected, seed):
    """Same full trajectory-lineage signature and phase/policy for each replacement."""
    groups = defaultdict(lambda: {"old": [], "new": []})
    for r in candidates:
        sig = tuple(r["trajectories"])
        if r["input"] in selected and not r["tags"]:
            groups[sig]["old"].append(r["input"])
        elif r["input"] not in selected and r["tags"]:
            groups[sig]["new"].append(r["input"])
    pairs = []
    for sig in sorted(groups, key=lambda t: rank(seed, t)):
        group = groups[sig]
        for key in group:
            group[key].sort(key=lambda k: rank(seed, k))
        pairs.extend(zip(group["old"], group["new"], strict=False))
    return pairs


def concentration(rows):
    counts = Counter(t for r in rows for t in r["trajectories"])
    return {
        "trajectories": len(counts),
        "max_inputs_per_trajectory": max(counts.values(), default=0),
        "histogram": {str(n): count for n, count in Counter(counts.values()).items()},
        "lineage_counts_sha256": fingerprint("trajectory-counts-v1", dict(sorted(counts.items()))),
    }


def semantic_plans(pool, parent, output, *, max_percentage=10, min_percentage=5):
    if output.exists():
        raise ValueError("Choose a fresh semantic plan.")
    lookup = {r["input"]: r for r in pool}
    cell_pairs, recipes = {}, {}
    for block in range(3):
        recipe = json.loads((parent / f"plan/block-{block}-both.json").read_text())
        recipes[block] = recipe
        for bucket in recipe["buckets"]:
            if bucket["split"] != "train":
                continue
            policy = bucket["themes"][0].removeprefix("policy:")
            phase = bucket["phases"][0]
            candidates = [r for r in pool if r["block"] == block and r["policy"] == policy and r["phase"] == phase]
            pairs = replacement_pairs(candidates, set(bucket["inputs"]), recipe["seed"])
            cell_pairs[(block, bucket["id"])] = pairs
    percentage = min(
        max_percentage,
        *(
            100 * len(cell_pairs[(block, b["id"])]) // b["count"]
            for block, recipe in recipes.items()
            for b in recipe["buckets"]
            if b["split"] == "train"
        ),
    )
    if percentage < min_percentage:
        raise ValueError(f"Matched enrichment supports only {percentage} percentage points; minimum {min_percentage}.")
    output.mkdir(parents=True)
    plans, cells = [], []
    for block, original in recipes.items():
        enriched = json.loads(json.dumps(original))
        old_rows, new_rows = [], []
        for bucket in enriched["buckets"]:
            if bucket["split"] != "train":
                continue
            old = set(bucket["inputs"])
            count = bucket["count"] * percentage // 100
            pairs = cell_pairs[(block, bucket["id"])][:count]
            new = old - {p[0] for p in pairs} | {p[1] for p in pairs}
            if len(new) != len(old):
                raise ValueError("Semantic replacement changed a quota.")
            bucket["inputs"] = sorted(new)
            old_rows.extend(lookup[k] for k in old)
            new_rows.extend(lookup[k] for k in new)
            cells.append(
                {
                    "block": block,
                    "bucket": bucket["id"],
                    "count": len(old),
                    "natural_tagged": sum(bool(lookup[k]["tags"]) for k in old),
                    "enriched_tagged": sum(bool(lookup[k]["tags"]) for k in new),
                    "replacements": pairs,
                    "available_matched_pairs": len(cell_pairs[(block, bucket["id"])]),
                }
            )
        if concentration(old_rows) != concentration(new_rows):
            raise ValueError("Matched enrichment changed source concentration.")
        for case, recipe in (("natural", original), ("enriched", enriched)):
            name = f"block-{block}-{case}"
            write_json(output / f"{name}.json", recipe, indent=2)
            plans.append(
                {
                    "name": name,
                    "block": block,
                    "case": case,
                    "recipe": f"{name}.json",
                    "train_inputs": 4000,
                    "concentration": concentration(old_rows),
                }
            )
    result = {
        "status": "complete",
        "percentage_point_increase": percentage,
        "plans": plans,
        "cells": cells,
        "trajectory_counts_identical": True,
        "tag_predicate": "in-check OR teacher-capture OR teacher-gives-check",
    }
    write_json(output / "manifest.json", result, indent=2)
    return result


def scaling_plans(pool, parent, output):
    if output.exists():
        raise ValueError("Choose a fresh scaling plan.")
    template = json.loads((parent / "plan/block-0-both.json").read_text())
    validation = [b for b in template["buckets"] if b["split"] == "validation"]
    lookup = {r["input"]: r for r in pool}
    counts = Counter((r["policy"], r["phase"]) for r in pool)
    plans = []
    output.mkdir(parents=True)
    for case, mix in {"plausible": (1, 0, 0), "mixed": (0.8, 0.1, 0.1)}.items():
        used, master = Counter(), []
        for policy, weight in zip(POLICIES, mix, strict=True):
            if not weight:
                continue
            for phase in sorted(PHASES, key=lambda p: counts[policy, p]):
                count = int(16000 * weight / 2)
                keys = choose(pool, policy, phase, count, used, template["seed"], 8)
                master.append(
                    {
                        "id": f"train-{policy}-{phase}",
                        "split": "train",
                        "count": count,
                        "themes": [f"policy:{policy}"],
                        "phases": [phase],
                        "inputs": keys,
                    }
                )
        previous = set()
        for size in (1000, 4000, 16000):
            buckets = []
            for b in master:
                count = b["count"] * size // 16000
                buckets.append({**b, "count": count, "inputs": b["inputs"][:count]})
            keys = {k for b in buckets for k in b["inputs"]}
            if len(keys) != size or not previous <= keys:
                raise ValueError("Scaling quotas or nesting failed.")
            previous = keys
            name = f"{case}-{size}"
            write_json(output / f"{name}.json", {**template, "buckets": buckets + validation}, indent=2)
            plans.append(
                {
                    "name": name,
                    "case": case,
                    "size": size,
                    "train_inputs": size,
                    "recipe": f"{name}.json",
                    "concentration": concentration([lookup[k] for k in keys]),
                }
            )
    result = {
        "status": "complete",
        "plans": plans,
        "nested": True,
        "master_pool": "union of three original training blocks",
        "tag_policy": "natural deterministic source-balanced selection, independent of semantic-screen results",
    }
    write_json(output / "manifest.json", result, indent=2)
    return result
