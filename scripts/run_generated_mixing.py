"""Prepare, run and independently verify the locked generated-source mixture screen."""

import argparse
import json
import shutil
import statistics
from pathlib import Path
from time import perf_counter

from qi.artifacts import write_json
from qi.learning.provenance import source_identity
from qi.learning.snapshot import SnapshotConfig, SnapshotTensors, prepare_snapshot, train_snapshot
from qi.players.policy.encoding import action_id
from qi.teacher import digest
from qi.training_data.mixing import plan_mixing
from qi.training_data.snapshots import SelectionRecipe, export_snapshot
from qi.training_data.store import Collection

ROOT = Path(__file__).resolve().parents[1]


def prepare(config, output, collection):
    if (output / "config.json").exists() and config != json.loads((output / "config.json").read_text()):
        raise ValueError("Preparation configuration changed; choose a fresh output directory.")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "config.json", config, indent=2)
    if digest(collection) != config["collection_sha256"]:
        raise ValueError("Collection identity differs from the frozen audit.")
    if not (output / "plan/manifest.json").exists():
        with Collection(collection, readonly=True) as store:
            plan_mixing(store.db, config, ROOT, output / "plan")
    plan = json.loads((output / "plan/manifest.json").read_text())
    write_json(output / "config.json", config, indent=2)
    for item in plan["plans"]:
        name = item["name"]
        snapshot = output / "snapshots" / name
        cache = output / "tensors" / name
        if not snapshot.exists():
            print(f"export {name}", flush=True)
            with Collection(collection, readonly=True) as store:
                recipe = SelectionRecipe.model_validate_json((output / "plan" / item["recipe"]).read_text())
                started = perf_counter()
                export_snapshot(store, recipe, snapshot)
                print(f"exported {name} in {perf_counter() - started:.1f}s", flush=True)
        if not cache.exists():
            print(f"prepare tensors {name}", flush=True)
            result = prepare_snapshot(snapshot, cache, chunk_size=config["training"]["chunk_size"])
            print(f"prepared {name} in {result['elapsed_seconds']:.1f}s", flush=True)
        else:
            SnapshotTensors(cache)
    return plan


def fit_config(config, snapshot, seed, seconds):
    return SnapshotConfig.model_validate(
        {
            "data": {"snapshot": str(snapshot.resolve())},
            "training": {**config["training"], "seed": seed},
            "execution": {
                "device": config["execution"]["device"],
                "threads": config["execution"]["threads"],
                "fit_seconds": float(seconds),
            },
        }
    )


def primary(report):
    cells = [v["agreement"] for k, v in report["stats"].items() if k.startswith("bucket:development-")]
    if len(cells) != 6:
        raise ValueError("Primary metric requires all six fixed development cells.")
    return statistics.mean(cells)


def run(config, output):
    if (output / "study").exists():
        raise ValueError("Study execution already exists; retain it and choose a new execution.")
    plan = json.loads((output / "plan/manifest.json").read_text())
    first = plan["plans"][0]["name"]
    data = SnapshotTensors(output / "tensors" / first)
    pilot_cfg = fit_config(config, output / "snapshots" / first, 917, config["execution"]["pilot_seconds"])
    # The resource pilot has no scientific validation result; its scores do not rank cases.
    pilot = train_snapshot(data, pilot_cfg, output / "pilot")
    if pilot["status"] != "complete":
        raise ValueError("Resource pilot incomplete; scientific matrix not started.")
    if pilot["process_peak_rss_bytes"] > 1_500_000_000:
        raise ValueError("Resource pilot exceeded 1.5GB process peak RSS; matrix not started.")
    fit_seconds = min(config["execution"]["max_fit_seconds"], max(60.0, 3 * pilot["elapsed_seconds"]))
    study = output / "study"
    study.mkdir()
    # Retain the exact executed Python and dependency sources, including dirty implementation bytes.
    source = study / "source"
    shutil.copytree(ROOT / "src/qi", source / "src/qi", ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy2(ROOT / name, source / name)
    shutil.copy2(Path(__file__), source / "run_generated_mixing.py")
    source_files = {str(p.relative_to(source)): digest(p) for p in source.rglob("*") if p.is_file()}
    write_json(study / "source-files.json", source_files, indent=2)
    frozen_source = source_identity()
    status = {
        "status": "running",
        "planned_fits": len(plan["plans"]) * len(config["seeds"]),
        "fit_seconds": fit_seconds,
        "total_seconds": config["execution"]["total_seconds"],
        "development_inputs_sha256": plan["development_inputs_sha256"],
        "trials": [],
        "source": frozen_source,
    }
    started = perf_counter()

    def save():
        status["elapsed_seconds"] = perf_counter() - started
        write_json(study / "summary.json", status, indent=2)

    save()
    try:
        for item in plan["plans"]:
            data = SnapshotTensors(output / "tensors" / item["name"])
            for seed in config["seeds"]:
                if source_identity()["source_sha256"] != frozen_source["source_sha256"]:
                    raise ValueError("Implementation changed during the matrix; retain partial execution.")
                remaining = config["execution"]["total_seconds"] - (perf_counter() - started)
                if remaining <= 0:
                    status["status"] = "deadline"
                    save()
                    return status
                name = f"{item['name']}-seed-{seed}"
                status["active_trial"] = name
                save()
                cfg = fit_config(config, output / "snapshots" / item["name"], seed, min(fit_seconds, remaining))
                print(f"fit {name} ({len(status['trials']) + 1}/{status['planned_fits']})", flush=True)
                report = train_snapshot(data, cfg, study / name)
                status["trials"].append(
                    {
                        "name": name,
                        "block": item["block"],
                        "case": item["case"],
                        "seed": seed,
                        "status": report["status"],
                        "primary": primary(report),
                        "seconds": report["elapsed_seconds"],
                        "validation": report["stats"]["validation"],
                        "train": report["stats"]["train"],
                    }
                )
                status.pop("active_trial")
                save()
                print(json.dumps(status["trials"][-1]), flush=True)
                if report["status"] != "complete":
                    status["status"] = "incomplete"
                    save()
                    return status
                if report["process_peak_rss_bytes"] > 1_500_000_000:
                    raise ValueError("Fit process exceeded 1.5GB peak RSS; stopping before another fit.")
        status["status"] = "complete"
    except (Exception, KeyboardInterrupt) as exc:
        status.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed", error=str(exc))
        raise
    finally:
        save()
    return status


def verify(config, output):
    study = output / "study"
    summary = json.loads((study / "summary.json").read_text())
    source = study / "source"
    for name, expected in json.loads((study / "source-files.json").read_text()).items():
        if digest(source / name) != expected:
            raise ValueError("Executed source archive differs from receipt.")
    expected = {(b, c, s) for b in range(config["blocks"]) for c in config["cases"] for s in config["seeds"]}
    actual = {(t["block"], t["case"], t["seed"]) for t in summary["trials"]}
    if summary["status"] != "complete" or actual != expected or len(actual) != len(summary["trials"]):
        raise ValueError("Cannot conclude an incomplete matrix.")
    common = None
    receipts = {}
    for trial in summary["trials"]:
        path = study / trial["name"]
        report = json.loads((path / "report.json").read_text())
        cfg = SnapshotConfig.model_validate_json((path / "config.json").read_text())
        expected_cfg = fit_config(
            config,
            output / "snapshots" / f"block-{trial['block']}-{trial['case']}",
            trial["seed"],
            cfg.execution.fit_seconds,
        )
        if cfg != expected_cfg or cfg.execution.fit_seconds > summary["fit_seconds"]:
            raise ValueError("Trial changed a frozen scientific setting or allowance.")
        if report["source"]["source_sha256"] != summary["source"]["source_sha256"]:
            raise ValueError("Trial implementation identity differs from the frozen matrix.")
        data = SnapshotTensors(output / "tensors" / f"block-{trial['block']}-{trial['case']}")
        if data.manifest["fingerprint"] != report["tensor_cache_fingerprint"]:
            raise ValueError("Consumed tensor cache identity differs from the report.")
        expected_rows = {r["input_hash"]: r for r in data.rows()}
        if report["status"] != "complete" or report["completed_updates"] != config["training"]["updates"]:
            raise ValueError("Incomplete update count.")
        if cfg.training.seed != trial["seed"] or cfg.training.chunk_size != config["training"]["chunk_size"]:
            raise ValueError("Trial config changed frozen settings.")
        if digest(path / "policy.pt") != report["checkpoint_sha256"]:
            raise ValueError("Checkpoint receipt mismatch.")
        if digest(path / "predictions.jsonl") != digest(path / "reloaded-predictions.jsonl"):
            raise ValueError("Reload prediction mismatch.")
        cells = {}
        raw_stats = {s: {"positions": 0, "correct": 0, "loss_sum": 0.0} for s in ("train", "validation")}
        keys = set()
        for line in (path / "predictions.jsonl").read_text().splitlines():
            row = json.loads(line)
            source_row = expected_rows.pop(row["input_hash"], None)
            if source_row is None or source_row["split"] != row["split"] or source_row["bucket"] != row["bucket"]:
                raise ValueError("Prediction inputs do not match consumed snapshot rows.")
            if action_id(source_row["move"]) != row["target"]:
                raise ValueError("Prediction target differs from the consumed snapshot label.")
            raw = raw_stats[row["split"]]
            raw["positions"] += 1
            raw["correct"] += int(row["prediction"] == row["target"])
            raw["loss_sum"] += row["loss"]
            if row["split"] == "validation":
                keys.add((row["input_hash"], row["target"], row["bucket"]))
                cells.setdefault(row["bucket"], []).append(row["prediction"] == row["target"])
        if expected_rows:
            raise ValueError("Missing per-input predictions.")
        for split, raw in raw_stats.items():
            for field in ("positions", "correct", "loss_sum"):
                if abs(raw[field] - report["stats"][split][field]) > 1e-8:
                    raise ValueError("Raw metric counts or cross-entropy differ from report.")
        value = statistics.mean(statistics.mean(v) for v in cells.values())
        if len(cells) != 6 or abs(value - trial["primary"]) > 1e-12:
            raise ValueError("Raw primary metric mismatch.")
        if common is not None and keys != common:
            raise ValueError("Development inputs/labels differ between fits.")
        common = keys
        for p in path.iterdir():
            if p.is_file():
                receipts[str(p.relative_to(output))] = digest(p)
    means = {}
    for case in config["cases"]:
        values = [t["primary"] for t in summary["trials"] if t["case"] == case]
        blocks = [
            statistics.mean(t["primary"] for t in summary["trials"] if t["case"] == case and t["block"] == b)
            for b in range(config["blocks"])
        ]
        means[case] = {"mean": statistics.mean(values), "block_means": blocks}
    for row in means.values():
        row["block_deltas"] = [
            a - b for a, b in zip(row["block_means"], means["plausible"]["block_means"], strict=True)
        ]
        row["all_blocks_positive"] = all(v > 0 for v in row["block_deltas"])
    best = max(config["cases"], key=lambda c: means[c]["mean"])
    advanced = best if best != "plausible" and means[best]["all_blocks_positive"] else "plausible"
    result = {
        "status": "verified",
        "complete_fits": len(actual),
        "development_inputs": len(common),
        "cases": means,
        "advance": advanced,
        "interpretation": "exploratory fixed-reference imitation; sealed test unscored",
    }
    write_json(output / "verification.json", result, indent=2)
    write_json(output / "receipts.json", receipts, indent=2)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=["prepare", "run", "verify"], required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    output = args.output.resolve()
    if args.stage != "prepare" and config != json.loads((output / "config.json").read_text()):
        raise ValueError("Submitted study config differs from frozen preparation.")
    collection = (args.config.parent / config["collection"]).resolve()
    result = (
        prepare(config, output, collection)
        if args.stage == "prepare"
        else run(config, output)
        if args.stage == "run"
        else verify(config, output)
    )
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
