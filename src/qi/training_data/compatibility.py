"""Explicit bounded legacy conversion; existing JSON readers remain supported."""

import json
from hashlib import sha256
from pathlib import Path

from qi.artifacts import provenance
from qi.protocol import Snapshot
from qi.training_data.contracts import Library
from qi.training_data.store import AnalysisSpec, Collection, GamePayload, RunPayload
from qi.training_data.v1 import Dataset, SourceGame

MAX_IMPORT_BYTES = 64 * 1024 * 1024


def import_json(store: Collection, path: Path) -> dict:
    with path.open("rb") as stream:
        content = stream.read(MAX_IMPORT_BYTES + 1)
    if len(content) > MAX_IMPORT_BYTES:
        raise ValueError("Legacy import is limited to 64 MiB; use incremental generation for larger data.")
    raw = json.loads(content)
    version = raw.get("schema_version")
    if version == "example-library-v1":
        data = Library.model_validate(raw)
        plans = {p.id: p for p in data.recipe.sources}
        metadata = {
            "recipe": data.recipe.model_dump(),
            "reserved_corpus": data.reserved_corpus.model_dump(),
            "status": data.status,
            "failure": data.failure,
        }
    elif version == 1:
        data = Dataset.model_validate(raw)
        metadata = {"seed": data.seed, "reserved_corpus": data.reserved_corpus.model_dump()}
    else:
        raise ValueError(
            "Collection import supports Dataset v1 and example-library-v1; "
            "other legacy formats remain readable via load_dataset."
        )
    # Build lineage once rather than scan every label for every source.
    by_source = {source.id: [] for source in data.sources}
    if isinstance(data, Library):
        for index, example in enumerate(data.examples):
            for source_id in example.source_ids:
                by_source[source_id].append((example.analysis, index))
    else:
        for index, label in enumerate(data.labels):
            by_source[label.source_id].append((label.analysis, index))
    parent = sha256(content).hexdigest()
    run = store.run(
        RunPayload(
            config={"import_format": str(version), "parent_digest": parent, "metadata": metadata},
            provenance=provenance(),
            seed=data.recipe.seed if isinstance(data, Library) else data.seed,
            planned_games=len(data.sources),
        )
    )
    active_game = None
    try:
        for source in data.sources:
            plan = plans[source.plan_id] if isinstance(data, Library) else None
            payload = GamePayload(
                source_id=source.id,
                family=source.family_id if plan else source.id,
                split=plan.split if plan else source.split,
                mode=plan.mode if plan else "random",
                initial=plan.start.snapshot if plan else Snapshot(),
                snapshot=plan.start.snapshot if plan else Snapshot(),
                actor=source.actor_spec if plan else {"recipe": "seeded-random-trajectories-v1"},
                plan=plan,
                themes=plan.start.themes if plan else [],
                objective=plan.start.objective if plan else None,
                parent_digest=parent,
            )
            game_id = store.begin_game(run, source.id, payload)
            if game_id is None:
                continue
            active_game = game_id
            game = payload.initial.game()
            for move in source.snapshot.moves[len(game.moves) :]:
                game = game.apply(move)
                store.append(game_id, Snapshot(moves=list(game.moves)))
            for answer, index in by_source[source.id]:
                occurrence = store.occurrence(
                    game_id,
                    answer.snapshot,
                    metadata={"legacy_index": index, "parent_digest": parent},
                    phase=plan.start.curated_phase if plan and answer.snapshot == plan.start.snapshot else None,
                )
                attempt = store.begin_analysis(occurrence, store.spec(AnalysisSpec.from_analysis(answer)))
                try:
                    store.finish_analysis(attempt, answer)
                except BaseException as exc:
                    store.finish_analysis(attempt, failure=str(exc), raw=[answer.model_dump_json()])
                    raise
            reason = source.stop_reason if plan else "terminal" if game.outcome else "ply-budget"
            store.finish_game(game_id, reason)
            active_game = None
        if isinstance(data, Library) and data.status != "complete":
            store.run_status(run, "failed", data.failure or "Imported incomplete library")
        else:
            store.run_status(run, "complete")
    except BaseException as exc:
        if active_game is not None:
            store.finish_game(active_game, "error", str(exc))
        store.run_status(run, "failed", str(exc))
        raise
    return {"run_id": run, "parent_digest": parent, **store.counts()}


def legacy_source(store: Collection, game_id: int) -> tuple[SourceGame, int, str]:
    """Only an imported v1 source can truthfully retain the v1 generator claim."""
    payload = store.game(game_id)
    record = store.db.execute(
        "SELECT json(r.payload) FROM generation_runs r JOIN games g ON g.run_id=r.id WHERE g.id=?",
        (game_id,),
    ).fetchone()
    run = RunPayload.model_validate_json(record[0])
    if (
        run.config.get("import_format") != "1"
        or payload.plan is not None
        or payload.initial.moves
        or payload.mode != "random"
        or payload.themes
        or payload.objective is not None
        or payload.family != payload.source_id
        or payload.actor != {"recipe": "seeded-random-trajectories-v1"}
        or not payload.parent_digest
        or payload.parent_digest != run.config.get("parent_digest")
    ):
        raise ValueError("Dataset v1 cannot express this source's generator, family, plan or annotation semantics.")
    return (
        SourceGame(id=payload.source_id, split=payload.split, snapshot=payload.snapshot),
        run.seed,
        payload.parent_digest,
    )


def export_legacy(snapshot: Path, destination: Path):
    """Small v1 export with explicit representability checks and a provenance receipt."""
    from qi.training_data.snapshots import SnapshotReader

    reader = SnapshotReader(snapshot)
    receipt = destination.with_name(destination.name + ".provenance.json")
    if reader.manifest["rows"] > 32768 or destination.exists() or receipt.exists():
        raise ValueError("Legacy export requires <=32768 rows and a fresh destination.")
    labels, sources, seeds, parents = [], {}, set(), set()
    with Collection(snapshot / "evidence.sqlite", readonly=True) as store:
        for batch in reader.batches():
            for row in batch.to_pylist():
                aliases = store.db.execute(
                    "SELECT DISTINCT game_id FROM position_occurrences WHERE input_hash=?",
                    (row["input_hash"],),
                ).fetchall()
                if len(aliases) != 1:
                    raise ValueError("Dataset v1 cannot express merged source lineage.")
                source, seed, parent = legacy_source(store, aliases[0][0])
                if source.id in sources and sources[source.id] != source:
                    raise ValueError("Dataset v1 cannot express colliding source IDs from different parents.")
                sources[source.id] = source
                seeds.add(seed)
                parents.add(parent)
        for batch in reader.label_batches():
            labels.extend(batch)
    if len(seeds) != 1:
        raise ValueError("Dataset v1 cannot express multiple generation seeds.")
    data = Dataset(
        seed=seeds.pop(),
        reserved_corpus=reader.recipe.reserved_corpus,
        sources=list(sources.values()),
        labels=labels,
    )
    result = {
        "dataset_sha256": data.digest,
        "snapshot_fingerprint": reader.manifest["fingerprint"],
        "source_bundle_sha256": reader.manifest["files"]["evidence.sqlite"],
        "parent_digests": sorted(parents),
        "selection_recipe": reader.recipe.model_dump(),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x") as stream:
        stream.write(data.model_dump_json() + "\n")
    with receipt.open("x") as stream:
        json.dump(result, stream, indent=2)
    return result
