"""Predeclared synthetic persistence/read workload; no engine or optimizer execution."""

import argparse
import json
import resource
import subprocess
import sys
from pathlib import Path
from time import perf_counter

from qi_game.contracts import Snapshot
from qi_game.reference import legal_moves

from qi.artifacts import provenance, write_json
from qi.evaluation import Corpus, Opening
from qi.teacher import TeacherAnalysis, digest
from qi.training_data.assembly import Bucket, MixtureRecipe
from qi.training_data.collection_generation import generate_collection
from qi.training_data.config import PreparationConfig, SupervisionSettings
from qi.training_data.contracts import GenerationRecipe, SourcePlan, StartingPosition, fingerprint
from qi.training_data.generation import teacher_spec
from qi.training_data.snapshots import SelectionRecipe, SnapshotBucket, SnapshotReader, export_snapshot
from qi.training_data.store import Collection


def cell(output: Path, games: int):
    output.mkdir(parents=True, exist_ok=False)
    engine, network = output / "synthetic-engine", output / "synthetic-network"
    engine.write_text("Synthetic benchmark, not an executable teacher.\n")
    network.write_text("Synthetic benchmark identity.\n")
    corpus = Corpus(
        id="collection-benchmark",
        provenance="Reserved initial state; synthetic labels",
        openings=[Opening(id="initial", description="Initial board", snapshot=Snapshot())],
    )
    corpus_path = output / "corpus.json"
    corpus_path.write_text(corpus.model_dump_json())
    supervision = SupervisionSettings(
        engine=str(engine.resolve()),
        network=str(network.resolve()),
        engine_sha256=digest(engine),
        network_sha256=digest(network),
        nodes=100,
        depth=2,
    )
    teacher = supervision.teacher()
    spec = teacher_spec(teacher)
    generation = GenerationRecipe(
        id="collection-io-v1",
        seed=7,
        seconds=600,
        sources=[
            SourcePlan(
                id=split,
                mode="random",
                split=split,
                games=games // 2,
                additional_plies=16,
                samples=4,
                start=StartingPosition(id="initial", version="1"),
            )
            for split in ("train", "validation")
        ],
    )
    config = PreparationConfig(
        corpus=str(corpus_path.resolve()),
        corpus_sha256=corpus.digest,
        generation=generation,
        supervision=supervision,
        assembly=MixtureRecipe(
            id="unused-legacy-assembly",
            supervision_fingerprint=fingerprint("supervision-v1", spec),
            buckets=[Bucket(id=s, split=s, count=1) for s in ("train", "validation")],
        ),
    )
    write_json(output / "config.json", config.model_dump(), indent=2)
    source = provenance()
    write_json(output / "provenance.json", source, indent=2)

    def labeler(game, teacher):
        return TeacherAnalysis(
            snapshot=Snapshot(moves=list(game.moves)),
            state_hash=game.state_hash,
            move=sorted(legal_moves(game.board, game.turn))[0],
            engine_name="synthetic-first-legal",
            engine_sha256=spec["engine_sha256"],
            network_sha256=spec["network_sha256"],
            settings=spec["settings"],
            requested_nodes=teacher.nodes,
            requested_depth=teacher.depth,
            timeout_seconds=teacher.timeout_seconds,
            reported_nodes=0,
            reported_depth=0,
            score=None,
            elapsed_ms=0.0,
            search_info=[],
        )

    logical_write_bytes = 0

    def trace(statement):
        nonlocal logical_write_bytes
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE")):
            logical_write_bytes += len(statement.encode())

    started = perf_counter()
    with Collection(output / "collection.sqlite") as store:
        store.db.set_trace_callback(trace)
        result = generate_collection(store, config, labeler=labeler)
        write_seconds = perf_counter() - started
        # An empty reserved initial board alone is too weak for random short games:
        # reserve every shared observation explicitly, retaining this exclusion evidence.
        overlap = store.db.execute(
            "SELECT min(o.id) FROM position_occurrences o JOIN games g ON g.id=o.game_id "
            "GROUP BY o.input_hash HAVING count(DISTINCT g.split)>1"
        ).fetchall()
        corpus.openings += [
            Opening(id=f"shared-{i}", description="Pre-export shared-input exclusion", snapshot=store.snapshot(row[0]))
            for i, row in enumerate(overlap)
            if store.snapshot(row[0]).moves
        ]
        # Quotas are deliberately small, fixed per source count; no quota weakening on failure.
        selection = SelectionRecipe(
            analysis_spec=result["analysis_spec"],
            reserved_corpus=corpus,
            buckets=[SnapshotBucket(id=s, split=s, count=games // 2) for s in ("train", "validation")],
        )
        write_json(output / "selection.json", selection.model_dump(), indent=2)
        export_started = perf_counter()
        exported = export_snapshot(store, selection, output / "snapshot", shard_rows=256)
        export_seconds = perf_counter() - export_started
    read = json.loads(
        subprocess.run(
            [sys.executable, __file__, "--read", str(output / "snapshot")],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        ).stdout
    )
    read_rows, read_seconds = read["rows"], read["seconds"]
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    metrics = {
        "games": games,
        "occurrences": result["position_occurrences"],
        "analyses": result["analyses"],
        "write_seconds": write_seconds,
        "occurrences_per_second": result["position_occurrences"] / write_seconds,
        "logical_sql_write_bytes": logical_write_bytes,
        "export_seconds": export_seconds,
        "snapshot_rows": exported["rows"],
        "read_rows": read_rows,
        "read_seconds": read_seconds,
        "read_rows_per_second": read_rows / read_seconds,
        "read_peak_rss_bytes": read["peak_rss_bytes"],
        "peak_rss_bytes": rss if sys.platform == "darwin" else rss * 1024,
        "disk_bytes": sum(p.stat().st_size for p in output.rglob("*") if p.is_file()),
        "shared_observation_exclusions": len(overlap),
        "provenance": source,
    }
    write_json(output / "results.json", metrics, indent=2)
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--read", type=Path)
    parser.add_argument("--cell", type=int)
    args = parser.parse_args()
    if args.read is not None:
        reader = SnapshotReader(args.read)
        started = perf_counter()
        rows = sum(len(batch) for batch in reader.batches(128))
        seconds = perf_counter() - started
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        print(
            json.dumps(
                {"rows": rows, "seconds": seconds, "peak_rss_bytes": rss if sys.platform == "darwin" else rss * 1024}
            )
        )
        return
    if args.output is None:
        parser.error("--output is required for generation cells")
    if args.cell is not None:
        cell(args.output, args.cell)
        return
    args.output.mkdir(parents=True, exist_ok=False)
    # Fresh process per size so peak RSS is comparable, not a cumulative maximum.
    results = []
    for games in (16, 64, 256):
        output = args.output / str(games)
        subprocess.run(
            [sys.executable, __file__, "--output", str(output), "--cell", str(games)], check=True, timeout=600
        )
        results.append(json.loads((output / "results.json").read_text()))
    write_json(args.output / "results.json", {"cells": results}, indent=2)
    print(json.dumps({"results": str(args.output / "results.json"), "cells": len(results)}))


if __name__ == "__main__":
    main()
