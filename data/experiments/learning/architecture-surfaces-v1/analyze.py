"""Project retained study observations into mechanism diagnostics; no fitting."""

import argparse
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


def read(path):
    return json.loads(Path(path).read_text())


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mean(values):
    values = list(values)
    return statistics.mean(values) if values else None


def metrics(rows):
    wrong = [r for r in rows if r["prediction"] != r["target"]]
    return {
        "positions": len(rows),
        "correct": sum(r["prediction"] == r["target"] for r in rows),
        "agreement": mean(r["prediction"] == r["target"] for r in rows),
        "cross_entropy": mean(r["loss"] for r in rows),
        "cross_entropy_temperature2": mean(r["loss_temperature2"] for r in rows),
        "confidence": mean(r["confidence"] for r in rows),
        "error_confidence": mean(r["confidence"] for r in wrong),
        "confidence_temperature2": mean(r["confidence_temperature2"] for r in rows),
        "entropy": mean(r["entropy"] for r in rows),
        "top3": mean(r["target"] in r["top3"] for r in rows),
        "source_agreement": mean(r["prediction"] // 90 == r["target"] // 90 for r in rows),
        "destination_agreement": mean(r["prediction"] % 90 == r["target"] % 90 for r in rows),
        "uniform_agreement": mean(1 / r["legal_count"] for r in rows),
        "unmasked_legal": mean(r["unmasked_prediction_legal"] for r in rows),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = read(args.study / "submitted-config.json")
    cache = Path(config["data"]["cache"])
    source_rows = lines(cache / "rows.jsonl")
    by_input = {r["input_hash"]: r for r in source_rows}
    targets = np.load(cache / "targets.npy", mmap_mode="r")
    masks = np.load(cache / "mask.npy", mmap_mode="r")
    frequency = {}
    for coordinate in ("absolute", "canonical"):
        frequency[coordinate] = Counter(
            8099 - int(targets[r["ordinal"]])
            if coordinate == "canonical" and r["turn"] == "black"
            else int(targets[r["ordinal"]])
            for r in source_rows
            if r["split"] == "train"
        )
    baselines = {}
    for coordinate in frequency:
        cells = defaultdict(list)
        for row in source_rows:
            if row["split"] != "validation":
                continue
            ordinal = row["ordinal"]
            legal = np.flatnonzero(masks[ordinal]).tolist()
            transform = coordinate == "canonical" and row["turn"] == "black"
            pred = max(legal, key=lambda a: (frequency[coordinate][8099 - a if transform else a], -a))
            cells[row["bucket"]].append(int(pred == targets[ordinal]))
        baselines[coordinate] = {
            "method": "Board-blind target-frequency ranking with legal mask; ties smallest absolute action.",
            "micro": mean(v for cell in cells.values() for v in cell),
            "macro": mean(mean(v) for v in cells.values()),
            "cells": {k: {"positions": len(v), "agreement": mean(v)} for k, v in cells.items()},
        }
    observations = []
    receipts = {}
    for path in sorted((args.study / "fits").glob("*/checkpoint-*/observation.json")):
        observation = read(path)
        predictions_path = path.parent / "dev-predictions.jsonl"
        rows = lines(predictions_path)
        assert len(rows) == 373 and len({r["input_hash"] for r in rows}) == 373
        groups = defaultdict(list)
        coord = "canonical" if observation["case"].startswith("canonical_") else "absolute"
        for row in rows:
            original = by_input[row["input_hash"]]
            target = row["target"]
            assert target == int(targets[original["ordinal"]])
            assert row["prediction"] in np.flatnonzero(masks[original["ordinal"]])
            model_target = 8099 - target if coord == "canonical" and row["turn"] == "black" else target
            names = ["all", "cell:" + row["bucket"], "turn:" + row["turn"]]
            names += ["forced" if row["legal_count"] == 1 else "nonforced"]
            names += ["absolute_unseen" if not frequency["absolute"][target] else "absolute_seen"]
            names += ["coordinate_unseen" if not frequency[coord][model_target] else "coordinate_seen"]
            names += [
                "legal:"
                + (
                    "1"
                    if row["legal_count"] == 1
                    else "2-3"
                    if row["legal_count"] <= 3
                    else "4-15"
                    if row["legal_count"] <= 15
                    else "16+"
                )
            ]
            names += ["tag:" + tag for tag in original["semantic_tags"]]
            for name in names:
                groups[name].append(row)
        summary = {name: metrics(values) for name, values in groups.items()}
        macro = mean(value["agreement"] for name, value in summary.items() if name.startswith("cell:"))
        observations.append(
            {
                "case": observation["case"],
                "seed": observation["seed"],
                "update": observation["update"],
                "macro_agreement": macro,
                "train": observation["stats"]["train"],
                "slices": summary,
            }
        )
        receipts[str(path)] = digest(path)
        receipts[str(predictions_path)] = digest(predictions_path)
    grouped = defaultdict(list)
    for row in observations:
        grouped[(row["case"], row["update"])].append(row)
    aggregates = []
    for (case, update), rows in grouped.items():
        aggregates.append(
            {
                "case": case,
                "update": update,
                "seeds": [r["seed"] for r in rows],
                "macro_agreement": mean(r["macro_agreement"] for r in rows),
                "macro_range": [min(r["macro_agreement"] for r in rows), max(r["macro_agreement"] for r in rows)],
                "train_agreement": mean(r["train"]["agreement"] for r in rows),
                "train_cross_entropy": mean(r["train"]["cross_entropy"] for r in rows),
                "slices": {
                    name: {
                        key: (
                            values[0][key] if key == "positions" else mean(v[key] for v in values if v[key] is not None)
                        )
                        for key in values[0]
                    }
                    for name in rows[0]["slices"]
                    if (values := [r["slices"][name] for r in rows])
                },
            }
        )
    contrasts = []
    for first, second in [
        ("absolute_mlp64", "absolute_mlp128"),
        ("absolute_mlp64", "canonical_mlp64"),
        ("canonical_mlp64", "canonical_pair64"),
        ("canonical_pair64", "canonical_conv32"),
    ]:
        for update in config["checkpoints"]:
            one = {r["seed"]: r for r in observations if r["case"] == first and r["update"] == update}
            two = {r["seed"]: r for r in observations if r["case"] == second and r["update"] == update}
            contrasts.append(
                {
                    "first": first,
                    "second": second,
                    "update": update,
                    "paired_macro_delta_pp": {
                        str(seed): 100 * (two[seed]["macro_agreement"] - one[seed]["macro_agreement"])
                        for seed in one.keys() & two.keys()
                    },
                }
            )
    result = {
        "version": "architecture-surfaces-analysis-v1",
        "scope": "Exploratory; initialization seeds share one dataset and development pool.",
        "baselines": baselines,
        "observations": observations,
        "aggregates": aggregates,
        "contrasts": contrasts,
        "receipts": receipts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "observations": len(observations)}))


if __name__ == "__main__":
    main()
