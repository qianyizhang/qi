"""Data-only feasibility audit of 48 x 16 versus 192 x 4; never train or query a teacher."""

import argparse
import json
from collections import Counter, defaultdict, deque
from pathlib import Path
from random import Random

from qi.learning.data import Dataset


def ply(label) -> int:
    return len(label.analysis.snapshot.moves)


def match_plies(groups: dict, source_ids: list[str], target: Counter, seed: int) -> list:
    """Integral source→ply flow: four distinct labels/game and an exact global histogram."""
    edges, residual = defaultdict(list), {}

    def edge(left, right, capacity):
        edges[left].append(right)
        edges[right].append(left)
        residual[left, right], residual[right, left] = capacity, 0

    rng = Random(seed)
    ids = list(source_ids)
    rng.shuffle(ids)
    for source in ids:
        edge("root", source, 4)
        positions = list(groups[source])
        rng.shuffle(positions)
        for label in positions:
            edge(source, f"ply-{ply(label)}", 1)
    for position, count in sorted(target.items()):
        edge(f"ply-{position}", "sink", count)
    flow = 0
    while True:
        parents, queue = {"root": None}, deque(["root"])
        while queue and "sink" not in parents:
            current = queue.popleft()
            for neighbor in edges[current]:
                if neighbor not in parents and residual[current, neighbor] > 0:
                    parents[neighbor] = current
                    queue.append(neighbor)
        if "sink" not in parents:
            break
        current = "sink"
        while parents[current] is not None:
            previous = parents[current]
            residual[previous, current] -= 1
            residual[current, previous] += 1
            current = previous
        flow += 1
    if flow != sum(target.values()):
        raise ValueError(f"Ply matching infeasible: matched {flow}/{sum(target.values())}; do not relax silently.")
    return [label for source in source_ids for label in groups[source] if residual[source, f"ply-{ply(label)}"] == 0]


def investigate(dataset: Dataset) -> dict:
    groups = defaultdict(list)
    for label in dataset.split_labels("train"):
        groups[label.source_id].append(label)
    full = {source: labels for source, labels in groups.items() if len(labels) == 16}
    ids = sorted(full)
    Random(401).shuffle(ids)
    if len(ids) < 3 * 192:
        raise ValueError("Need at least 576 full sources for three disjoint feasibility blocks.")
    holdout = {label.input_sha256 for label in dataset.split_labels("validation")}
    source_snapshots = {source.id: tuple(source.snapshot.moves) for source in dataset.sources}
    if len({source_snapshots[source] for source in ids}) != len(ids):
        raise ValueError("Duplicate complete trajectories are not independent source games.")
    result = {
        "purpose": "selection feasibility only; no policy, loss, or teacher-target comparison",
        "dataset_sha256": dataset.digest,
        "selection_seed": 401,
        "contributing_train_games": len(groups),
        "labels_per_train_source": dict(sorted(Counter(map(len, groups.values())).items())),
        "full_16_label_sources": len(full),
        "sources_with_four_per_eight_ply_band": sum(
            all(sum((ply(label) - 1) // 8 == band for label in labels) >= 4 for band in range(4))
            for labels in full.values()
        ),
        "heldout_games": sum(source.split == "validation" for source in dataset.sources),
        "heldout_positions": len(holdout),
        "replicates": [],
    }
    for index in range(3):
        pool = ids[index * 192 : (index + 1) * 192]
        concentrated = [label for source in pool[:48] for label in full[source]]
        target = Counter(map(ply, concentrated))
        broader = match_plies(full, pool, target, seed=501 + index)
        cases = {}
        for name, labels, expected_sources, per_game in [
            ("concentrated", concentrated, 48, 16),
            ("broader", broader, 192, 4),
        ]:
            keys = {label.input_sha256 for label in labels}
            counts = Counter(label.source_id for label in labels)
            assert len(labels) == len(keys) == 768
            assert len(counts) == expected_sources and set(counts.values()) == {per_game}
            assert Counter(map(ply, labels)) == target and not keys & holdout
            cases[name] = {"games": len(counts), "labels": len(labels), "input_ids": sorted(keys)}
        overlap = set(cases["concentrated"]["input_ids"]) & set(cases["broader"]["input_ids"])
        assert len(overlap) == 192
        result["replicates"].append(
            {
                "block": index,
                "source_games": pool,
                "ply_counts": dict(sorted(target.items())),
                "shared_inputs": len(overlap),
                "cases": cases,
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a fresh output path.")
    dataset = Dataset.model_validate_json(args.data.read_text())
    result = investigate(dataset)
    result["source_dataset"] = str(args.data.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: value for key, value in result.items() if key != "replicates"}))
    print("Three disjoint blocks feasible: 768 labels/case; exact ply matching; 192 shared inputs/pair.")


if __name__ == "__main__":
    main()
