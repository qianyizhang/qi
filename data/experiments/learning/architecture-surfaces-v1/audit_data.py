"""Descriptive frozen-input audit; no teacher queries or model predictions."""

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from time import perf_counter

import numpy as np

from qi.artifacts import write_json
from qi.evaluation import Corpus
from qi.game import Game, other
from qi.learning.provenance import source_identity
from qi.learning.snapshot import SnapshotTensors
from qi.players.policy.encoding import action_id, input_key
from qi.teacher import digest
from qi.training_data.v1 import reserved_inputs


def distribution(values):
    values = np.asarray(values, dtype=float)
    if not len(values):
        return {"count": 0}
    return {
        "count": len(values),
        "min": float(values.min()),
        "p10": float(np.quantile(values, 0.1)),
        "median": float(np.median(values)),
        "p90": float(np.quantile(values, 0.9)),
        "max": float(values.max()),
        "mean": float(values.mean()),
    }


def frequency_bin(count):
    if count == 0:
        return "0-unseen"
    if count == 1:
        return "1"
    if count < 5:
        return "2-4"
    if count < 20:
        return "5-19"
    return "20+"


def summarize(rows):
    n = len(rows)
    legal = np.asarray([r["legal_count"] for r in rows])
    return {
        "positions": n,
        "turn_counts": dict(Counter(r["turn"] for r in rows)),
        "legal_count": distribution(legal),
        "legal_count_histogram": dict(sorted(Counter(map(int, legal)).items())),
        "forced_positions": int(sum(legal == 1)),
        "forced_fraction": float(np.mean(legal == 1)),
        "uniform_legal_agreement": float(np.mean(1 / legal)),
        "uniform_legal_cross_entropy": float(np.mean(np.log(legal))),
        "ply_count": distribution([r["ply_count"] for r in rows]),
        "material_total": distribution([r["material_total"] for r in rows]),
        "material_nonking": distribution([r["material_total"] - 2 for r in rows]),
        "tag_counts": dict(Counter(tag for r in rows for tag in r["semantic_tags"])),
        "no_tag_positions": sum(not r["semantic_tags"] for r in rows),
        "target_piece_counts": dict(Counter(r["target_piece"] for r in rows)),
        "target_training_frequency": dict(Counter(frequency_bin(r["train_action_count"]) for r in rows)),
        "canonical_target_training_frequency": dict(
            Counter(frequency_bin(r["train_canonical_action_count"]) for r in rows)
        ),
        "unseen_target_source_square": sum(r["train_source_count"] == 0 for r in rows),
        "unseen_target_destination_square": sum(r["train_destination_count"] == 0 for r in rows),
    }


def concentration(rows):
    counts = Counter(r["trajectory"] for r in rows)
    values = sorted(counts.values(), reverse=True)
    n = len(rows)
    return {
        "positions": n,
        "distinct_trajectories": len(counts),
        "distinct_families": len({r["family"] for r in rows}),
        "contributions_per_trajectory": distribution(values),
        "largest_trajectory_fraction": values[0] / n,
        "top10_trajectory_fraction": sum(values[:10]) / n,
        "inverse_concentration_effective_trajectories": n * n / sum(v * v for v in values),
    }


def history_aliases(db, inputs, analysis_spec):
    """Only selected-input state/move counts; no unselected or sealed labels read."""
    details = {}
    for start in range(0, len(inputs), 500):
        batch = inputs[start : start + 500]
        placeholders = ",".join("?" for _ in batch)
        query = f"""SELECT o.input_hash, count(DISTINCT o.identity), count(DISTINCT o.state_hash),
            count(DISTINCT g.trajectory), count(DISTINCT o.ply_count), count(DISTINCT a.move)
            FROM position_occurrences o JOIN games g ON g.id=o.game_id
            LEFT JOIN analysis_specs s ON s.identity=?
            LEFT JOIN analyses a ON a.occurrence_id=o.id AND a.spec_id=s.id AND a.status='success'
            WHERE o.input_hash IN ({placeholders}) GROUP BY o.input_hash"""
        for key, occurrences, states, trajectories, plies, moves in db.execute(query, [analysis_spec, *batch]):
            details[key] = {
                "stored_occurrences": occurrences,
                "distinct_history_states": states,
                "distinct_trajectories": trajectories,
                "distinct_ply_counts": plies,
                "distinct_successful_targets_at_selected_spec": moves,
            }
    return details


def audit(cache_path, sealed, output):
    cache = SnapshotTensors(cache_path)
    snapshot = Path(cache.manifest["snapshot"])
    snapshot_manifest = json.loads((snapshot / "manifest.json").read_text())
    reserved = reserved_inputs(Corpus.model_validate(snapshot_manifest["recipe"]["reserved_corpus"]))
    identity_paths = [cache_path / name for name in ("manifest.json", *cache.manifest["files"])]
    identity_paths += [snapshot / "manifest.json", snapshot / "evidence.sqlite"]
    before = {str(path.resolve()): digest(path) for path in identity_paths}
    rows = []
    for row in cache.rows():
        game = Game(board=row["board"], turn=row["turn"])
        original = input_key(game)
        if original != row["input_hash"]:
            raise ValueError("Row board and identity disagree.")
        rotated = input_key(Game(board=game.board[::-1].swapcase(), turn=other(game.turn)))
        target = int(cache.arrays["targets"][row["ordinal"]])
        if target != action_id(row["move"]):
            raise ValueError("Row move and target disagree.")
        canonical = original if game.turn == "red" else rotated
        canonical_target = target if game.turn == "red" else 8099 - target
        legal_count = int(cache.arrays["mask"][row["ordinal"]].sum())
        if legal_count < 1 or not cache.arrays["mask"][row["ordinal"], target]:
            raise ValueError("Illegal target or empty mask.")
        rows.append(
            {
                key: row[key]
                for key in (
                    "input_hash",
                    "ordinal",
                    "occurrence",
                    "bucket",
                    "split",
                    "phase",
                    "turn",
                    "ply_count",
                    "semantic_tags",
                )
            }
            | {
                "canonical_input_hash": canonical,
                "opposite_color_input_hash": rotated,
                "target": target,
                "canonical_target": canonical_target,
                "legal_count": legal_count,
                "material_total": sum(row["material"].values()),
                "target_piece": game.board[target // 90].upper(),
            }
        )
    train = [r for r in rows if r["split"] == "train"]
    development = [r for r in rows if r["split"] == "validation"]
    counts = Counter(r["target"] for r in train)
    canonical_counts = Counter(r["canonical_target"] for r in train)
    source_counts = Counter(r["target"] // 90 for r in train)
    destination_counts = Counter(r["target"] % 90 for r in train)
    for row in rows:
        row.update(
            train_action_count=counts[row["target"]],
            train_canonical_action_count=canonical_counts[row["canonical_target"]],
            train_source_count=source_counts[row["target"] // 90],
            train_destination_count=destination_counts[row["target"] % 90],
        )
    collisions = {}
    for name, hashes in (("sealed", sealed), ("reserved", reserved)):
        collisions[name] = {
            "identity_count": len(hashes),
            "original_matches": [r["input_hash"] for r in rows if r["input_hash"] in hashes],
            "opposite_color_matches": [r["input_hash"] for r in rows if r["opposite_color_input_hash"] in hashes],
        }
    # Selected identities must be disjoint before reading their teacher-target counts.
    if collisions["sealed"]["original_matches"]:
        raise ValueError("Selected inputs overlap sealed identities; stop before evidence queries.")
    with sqlite3.connect(f"file:{snapshot / 'evidence.sqlite'}?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        occurrence_identity = {
            occurrence: (trajectory, family)
            for occurrence, trajectory, family in db.execute(
                "SELECT o.identity,g.trajectory,g.family FROM position_occurrences o JOIN games g ON g.id=o.game_id"
            )
        }
        for row in rows:
            row["trajectory"], row["family"] = occurrence_identity[row["occurrence"]]
        histories = history_aliases(db, [r["input_hash"] for r in rows], cache.manifest["analysis_spec"])
    for row in rows:
        row["retained_history_evidence"] = histories[row["input_hash"]]
    canonical_groups = defaultdict(list)
    for row in rows:
        canonical_groups[row["canonical_input_hash"]].append(row)
    conflicting = [key for key, group in canonical_groups.items() if len({r["canonical_target"] for r in group}) > 1]
    cross_split = [key for key, group in canonical_groups.items() if len({r["split"] for r in group}) > 1]
    grouped = {split: summarize(selected) for split, selected in (("train", train), ("development", development))}
    buckets = {
        name: summarize([r for r in rows if r["bucket"] == name]) for name in sorted({r["bucket"] for r in rows})
    }
    dev_buckets = [value for name, value in buckets.items() if name.startswith("development-")]
    result = {
        "cache": str(cache_path.resolve()),
        "cache_fingerprint": cache.manifest["fingerprint"],
        "snapshot_fingerprint": cache.manifest["snapshot_fingerprint"],
        "supervision": cache.manifest["supervision"],
        "identities": before,
        "split_summaries": grouped,
        "bucket_summaries": buckets,
        "phase_summaries": {
            f"{split}:{phase}": summarize([r for r in rows if r["split"] == split and r["phase"] == phase])
            for split in ("train", "validation")
            for phase in sorted({r["phase"] for r in rows if r["split"] == split})
        },
        "development_macro": {
            "cells": len(dev_buckets),
            "uniform_legal_agreement": float(np.mean([r["uniform_legal_agreement"] for r in dev_buckets])),
            "uniform_legal_cross_entropy": float(np.mean([r["uniform_legal_cross_entropy"] for r in dev_buckets])),
            "forced_fraction": float(np.mean([r["forced_fraction"] for r in dev_buckets])),
        },
        "target_support": {
            "possible_coordinate_actions": 8100,
            "training_distinct_actions": len(counts),
            "training_distinct_canonical_actions": len(canonical_counts),
            "training_distinct_source_squares": len(source_counts),
            "training_distinct_destination_squares": len(destination_counts),
            "training_action_count_histogram": dict(sorted(Counter(counts.values()).items())),
        },
        "trajectory_concentration": {
            "train": concentration(train),
            "development": concentration(development),
            "by_bucket": {name: concentration([r for r in rows if r["bucket"] == name]) for name in buckets},
            "cross_split_trajectories": sorted(
                {r["trajectory"] for r in train} & {r["trajectory"] for r in development}
            ),
            "cross_split_families": sorted({r["family"] for r in train} & {r["family"] for r in development}),
        },
        "input_equivalence": {
            "original_cross_split": sorted({r["input_hash"] for r in train} & {r["input_hash"] for r in development}),
            "canonical_cross_split": cross_split,
            "canonical_duplicate_groups": sum(len(group) > 1 for group in canonical_groups.values()),
            "canonical_conflicting_target_groups": conflicting,
            "exclusions": collisions,
            "method": (
                "For selected rows only, hash original and rotate180/color-swap/opposite-turn board inputs. "
                "Canonical is the red-to-move identity. Sealed file contributes identity hashes only; "
                "no sealed boards, labels, models or scores loaded."
            ),
        },
        "retained_history_aliases": {
            "selected_inputs": len(rows),
            "inputs_with_multiple_occurrences": sum(r["stored_occurrences"] > 1 for r in histories.values()),
            "inputs_with_multiple_history_states": sum(r["distinct_history_states"] > 1 for r in histories.values()),
            "inputs_with_multiple_trajectories": sum(r["distinct_trajectories"] > 1 for r in histories.values()),
            "inputs_with_multiple_ply_counts": sum(r["distinct_ply_counts"] > 1 for r in histories.values()),
            "inputs_with_conflicting_successful_targets_at_selected_spec": sum(
                r["distinct_successful_targets_at_selected_spec"] > 1 for r in histories.values()
            ),
            "scope": (
                "Only occurrences retained in this frozen snapshot evidence.sqlite for selected board/turn identities; "
                "not a census of parent collection or a proof that board-only observation is sufficient."
            ),
        },
    }
    supporting = output / f"{cache_path.name}-rows.jsonl"
    with supporting.open("x") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
    result["supporting_rows"] = {"path": str(supporting.resolve()), "sha256": digest(supporting), "rows": len(rows)}
    result["inputs_unchanged"] = before == {path: digest(Path(path)) for path in before}
    if not result["inputs_unchanged"]:
        raise ValueError("Input identity changed during read-only audit.")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    output = args.output.resolve()
    if output.exists():
        raise ValueError("Choose a fresh audit output directory.")
    output.mkdir(parents=True)
    started = perf_counter()
    sealed_path = root / "artifacts/learning/generated-source-mixing-v1-run3/plan/sealed-test-inputs.json"
    sealed_digest = digest(sealed_path)
    sealed = {row["input"] for row in json.loads(sealed_path.read_text())}
    report = {
        "schema_version": "architecture-data-audit-v1",
        "source": source_identity(),
        "script_sha256": digest(Path(__file__)),
        "sealed_identity_file": {"path": str(sealed_path), "sha256": sealed_digest, "identities": len(sealed)},
        "settings": {
            "caches": ["mixed-4000", "mixed-16000"],
            "statistical_role": "descriptive reused development data; no teacher or model inference",
        },
        "datasets": {},
    }
    for name in report["settings"]["caches"]:
        path = root / "artifacts/learning/generated-followups-v1/scaling/tensors" / name
        report["datasets"][name] = audit(path, sealed, output)
        write_json(output / "data-audit.json", report, indent=2)
    report["sealed_identity_file"]["unchanged"] = digest(sealed_path) == sealed_digest
    report["elapsed_seconds"] = perf_counter() - started
    report["status"] = "complete"
    write_json(output / "data-audit.json", report, indent=2)
    print(
        json.dumps(
            {
                "status": "complete",
                "report": str(output / "data-audit.json"),
                "elapsed_seconds": report["elapsed_seconds"],
            }
        )
    )


if __name__ == "__main__":
    main()
