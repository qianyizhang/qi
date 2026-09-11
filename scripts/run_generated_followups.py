"""Prepare, execute and verify the two frozen generated-data follow-up studies."""

import argparse
import json
import re
import shutil
import statistics
from collections import Counter
from pathlib import Path
from time import perf_counter

import torch

from qi.artifacts import write_json
from qi.learning.provenance import source_identity
from qi.learning.snapshot import SnapshotConfig, SnapshotTensors, evaluate, prepare_snapshot, train_snapshot
from qi.players.policy.encoding import action_id
from qi.players.policy.runtime import load_checkpoint
from qi.teacher import digest
from qi.training_data.followups import concentration, load_pool
from qi.training_data.semantics import semantic_tags
from qi.training_data.snapshots import SelectionRecipe, SnapshotReader, export_snapshot
from qi.training_data.store import Collection

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def check_frozen(config, root):
    if config["version"] != "generated-followups-v1":
        raise ValueError("Unsupported follow-up protocol.")
    if str((root.resolve() / "pool/manifest.json").relative_to(ROOT)) not in config["frozen_files"]:
        raise ValueError("Output does not match the frozen artifact root.")
    if (
        config["seeds"] != [7, 17, 27]
        or config["chunk_size"] != 256
        or config["semantic"]["updates"] != 200
        or config["semantic"]["percentage_point_increase"] != 10
        or config["scaling"]["sizes"] != [1000, 4000, 16000]
        or config["scaling"]["passes"] != 200
        or config["scaling"]["presentations"] != 800000
    ):
        raise ValueError("Scientific settings do not match this locked protocol version.")
    for name, expected in config["frozen_files"].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f"Frozen input changed: {name}")
    path = root / "config.json"
    if path.exists() and read(path) != config:
        raise ValueError("Submitted configuration differs from this execution.")


def locations(config, root, study, item):
    if study == "semantic" and item["case"] == "natural":
        parent = ROOT / config["parent"]
        name = f"block-{item['block']}-both"
        return parent / "snapshots" / name, parent / "tensors" / name
    dataset = item.get("dataset", item["name"])
    return root / study / "snapshots" / dataset, root / study / "tensors" / dataset


def check_plan(config, root, study):
    """Check intended controls directly from selected identities and training evidence."""
    pool = {r["input"]: r for r in load_pool(root / "pool")}
    plan = read(root / study / "plan/manifest.json")
    expected_names = (
        {f"block-{b}-{c}" for b in range(3) for c in ("natural", "enriched")}
        if study == "semantic"
        else {f"{c}-{n}" for c in ("plausible", "mixed") for n in (1000, 4000, 16000)}
    )
    if len(plan["plans"]) != 6 or {p["name"] for p in plan["plans"]} != expected_names:
        raise ValueError("Dataset matrix differs from the six frozen cases.")
    parent = ROOT / config["parent"]
    development = read(parent / "plan/manifest.json")["development_buckets"]
    all_validation = {k for b in development for k in b["inputs"]}
    sealed = {r["input"] for r in read(parent / "plan/sealed-test-inputs.json")}
    if pool.keys() & (all_validation | sealed):
        raise ValueError("Candidate pool reaches a protected evaluation group.")
    selected, validation, cells = {}, None, {}
    for item in plan["plans"]:
        recipe = SelectionRecipe.model_validate(read(root / study / "plan" / item["recipe"]))
        val = [b.model_dump() for b in recipe.buckets if b.split == "validation"]
        if validation is not None and val != validation:
            raise ValueError("Development recipe varies between cases.")
        validation = val
        if {k for b in val for k in b["inputs"]} != all_validation:
            raise ValueError("Development inputs differ from the original frozen benchmark.")
        keys = [k for b in recipe.buckets if b.split == "train" for k in b.inputs]
        if len(keys) != len(set(keys)) or len(keys) != item["train_inputs"] or not set(keys) <= pool.keys():
            raise ValueError("Invalid training selection identity or count.")
        rows = [pool[k] for k in keys]
        if concentration(rows) != item["concentration"] or concentration(rows)["max_inputs_per_trajectory"] > 8:
            raise ValueError("Source concentration differs from the frozen plan or cap.")
        selected[item["name"]] = set(keys)
        for b in recipe.buckets:
            if b.split != "train":
                continue
            rs = [pool[k] for k in b.inputs]
            policy = b.themes[0].removeprefix("policy:")
            if any(r["policy"] != policy or r["phase"] != b.phases[0] for r in rs):
                raise ValueError("Policy or phase changed within a declared cell.")
            if study == "semantic" and any(r["block"] != item["block"] for r in rs):
                raise ValueError("Semantic cases cross training blocks.")
            expected = (
                (1600 if policy == "plausible" else 200)
                if study == "semantic"
                else int(
                    item["size"] * (1 if item["case"] == "plausible" else 0.8 if policy == "plausible" else 0.1) / 2
                )
            )
            if b.count != expected or len(rs) != expected:
                raise ValueError("A fixed policy/phase quota changed.")
            cells[item["name"], b.id] = rs
    if study == "semantic":
        for block in range(3):
            before, after = f"block-{block}-natural", f"block-{block}-enriched"
            original = read(parent / f"plan/block-{block}-both.json")
            if selected[before] != {k for b in original["buckets"] if b["split"] == "train" for k in b["inputs"]}:
                raise ValueError("Natural control changed from the previous screen.")
            for name, bucket in list(cells):
                if name != before:
                    continue
                old, new = cells[before, bucket], cells[after, bucket]
                if Counter(t for r in old for t in r["trajectories"]) != Counter(
                    t for r in new for t in r["trajectories"]
                ):
                    raise ValueError("Enrichment changes trajectory contributions.")
                increase = sum(bool(r["tags"]) for r in new) - sum(bool(r["tags"]) for r in old)
                if increase * 100 != len(old) * config["semantic"]["percentage_point_increase"]:
                    raise ValueError("Enrichment does not match the frozen per-cell increase.")
            for other in range(block):
                if (selected[before] | selected[after]) & (
                    selected[f"block-{other}-natural"] | selected[f"block-{other}-enriched"]
                ):
                    raise ValueError("Semantic training blocks share selected inputs.")
    else:
        for case in ("plausible", "mixed"):
            if not selected[f"{case}-1000"] < selected[f"{case}-4000"] < selected[f"{case}-16000"]:
                raise ValueError("Scaling inputs are not nested.")
    return plan


def prepare(config, root, study):
    check_frozen(config, root)
    plan = check_plan(config, root, study)
    write_json(root / "config.json", config, indent=2)
    result = {"status": "preparing", "datasets": [], "started_source": source_identity()}
    started = perf_counter()
    for item in plan["plans"]:
        snapshot, cache = locations(config, root, study, item)
        if not snapshot.exists():
            print(f"export {study}/{item['name']}", flush=True)
            with Collection(ROOT / config["collection"], readonly=True) as store:
                recipe = SelectionRecipe.model_validate(read(root / study / "plan" / item["recipe"]))
                t = perf_counter()
                export_snapshot(store, recipe, snapshot)
                print(f"exported in {perf_counter() - t:.1f}s", flush=True)
        if not cache.exists():
            prepare_snapshot(snapshot, cache, chunk_size=config["chunk_size"])
        reader, tensors = SnapshotReader(snapshot), SnapshotTensors(cache)
        expected = SelectionRecipe.model_validate(read(root / study / "plan" / item["recipe"]))
        if reader.recipe != expected or tensors.manifest["snapshot_fingerprint"] != reader.manifest["fingerprint"]:
            raise ValueError("Prepared input does not match the frozen recipe.")
        result["datasets"].append(
            {
                "name": item["name"],
                "snapshot": str(snapshot.resolve()),
                "cache": str(cache.resolve()),
                "snapshot_fingerprint": reader.manifest["fingerprint"],
                "cache_fingerprint": tensors.manifest["fingerprint"],
            }
        )
        result["elapsed_seconds"] = perf_counter() - started
        write_json(root / study / "preparation.json", result, indent=2)
        print(f"ready {study}/{item['name']} ({len(result['datasets'])}/{len(plan['plans'])})", flush=True)
    result["status"] = "complete"
    write_json(root / study / "preparation.json", result, indent=2)
    return result


def trial_plan(config, plan, study):
    trials = []
    for item in plan["plans"]:
        size = item["train_inputs"]
        updates = [200] if study == "semantic" else sorted({200, config["scaling"]["presentations"] // size})
        for count in updates:
            for seed in config["seeds"]:
                trials.append(
                    {
                        **item,
                        "updates": count,
                        "seed": seed,
                        "dataset": item["name"],
                        "name": f"{item['name']}-updates-{count}-seed-{seed}",
                    }
                )
    return trials


def fit_config(config, snapshot, item, seconds):
    return SnapshotConfig.model_validate(
        {
            "data": {"snapshot": str(snapshot.resolve())},
            "training": {"updates": item["updates"], "seed": item["seed"], "chunk_size": config["chunk_size"]},
            "execution": {"device": "cpu", "threads": 1, "fit_seconds": seconds},
        }
    )


def checked_data(config, root, study, item):
    snapshot, cache = locations(config, root, study, item)
    reader, data = SnapshotReader(snapshot), SnapshotTensors(cache)
    prepared = next(p for p in read(root / study / "preparation.json")["datasets"] if p["name"] == item["dataset"])
    expected = SelectionRecipe.model_validate(read(root / study / "plan" / item["recipe"]))
    if (
        reader.recipe != expected
        or prepared["snapshot_fingerprint"] != reader.manifest["fingerprint"]
        or prepared["cache_fingerprint"] != data.manifest["fingerprint"]
        or data.manifest["snapshot_fingerprint"] != reader.manifest["fingerprint"]
    ):
        raise ValueError("Prepared snapshot/cache differs from the frozen selection.")
    return snapshot, reader, data


def primary(stats):
    values = [s["agreement"] for k, s in stats.items() if k.startswith("bucket:development-")]
    if len(values) != 6:
        raise ValueError("Primary requires six development policy/phase cells.")
    return statistics.mean(values)


def prior_attempts(root, study):
    attempts = []
    for path in sorted((root / study).glob("study*/summary.json")):
        previous = read(path)
        if previous["status"] not in ("complete", "failed", "interrupted"):
            raise ValueError("An earlier attempt is not terminal; reconcile its writer before starting another.")
        attempts.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": digest(path),
                "elapsed_seconds": previous["elapsed_seconds"],
                "status": previous["status"],
                "completed_fits": len(previous["trials"]),
            }
        )
    return attempts


def run(config, root, study, *, attempt="study"):
    check_frozen(config, root)
    plan = check_plan(config, root, study)
    if read(root / study / "preparation.json")["status"] != "complete":
        raise ValueError("Preparation incomplete.")
    out = root / study / attempt
    if out.exists():
        raise ValueError("Retain existing scientific execution; do not overwrite or silently resume.")
    if (root / study / "verification.json").exists():
        raise ValueError("This study already has an assessed execution.")
    earlier = prior_attempts(root, study)
    earlier_seconds = sum(a["elapsed_seconds"] for a in earlier)
    previous_seconds = 0.0
    if study == "scaling":
        previous = read(root / "semantic/verification.json")
        if previous["status"] != "verified":
            raise ValueError("Complete and verify semantic screen before scaling fits.")
        previous_seconds = previous["elapsed_seconds"] + previous.get("prior_attempt_seconds", 0)
    out.mkdir()
    source = out / "source"
    shutil.copytree(ROOT / "src/qi", source / "src/qi", ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy2(ROOT / name, source / name)
    shutil.copy2(Path(__file__), source / Path(__file__).name)
    archive = {str(p.relative_to(source)): digest(p) for p in source.rglob("*") if p.is_file()}
    write_json(out / "source-files.json", archive, indent=2)
    trials = trial_plan(config, plan, study)
    write_json(out / "trials.json", trials, indent=2)
    status = {
        "status": "running",
        "study": study,
        "planned_fits": len(trials),
        "trials": [],
        "source": source_identity(),
        "prior_stage_seconds": previous_seconds,
        "prior_attempt_seconds": earlier_seconds,
        "prior_attempts": earlier,
        "attempt": attempt,
    }
    started = perf_counter()

    def save():
        status["elapsed_seconds"] = perf_counter() - started
        write_json(out / "summary.json", status, indent=2)

    def fit(item, path):
        remaining = (
            config["execution"]["total_seconds"] - previous_seconds - earlier_seconds - (perf_counter() - started)
        )
        if remaining <= 0:
            raise ValueError("Combined study allowance exhausted.")
        snapshot, _, data = checked_data(config, root, study, item)
        cfg = fit_config(config, snapshot, item, min(config["execution"]["fit_seconds"], remaining))
        result = train_snapshot(data, cfg, path)
        if result["status"] != "complete":
            raise ValueError("Fit did not complete all requested updates; retain partial study.")
        if result["process_peak_rss_bytes"] > config["execution"]["max_rss_bytes"]:
            raise ValueError("Process peak RSS exceeded the frozen stop threshold.")
        return result

    save()
    try:
        if study == "scaling":
            pilot = next(p for p in plan["plans"] if p["name"] == "mixed-16000")
            status["active_trial"] = "resource-pilot"
            save()
            report = fit({**pilot, "dataset": pilot["name"], "updates": 200, "seed": 917}, out / "resource-pilot")
            status["pilot_seconds"] = report["elapsed_seconds"]
            save()
        for item in trials:
            if source_identity()["source_sha256"] != status["source"]["source_sha256"]:
                raise ValueError("Implementation changed during the matrix.")
            if digest(Path(__file__)) != archive[Path(__file__).name]:
                raise ValueError("Study runner changed during the matrix.")
            status["active_trial"] = item["name"]
            save()
            print(f"fit {study}/{item['name']} ({len(status['trials']) + 1}/{len(trials)})", flush=True)
            report = fit(item, out / item["name"])
            status["trials"].append(
                {
                    "name": item["name"],
                    "primary": primary(report["stats"]),
                    "seconds": report["elapsed_seconds"],
                    "status": report["status"],
                }
            )
            save()
        status.update(status="complete")
        status.pop("active_trial", None)
    except (Exception, KeyboardInterrupt) as exc:
        status.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed", error=str(exc))
        raise
    finally:
        save()
    return status


def assess(trials, study):
    if study == "semantic":
        cases = {}
        for case in ("natural", "enriched"):
            rows = [t for t in trials if t["case"] == case]
            cases[case] = {
                "mean": statistics.mean(t["primary"] for t in rows),
                "block_means": [statistics.mean(t["primary"] for t in rows if t["block"] == b) for b in range(3)],
            }
        deltas = [a - b for a, b in zip(cases["enriched"]["block_means"], cases["natural"]["block_means"], strict=True)]
        return {
            "cases": cases,
            "block_deltas": deltas,
            "advance": "enriched" if all(d > 0 for d in deltas) else "natural",
        }
    curves = {}
    for regime in ("passes", "presentations"):
        curves[regime] = {}
        for case in ("plausible", "mixed"):
            points = {}
            for size in (1000, 4000, 16000):
                updates = 200 if regime == "passes" else 800000 // size
                rows = sorted(
                    [t for t in trials if t["case"] == case and t["size"] == size and t["updates"] == updates],
                    key=lambda t: t["seed"],
                )
                points[str(size)] = {
                    "mean": statistics.mean(t["primary"] for t in rows),
                    "seed_values": [t["primary"] for t in rows],
                    "updates": updates,
                }
            deltas = [a - b for a, b in zip(points["16000"]["seed_values"], points["1000"]["seed_values"], strict=True)]
            curves[regime][case] = {
                "points": points,
                "endpoint_seed_deltas": deltas,
                "supported": all(d > 0 for d in deltas)
                and points["1000"]["mean"] < points["4000"]["mean"] < points["16000"]["mean"],
            }
    return {
        "curves": curves,
        "interpretation": "One nested master pool and initialization seeds; no independent dataset replication.",
    }


def verify(config, root, study, *, attempt="study"):
    check_frozen(config, root)
    plan = check_plan(config, root, study)
    out = root / study / attempt
    summary = read(out / "summary.json")
    trials = trial_plan(config, plan, study)
    if (
        summary["status"] != "complete"
        or read(out / "trials.json") != trials
        or [t["name"] for t in summary["trials"]] != [t["name"] for t in trials]
    ):
        raise ValueError("Incomplete or changed trial matrix.")
    for name, sha in read(out / "source-files.json").items():
        if digest(out / "source" / name) != sha:
            raise ValueError("Source archive changed.")
    for earlier in summary["prior_attempts"]:
        if digest(root / earlier["path"]) != earlier["sha256"]:
            raise ValueError("A charged prior attempt changed after execution started.")
    torch.set_num_threads(1)
    common, results, receipts = None, [], {}
    verify_dir = out / "independent-verification"
    if verify_dir.exists():
        raise ValueError("Independent verification output already exists; preserve it.")
    verify_dir.mkdir()
    for item, saved in zip(trials, summary["trials"], strict=True):
        path = out / item["name"]
        snapshot, reader, data = checked_data(config, root, study, item)
        report, cfg = read(path / "report.json"), SnapshotConfig.model_validate(read(path / "config.json"))
        if (
            cfg != fit_config(config, snapshot, item, cfg.execution.fit_seconds)
            or cfg.execution.fit_seconds > config["execution"]["fit_seconds"]
        ):
            raise ValueError("Fit scientific configuration differs from protocol.")
        if (
            report["status"] != "complete"
            or report["completed_updates"] != item["updates"]
            or report["source"]["source_sha256"] != summary["source"]["source_sha256"]
        ):
            raise ValueError("Fit status, update count or implementation mismatch.")
        if (
            report["tensor_cache_fingerprint"] != data.manifest["fingerprint"]
            or report["snapshot_fingerprint"] != reader.manifest["fingerprint"]
        ):
            raise ValueError("Fit consumed different data.")
        rows = list(data.rows())
        keys = {(r["input_hash"], r["move"], r["bucket"]) for r in rows if r["split"] == "validation"}
        if common is not None and keys != common:
            raise ValueError("Shared development labels changed.")
        common = keys
        lookup = {r["input_hash"]: r for r in rows}
        for line in (path / "predictions.jsonl").read_text().splitlines():
            pred = json.loads(line)
            row = lookup.pop(pred["input_hash"], None)
            if (
                row is None
                or pred["target"] != action_id(row["move"])
                or pred["split"] != row["split"]
                or pred["bucket"] != row["bucket"]
            ):
                raise ValueError("Prediction identity or target mismatch.")
            if row["semantic_tags"] != semantic_tags(row["board"], row["turn"], row["move"]):
                raise ValueError("Semantic feature derivation changed.")
        if lookup:
            raise ValueError("Predictions do not cover consumed rows.")
        loaded = load_checkpoint(str((path / "policy.pt").resolve()), digest(path / "policy.pt"))
        if loaded.sha256 != report["checkpoint_sha256"] or loaded.metadata.steps != item["updates"]:
            raise ValueError("Checkpoint metadata mismatch.")
        if (
            set(loaded.metadata.train_inputs) != {r["input_hash"] for r in rows if r["split"] == "train"}
            or set(loaded.metadata.validation_inputs) != {r["input_hash"] for r in rows if r["split"] == "validation"}
            or loaded.metadata.seed != item["seed"]
            or loaded.metadata.training_protocol != cfg.training.batching
        ):
            raise ValueError("Checkpoint selection or training protocol differs from the fit.")
        predictions = verify_dir / f"{item['name']}.jsonl"
        stats = evaluate(loaded.model, data, predictions, chunk_size=config["chunk_size"])
        if (
            stats != report["stats"]
            or digest(predictions) != digest(path / "predictions.jsonl")
            or digest(predictions) != digest(path / "reloaded-predictions.jsonl")
        ):
            raise ValueError("Independently reloaded predictions or metrics differ.")
        score = primary(stats)
        if score != saved["primary"]:
            raise ValueError("Primary score arithmetic mismatch.")
        old_equal = None
        if study == "semantic" and item["case"] == "natural":
            old = ROOT / config["parent"] / f"study/block-{item['block']}-both-seed-{item['seed']}/predictions.jsonl"
            old_equal = digest(old) == digest(predictions)
            if not old_equal:
                raise ValueError("Natural-control predictions differ from the completed parent screen.")
        results.append(
            {
                **{k: v for k, v in item.items() if k not in ("recipe", "concentration")},
                "primary": score,
                "stats": stats,
                "seconds": report["elapsed_seconds"],
                "peak_rss_bytes": report["process_peak_rss_bytes"],
                "parent_predictions_equal": old_equal,
            }
        )
        for p in path.iterdir():
            if p.is_file():
                receipts[str(p.relative_to(root))] = digest(p)
        print(f"verified {study}/{item['name']} ({len(results)}/{len(trials)})", flush=True)
    if study == "scaling":
        pilot = out / "resource-pilot"
        report = read(pilot / "report.json")
        if report["status"] != "complete" or report["completed_updates"] != 200:
            raise ValueError("Largest-size resource pilot was incomplete.")
        for p in pilot.iterdir():
            if p.is_file():
                receipts[str(p.relative_to(root))] = digest(p)
    for earlier in summary["prior_attempts"]:
        for p in (root / earlier["path"]).parent.rglob("*"):
            if p.is_file():
                receipts[str(p.relative_to(root))] = digest(p)
    result = {
        "status": "verified",
        "study": study,
        "complete_fits": len(results),
        "development_inputs": len(common),
        "sealed_test_scored": False,
        "assessment": assess(results, study),
        "trials": results,
        "source": summary["source"],
        "elapsed_seconds": summary["elapsed_seconds"],
        "prior_stage_seconds": summary["prior_stage_seconds"],
        "prior_attempt_seconds": summary["prior_attempt_seconds"],
        "prior_attempts": summary["prior_attempts"],
        "execution_dir": str(out.relative_to(root)),
    }
    write_json(root / study / "verification.json", result, indent=2)
    write_json(root / study / "receipts.json", receipts, indent=2)
    return {k: v for k, v in result.items() if k != "trials"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--study", choices=("semantic", "scaling"), required=True)
    parser.add_argument("--stage", choices=("prepare", "run", "verify"), required=True)
    parser.add_argument(
        "--attempt", default="study", help="Fresh operational attempt name; earlier attempts stay in place."
    )
    args = parser.parse_args()
    if not re.fullmatch(r"study(?:-[a-z0-9]+)*", args.attempt):
        parser.error("Attempt names must be study or study- followed by lowercase words/numbers.")
    config = read(args.config)
    result = (
        prepare(config, args.output.resolve(), args.study)
        if args.stage == "prepare"
        else {"run": run, "verify": verify}[args.stage](config, args.output.resolve(), args.study, attempt=args.attempt)
    )
    print(json.dumps({k: v for k, v in result.items() if k not in ("datasets", "trials")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
