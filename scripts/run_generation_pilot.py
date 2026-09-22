"""Freeze and execute one bounded policy-generation recipe into a SQLite collection."""

import argparse
import json
import resource
import shutil
import sys
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from qi.artifacts import provenance, write_json
from qi.teacher import digest
from qi.training_data.generation_runner import PolicyGenerationConfig, SessionProvider, generate_policies, pin_teachers
from qi.training_data.resource_probe import ResourceProbe, enforce_resources
from qi.training_data.snapshots import SelectionRecipe, SnapshotReader, export_snapshot, verify_snapshot
from qi.training_data.store import Collection


def main():
    began = perf_counter()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--workers", type=int, choices=(1, 2), default=1, help="Opt-in two-worker generation; serial by default"
    )
    parser.add_argument(
        "--collection",
        type=Path,
        help="Existing collection for generated parent lineage; default OUTPUT/collection.sqlite",
    )
    parser.add_argument(
        "--resume", action="store_true", help="Reuse the exact frozen recipe; preserve prior executions"
    )
    parser.add_argument(
        "--continue-from-run",
        type=int,
        help="Explicitly adopt disposed work from an inactive original run with the identical recipe",
    )
    parser.add_argument(
        "--preview", action="store_true", help="Validate config and pinned assets without generation or writes"
    )
    parser.add_argument(
        "--export-recipe", type=Path, help="Explicit selected-only SQL recipe; output is an immutable snapshot"
    )
    parser.add_argument(
        "--max-write-gb", type=float, help="Stop at game boundaries after this many OS-attributed GB written"
    )
    parser.add_argument(
        "--max-rss-mb", type=float, help="Stop when sampled runner plus teacher RSS reaches this many MB"
    )
    parser.add_argument("--min-free-gb", type=float, help="Keep this many GB of free disk space")
    args = parser.parse_args()
    values = (args.max_write_gb, args.max_rss_mb, args.min_free_gb)
    if any(value is not None and (not 0 < value < float("inf")) for value in values):
        parser.error("Resource limits must be finite and positive.")
    limits = {
        name: int(value * scale)
        for name, value, scale in (
            ("max_write_bytes", args.max_write_gb, 1e9),
            ("max_rss_bytes", args.max_rss_mb, 1e6),
            ("min_free_bytes", args.min_free_gb, 1e9),
        )
        if value is not None
    }
    config = PolicyGenerationConfig.model_validate_json(args.config.read_text()).resolve(args.config.resolve().parent)
    identities = pin_teachers(config)
    export = SelectionRecipe.model_validate_json(args.export_recipe.read_text()) if args.export_recipe else None
    if export and (not export.selected_only or export.reserved_corpus != config.corpus):
        parser.error("Policy exports require selected_only=true and the same frozen exclusion corpus.")
    if args.workers == 2:
        from qi.training_data.parallel_generation import run_parallel, validate_parallel

        if args.collection is not None or args.continue_from_run is not None:
            parser.error(
                "Parallel generation owns a fresh output collection; "
                "external collections/continuation use serial execution."
            )
        validate_parallel(config, limits)
        if args.preview:
            print(
                json.dumps(
                    {
                        "config": config.model_dump(),
                        "workers": 2,
                        "shards": len(config.sources),
                        "resource_limits": limits,
                    },
                    indent=2,
                )
            )
        else:
            print(json.dumps(run_parallel(config, args.output, resume=args.resume, export=export, limits=limits)))
        return
    if args.continue_from_run is not None:
        from qi.training_data.generation_io import CollectionIO

        with Collection((args.collection or args.output / "collection.sqlite").resolve(), readonly=True) as store:
            inherited = CollectionIO(store).continuation(args.continue_from_run, config.model_dump())
    else:
        inherited = {}
    if args.preview:
        print(
            json.dumps(
                {"config": config.model_dump(), "resource_limits": limits, "inherited_games": inherited}, indent=2
            )
        )
        return
    collection = (args.collection or args.output / "collection.sqlite").resolve()
    frozen = {
        "config": config.model_dump(),
        "collection": str(collection),
        "export": export.model_dump() if export else None,
    }
    if args.continue_from_run is not None:
        frozen["continued_from_run"] = args.continue_from_run
        frozen["inherited_games"] = inherited
    if limits:
        frozen["resource_limits"] = limits
    if args.resume:
        if json.loads((args.output / "frozen.json").read_text()) != frozen:
            parser.error("Resume requires the exact frozen config, collection and export recipe.")
    else:
        args.output.mkdir(parents=True, exist_ok=False)
        write_json(args.output / "frozen.json", frozen, indent=2)
    execution = args.output / "executions" / uuid4().hex
    execution.mkdir(parents=True)
    source = execution / "source"
    root = Path(__file__).resolve().parents[1]
    before = provenance()
    files = [
        *sorted((root / "src/qi").rglob("*.py")),
        Path(__file__).resolve(),
        root / "pyproject.toml",
        root / "uv.lock",
    ]
    hashes = {}
    for path in files:
        relative = path.relative_to(root)
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        hashes[str(relative)] = digest(target)
    write_json(execution / "provenance.json", {"runtime": before, "source_files": hashes}, indent=2)
    if before["source_sha256"] != provenance()["source_sha256"]:
        raise ValueError("Source changed while archiving; keep this attempt and retry after writers settle.")
    started = perf_counter()
    summary = {"status": "failed", "collection": str(collection)}
    probe = ResourceProbe(collection)
    try:
        enforce_resources(probe.snapshot(), limits, shutil.disk_usage(collection.parent).free)
        with (
            (execution / "events.jsonl").open("x") as events,
            Collection(collection) as store,
            SessionProvider(identities) as provider,
        ):

            def event(value):
                events.write(json.dumps(value) + "\n")
                events.flush()
                if value["kind"] in {"completed-game", "reused-game", "rejected-game", "reused-rejection"}:
                    result = value["result"]
                    pids = [session.engine.process.pid for session in provider.sessions.values() if session.engine]
                    sample = probe.snapshot(pids)
                    write_json(
                        execution / "progress.json",
                        {
                            "game_id": value["game_id"],
                            "source": result["source"],
                            "index": result["index"],
                            "sampling": result["sampling"],
                            "resource": sample,
                        },
                        indent=2,
                    )
                    enforce_resources(sample, limits, shutil.disk_usage(collection.parent).free)
                    print(
                        json.dumps(
                            {
                                "kind": value["kind"],
                                "source": result["source"],
                                "game": result["index"],
                                "selected": result["sampling"]["actual"],
                                "shortfall": result["sampling"]["shortfall"],
                            }
                        ),
                        flush=True,
                    )

            summary = generate_policies(
                store, config, provider=provider, event=event, continue_from_run=args.continue_from_run
            )
            if export:
                tick = perf_counter()
                destination = execution / "snapshot"
                manifest = export_snapshot(store, export, destination)
                summary["export_seconds"] = perf_counter() - tick
                tick = perf_counter()
                verify_snapshot(destination)
                rows = sum(len(batch) for batch in SnapshotReader(destination).batches(128))
                summary["snapshot"] = {
                    "path": str(destination),
                    "rows": manifest["rows"],
                    "read_rows": rows,
                    "verify_read_seconds": perf_counter() - tick,
                }
    except BaseException as exc:
        summary.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        summary["generation_export_seconds"] = perf_counter() - started
        summary["preflight_archive_seconds"] = started - began
        summary["end_to_end_seconds"] = perf_counter() - began
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        summary["peak_rss_bytes"] = rss if sys.platform == "darwin" else rss * 1024
        summary["collection_disk_bytes"] = sum(
            p.stat().st_size for p in collection.parent.glob(collection.name + "*") if p.is_file()
        )
        summary["execution_disk_bytes"] = sum(p.stat().st_size for p in execution.rglob("*") if p.is_file())
        summary["resources"] = probe.snapshot()
        summary["resource_limits"] = limits
        summary["source_sha256"] = before["source_sha256"]
        summary["source_changed_during_run"] = provenance()["source_sha256"] != before["source_sha256"]
        write_json(execution / "summary.json", summary, indent=2)
        write_json(args.output / "latest.json", {"execution": str(execution), "status": summary["status"]}, indent=2)
        print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
