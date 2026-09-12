"""Bounded study runner using the existing frozen tensors and full-batch update.

This is an exploratory artifact runner, not a production checkpoint format.
Verification is a separate CLI invocation and reloads every saved checkpoint.
"""

import argparse
import json
import math
import os
import platform
import resource
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import torch
from models import CASES, make_case, model_description

from qi.artifacts import write_json
from qi.game import Game
from qi.learning.provenance import source_identity
from qi.learning.snapshot import SnapshotTensors, accumulated_step
from qi.players.policy.encoding import input_key
from qi.teacher import digest

ROOT = Path(__file__).resolve().parents[4]
SCHEMA = "architecture-surfaces-study-v1"


def now():
    return datetime.now(timezone.utc).isoformat()


def peak_rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)


def read_json(path):
    return json.loads(Path(path).read_text())


class BudgetStop(RuntimeError):
    pass


def budget_check(config, deadline=None):
    if peak_rss() > config["execution"]["max_rss_bytes"]:
        raise BudgetStop("process_peak_rss_limit")
    if deadline is not None and perf_counter() >= deadline:
        raise BudgetStop("deadline")


def checked_batches(data, split, chunk_size, config, deadline=None):
    for batch in data.batches(split, chunk_size):
        budget_check(config, deadline)
        yield batch


def load_config(path):
    config = read_json(path)
    if not config["cases"] or len(set(config["cases"])) != len(config["cases"]) or set(config["cases"]) - set(CASES):
        raise ValueError("Cases must be distinct study case names.")
    if not config["seeds"] or len(set(config["seeds"])) != len(config["seeds"]):
        raise ValueError("Seeds must be nonempty and distinct.")
    if any(type(seed) is not int or seed < 0 or seed >= 2**63 for seed in config["seeds"]):
        raise ValueError("Invalid seed.")
    updates = config["checkpoints"]
    if not updates or sorted(set(updates)) != updates or any(type(u) is not int or not 1 <= u <= 2000 for u in updates):
        raise ValueError("Checkpoints must be sorted unique positive updates, at most 2000.")
    execution = config["execution"]
    if execution["threads"] != 1:
        raise ValueError("This study fixes CPU threads to one.")
    if not 0 < execution["fit_seconds"] <= 600 or not 0 < execution["total_seconds"] <= 1800:
        raise ValueError("Study exceeds the bounded fit/matrix allowance.")
    if not 0 < execution["max_rss_bytes"] <= 1_500_000_000:
        raise ValueError("Study exceeds the process RSS allowance.")
    if not 0 < config["optimizer"]["learning_rate"] <= 1:
        raise ValueError("Invalid learning rate.")
    chunk_size = config.get("training", {}).get("chunk_size", 256)
    if type(chunk_size) is not int or not 1 <= chunk_size <= 4096:
        raise ValueError("Invalid chunk size.")
    config.setdefault("training", {})["chunk_size"] = chunk_size
    return config


def validate_data(config):
    path = Path(config["data"]["cache"])
    if digest(path / "manifest.json") != config["data"]["manifest_sha256"]:
        raise ValueError("Frozen tensor manifest hash mismatch.")
    sealed_path = Path(config["data"]["sealed_inputs"])
    if digest(sealed_path) != config["data"]["sealed_sha256"]:
        raise ValueError("Sealed input identity file hash mismatch.")
    sealed = read_json(sealed_path)
    if isinstance(sealed, dict):
        sealed = sealed["inputs"]
    if isinstance(sealed, list) and sealed and isinstance(sealed[0], dict):
        sealed = [row["input"] for row in sealed]
    if not isinstance(sealed, list) or not all(isinstance(x, str) and len(x) == 64 for x in sealed):
        raise ValueError("Sealed identities must be a list of input hashes.")
    if len(set(sealed)) != len(sealed):
        raise ValueError("Duplicate sealed identities.")
    sealed = set(sealed)
    data = SnapshotTensors(path)
    exact, canonical = defaultdict(set), defaultdict(set)
    counts = defaultdict(int)
    sealed_hits, canonical_sealed_hits = [], []
    for row in data.rows():
        split = row["split"]
        if split not in ("train", "validation"):
            raise ValueError("Study cache must contain only train and validation.")
        game = Game(board=row["board"], turn=row["turn"])
        identity = input_key(game)
        if identity != row["input_hash"]:
            raise ValueError("Row input hash differs from its board and turn.")
        equivalent = input_key(Game(board=game.board[::-1].swapcase(), turn="black" if game.turn == "red" else "red"))
        canonical[split].add(min(identity, equivalent))
        if identity in exact[split]:
            raise ValueError("Duplicate exact input within a split.")
        exact[split].add(identity)
        counts[split] += 1
        if identity in sealed:
            sealed_hits.append(identity)
        if equivalent in sealed:
            canonical_sealed_hits.append(identity)
    if dict(counts) != data.manifest["counts"] or sum(counts.values()) != data.manifest["rows"]:
        raise ValueError("Rows differ from frozen split counts.")
    exact_overlap = exact["train"] & exact["validation"]
    canonical_overlap = canonical["train"] & canonical["validation"]
    if exact_overlap or canonical_overlap or sealed_hits or canonical_sealed_hits:
        raise ValueError(
            "Input isolation failure: "
            f"exact_train_dev={len(exact_overlap)}, canonical_train_dev={len(canonical_overlap)}, "
            f"sealed={len(sealed_hits)}, canonical_sealed={len(canonical_sealed_hits)}"
        )
    return data, {
        "counts": dict(counts),
        "sealed_input_identities": len(sealed),
        "exact_train_dev_overlap": 0,
        "canonical_train_dev_overlap": 0,
        "sealed_overlap": 0,
        "canonical_sealed_overlap": 0,
        "canonical_unique_by_split": {split: len(keys) for split, keys in canonical.items()},
        "tensor_fingerprint": data.manifest["fingerprint"],
        "snapshot_fingerprint": data.manifest["snapshot_fingerprint"],
        "supervision": data.manifest["supervision"],
    }


def source_paths():
    paths = list((ROOT / "src/qi").rglob("*.py"))
    paths += [ROOT / "uv.lock", ROOT / "pyproject.toml"]
    paths += [Path(__file__).parent / name for name in ("run.py", "models.py", "test_study.py")]
    return sorted(paths)


def preserve_lineage(config_path, output):
    records = {}
    for path in source_paths():
        relative = path.relative_to(ROOT)
        archived = output / "lineage" / relative
        archived.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, archived)
        records[str(relative)] = digest(archived)
        if records[str(relative)] != digest(path):
            raise ValueError("Source changed during archival.")
    shutil.copy2(config_path, output / "submitted-config.json")
    lineage = {
        "timestamp": now(),
        "source": source_identity(),
        "submitted_config_sha256": digest(config_path),
        "files": records,
        "python": sys.version,
        "torch": str(torch.__version__),
        "platform": platform.platform(),
        "pid": os.getpid(),
    }
    write_json(output / "lineage.json", lineage, indent=2)
    return lineage


def check_lineage(output, *, current=True):
    lineage = read_json(output / "lineage.json")
    if digest(output / "submitted-config.json") != lineage["submitted_config_sha256"]:
        raise ValueError("Submitted config archive changed.")
    for name, expected in lineage["files"].items():
        if digest(output / "lineage" / name) != expected:
            raise ValueError(f"Archived source changed: {name}")
        if current and digest(ROOT / name) != expected:
            raise ValueError(f"Current source differs from frozen run: {name}")
    return lineage


def empty_stats():
    return {
        "positions": 0,
        "correct": 0,
        "top3_correct": 0,
        "legal_outputs": 0,
        "unmasked_legal_outputs": 0,
        "loss_sum": 0.0,
        "confidence_sum": 0.0,
        "entropy_sum": 0.0,
        "uniform_loss_sum": 0.0,
        "legal_count_sum": 0,
        "loss_temperature2_sum": 0.0,
        "confidence_temperature2_sum": 0.0,
    }


def evaluate_case(model, data, output, config, *, deadline=None):
    """Keep per-input dev observations and matched train/cohort aggregates."""
    stats = defaultdict(empty_stats)
    model.eval()
    with output.open("x") as stream, torch.inference_mode():
        for rows, (features, mask, targets) in checked_batches(
            data, None, config["training"]["chunk_size"], config, deadline
        ):
            raw_logits = model(features)
            if not torch.isfinite(raw_logits).all():
                raise ValueError("Nonfinite model logits.")
            logits = raw_logits.masked_fill(~mask, -torch.inf)
            losses = torch.nn.functional.cross_entropy(logits, targets, reduction="none")
            if not torch.isfinite(losses).all():
                raise ValueError("Nonfinite evaluation losses.")
            log_probs = logits.log_softmax(dim=1)
            probs = log_probs.exp()
            entropy = -(probs * log_probs.masked_fill(~mask, 0.0)).sum(dim=1)
            confidence, predictions = probs.max(dim=1)
            losses_temperature2 = torch.nn.functional.cross_entropy(logits / 2.0, targets, reduction="none")
            confidence_temperature2 = (logits / 2.0).softmax(dim=1).max(dim=1).values
            ranks = probs.topk(3, dim=1).indices
            unmasked_predictions = raw_logits.argmax(dim=1)
            for i, row in enumerate(rows):
                target, prediction = int(targets[i]), int(predictions[i])
                legal_count = int(mask[i].sum())
                top3 = [int(x) for x in ranks[i] if bool(mask[i, x])]
                raw = {
                    "ordinal": row["ordinal"],
                    "input_hash": row["input_hash"],
                    "split": row["split"],
                    "bucket": row["bucket"],
                    "phase": row["phase"],
                    "turn": row["turn"],
                    "semantic_tags": row["semantic_tags"],
                    "target": target,
                    "prediction": prediction,
                    "loss": float(losses[i]),
                    "confidence": float(confidence[i]),
                    "loss_temperature2": float(losses_temperature2[i]),
                    "confidence_temperature2": float(confidence_temperature2[i]),
                    "entropy": float(entropy[i]),
                    "top3": top3,
                    "legal_count": legal_count,
                    "unmasked_prediction": int(unmasked_predictions[i]),
                    "unmasked_prediction_legal": bool(mask[i, unmasked_predictions[i]]),
                    "legal_output": bool(mask[i, prediction]),
                }
                groups = [row["split"], f"{row['split']}:bucket:{row['bucket']}"]
                groups += [f"{row['split']}:phase:{row['phase']}", f"{row['split']}:turn:{row['turn']}"]
                groups += [f"{row['split']}:tag:{tag}" for tag in row["semantic_tags"]]
                for group in groups:
                    stat = stats[group]
                    stat["positions"] += 1
                    stat["correct"] += int(prediction == target)
                    stat["top3_correct"] += int(target in top3)
                    stat["legal_outputs"] += int(raw["legal_output"])
                    stat["unmasked_legal_outputs"] += int(raw["unmasked_prediction_legal"])
                    stat["loss_sum"] += raw["loss"]
                    stat["confidence_sum"] += raw["confidence"]
                    stat["loss_temperature2_sum"] += raw["loss_temperature2"]
                    stat["confidence_temperature2_sum"] += raw["confidence_temperature2"]
                    stat["entropy_sum"] += raw["entropy"]
                    stat["uniform_loss_sum"] += math.log(legal_count)
                    stat["legal_count_sum"] += legal_count
                if row["split"] == "validation":
                    stream.write(json.dumps(raw, sort_keys=True) + "\n")
    for stat in stats.values():
        n = stat["positions"]
        stat.update(
            agreement=stat["correct"] / n,
            top3_agreement=stat["top3_correct"] / n,
            cross_entropy=stat["loss_sum"] / n,
            mean_confidence=stat["confidence_sum"] / n,
            mean_entropy=stat["entropy_sum"] / n,
            uniform_cross_entropy=stat["uniform_loss_sum"] / n,
            mean_legal_count=stat["legal_count_sum"] / n,
            cross_entropy_temperature2=stat["loss_temperature2_sum"] / n,
            mean_confidence_temperature2=stat["confidence_temperature2_sum"] / n,
        )
    return dict(stats)


def save_checkpoint(model, case, seed, update, fit_path, data, config, deadline):
    path = fit_path / f"checkpoint-{update:04d}"
    path.mkdir()
    metadata = {"schema": SCHEMA, "case": case, "seed": seed, "update": update}
    with (path / "model.pt").open("xb") as stream:
        torch.save({"study": metadata, "state_dict": model.state_dict()}, stream)
    checkpoint_identity = {**metadata, "checkpoint_sha256": digest(path / "model.pt")}
    write_json(path / "checkpoint.json", checkpoint_identity, indent=2)
    stats = evaluate_case(model, data, path / "dev-predictions.jsonl", config, deadline=deadline)
    observation = {
        **checkpoint_identity,
        "stats": stats,
        "dev_predictions_sha256": digest(path / "dev-predictions.jsonl"),
        "timestamp": now(),
    }
    write_json(path / "observation.json", observation, indent=2)
    model.train()
    return observation


def fit(case, seed, config, data, output, total_deadline):
    path = output / "fits" / f"{case}-seed-{seed}"
    path.mkdir(parents=True)
    report = {
        "case": case,
        "seed": seed,
        "status": "running",
        "started": now(),
        "completed_updates": 0,
        "observations": [],
        "model": model_description(case),
        "update_losses": [],
    }
    write_json(path / "config.json", {**config, "case": case, "seed": seed}, indent=2)
    started = perf_counter()
    cpu_started = resource.getrusage(resource.RUSAGE_SELF)
    deadline = min(total_deadline, started + config["execution"]["fit_seconds"])
    optimization_seconds = 0.0
    try:
        budget_check(config, deadline)
        torch.manual_seed(seed)
        model = make_case(case)
        optimizer = torch.optim.Adam(model.parameters(), lr=config["optimizer"]["learning_rate"])
        model.train()
        for update in range(1, max(config["checkpoints"]) + 1):
            step_started = perf_counter()
            loss = accumulated_step(
                model,
                optimizer,
                checked_batches(data, "train", config["training"]["chunk_size"], config, deadline),
                data.manifest["counts"]["train"],
                deadline=deadline,
                device="cpu",
            )
            optimization_seconds += perf_counter() - step_started
            if loss is None:
                raise BudgetStop("deadline_during_incomplete_update")
            report["completed_updates"] = update
            report["update_losses"].append(loss)
            if update in config["checkpoints"]:
                observation = save_checkpoint(model, case, seed, update, path, data, config, deadline)
                report["observations"].append(update)
                print(
                    json.dumps(
                        {
                            "event": "checkpoint",
                            "case": case,
                            "seed": seed,
                            "update": update,
                            "validation": observation["stats"]["validation"],
                        }
                    ),
                    flush=True,
                )
            if update % 10 == 0 or update in config["checkpoints"]:
                report["elapsed_seconds"] = perf_counter() - started
                write_json(path / "report.json", report, indent=2)
        report["status"] = "complete"
    except BudgetStop as exc:
        report.update(status="budget_incomplete", reason=str(exc))
    except (Exception, KeyboardInterrupt) as exc:
        report.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed", error=repr(exc))
        raise
    finally:
        cpu_end = resource.getrusage(resource.RUSAGE_SELF)
        report.update(
            finished=now(),
            elapsed_seconds=perf_counter() - started,
            optimization_seconds=optimization_seconds,
            cpu_user_seconds=cpu_end.ru_utime - cpu_started.ru_utime,
            cpu_system_seconds=cpu_end.ru_stime - cpu_started.ru_stime,
            process_peak_rss_bytes=peak_rss(),
            memory_scope="Process lifetime high-water RSS, including imports and previous fits.",
        )
        write_json(path / "report.json", report, indent=2)
    return report


def preview(config):
    started = perf_counter()
    data, validation = validate_data(config)
    return {
        "schema": SCHEMA,
        "status": "preview_validated",
        "data": validation,
        "cases": {name: model_description(name) for name in config["cases"]},
        "fits": len(config["cases"]) * len(config["seeds"]),
        "checkpoint_observations": len(config["cases"]) * len(config["seeds"]) * len(config["checkpoints"]),
        "checkpoints_are_same_fit": True,
        "device": "cpu",
        "optimizer": "Adam",
        "batching": "snapshot-full-batch-v1",
        "execution": config["execution"],
        "rows": data.manifest["rows"],
        "elapsed_seconds": perf_counter() - started,
        "process_peak_rss_bytes": peak_rss(),
    }


def run(config, config_path, output):
    if output.exists():
        raise ValueError("Choose a fresh output directory; runs are never overwritten or silently resumed.")
    output.mkdir(parents=True)
    started = perf_counter()
    report = {"schema": SCHEMA, "status": "preparing", "started": now(), "fits": []}
    write_json(output / "config.json", config, indent=2)
    write_json(output / "report.json", report, indent=2)
    before_threads = torch.get_num_threads()
    try:
        torch.set_num_threads(config["execution"]["threads"])
        preserve_lineage(config_path, output)
        data, validation = validate_data(config)
        report.update(status="running", data=validation)
        deadline = started + config["execution"]["total_seconds"]
        # Seed-major order interleaves the model families under the shared wall-clock cap.
        for seed in config["seeds"]:
            for case in config["cases"]:
                budget_check(config, deadline)
                check_lineage(output)
                result = fit(case, seed, config, data, output, deadline)
                report["fits"].append(result)
                report["elapsed_seconds"] = perf_counter() - started
                write_json(output / "report.json", report, indent=2)
        report["status"] = (
            "complete" if all(result["status"] == "complete" for result in report["fits"]) else "budget_incomplete"
        )
    except BudgetStop as exc:
        report.update(status="budget_incomplete", reason=str(exc))
    except (Exception, KeyboardInterrupt) as exc:
        report.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed", error=repr(exc))
        raise
    finally:
        torch.set_num_threads(before_threads)
        # A raised fit still owns a durable failure/partial report and belongs in the matrix receipt.
        report["fits"] = [read_json(path) for path in sorted((output / "fits").glob("*/report.json"))]
        report.update(
            finished=now(),
            elapsed_seconds=perf_counter() - started,
            process_peak_rss_bytes=peak_rss(),
            requested_fits=len(config["cases"]) * len(config["seeds"]),
            completed_fits=sum(f["status"] == "complete" for f in report["fits"]),
        )
        write_json(output / "report.json", report, indent=2)
    return report


def load_study_checkpoint(path, observation):
    if digest(path) != observation["checkpoint_sha256"]:
        raise ValueError("Checkpoint content hash mismatch.")
    payload = torch.load(path, map_location="cpu", weights_only=True)
    expected_meta = {key: observation[key] for key in ("schema", "case", "seed", "update")}
    if set(payload) != {"study", "state_dict"} or payload["study"] != expected_meta:
        raise ValueError("Checkpoint study metadata mismatch.")
    model = make_case(observation["case"])
    expected = model.state_dict()
    actual = payload["state_dict"]
    if set(actual) != set(expected):
        raise ValueError("Checkpoint parameters mismatch.")
    for key, value in actual.items():
        if value.shape != expected[key].shape or value.dtype != torch.float32 or not torch.isfinite(value).all():
            raise ValueError(f"Invalid checkpoint tensor: {key}")
    model.load_state_dict(actual, strict=True)
    return model.eval()


def verify(config, output):
    started = perf_counter()
    verification = {"schema": SCHEMA, "status": "verifying", "started": now(), "pid": os.getpid(), "checkpoints": []}
    before_threads = torch.get_num_threads()
    verification_path = output / f"verification-{os.getpid()}.json"
    try:
        torch.set_num_threads(1)
        lineage = check_lineage(output)
        if lineage["pid"] == os.getpid():
            raise ValueError("Verification must run in a fresh process.")
        if config != read_json(output / "config.json"):
            raise ValueError("Verification config differs from saved resolved config.")
        data, validation = validate_data(config)
        verification["data"] = validation
        report = read_json(output / "report.json")
        for fit_path in sorted((output / "fits").iterdir()):
            fit_report = read_json(fit_path / "report.json")
            for checkpoint in sorted(fit_path.glob("checkpoint-*")):
                if not (checkpoint / "observation.json").exists():
                    identity = read_json(checkpoint / "checkpoint.json")
                    model = load_study_checkpoint(checkpoint / "model.pt", identity)
                    reloaded_path = checkpoint / f"verified-dev-{os.getpid()}.jsonl"
                    stats = evaluate_case(model, data, reloaded_path, config)
                    verification["checkpoints"].append(
                        {"path": str(checkpoint), "status": "reloaded_incomplete_observation", "stats": stats}
                    )
                    continue
                observation = read_json(checkpoint / "observation.json")
                if observation["update"] not in fit_report["observations"]:
                    raise ValueError("Observation absent from fit report.")
                model = load_study_checkpoint(checkpoint / "model.pt", observation)
                if digest(checkpoint / "dev-predictions.jsonl") != observation["dev_predictions_sha256"]:
                    raise ValueError("Saved prediction hash mismatch.")
                reloaded_path = checkpoint / f"verified-dev-{os.getpid()}.jsonl"
                stats = evaluate_case(model, data, reloaded_path, config)
                if stats != observation["stats"] or digest(reloaded_path) != observation["dev_predictions_sha256"]:
                    raise ValueError("Fresh-process checkpoint predictions or statistics differ.")
                verification["checkpoints"].append(
                    {
                        "path": str(checkpoint),
                        "status": "exact_reload_equal",
                        "checkpoint_sha256": digest(checkpoint / "model.pt"),
                    }
                )
        expected = sum(len(fit["observations"]) for fit in report["fits"])
        exact = sum(item["status"] == "exact_reload_equal" for item in verification["checkpoints"])
        if expected != exact:
            raise ValueError("Matrix report and verified observation counts differ.")
        verification.update(status="verified", verified_observations=exact, source_run_status=report["status"])
    except (Exception, KeyboardInterrupt) as exc:
        verification.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed", error=repr(exc))
        raise
    finally:
        torch.set_num_threads(before_threads)
        verification.update(finished=now(), elapsed_seconds=perf_counter() - started, process_peak_rss_bytes=peak_rss())
        write_json(verification_path, verification, indent=2)
    return verification


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", choices=("preview", "run", "verify"), required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    if args.stage == "preview":
        result = preview(config)
    elif args.stage == "run":
        result = run(config, args.config, args.output)
    else:
        result = verify(config, args.output)
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
