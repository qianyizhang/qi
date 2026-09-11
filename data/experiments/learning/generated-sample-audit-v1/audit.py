"""Read-only descriptive audit; no label queries, data selection, or fitting."""

import collections
import hashlib
import json
import pathlib
import sqlite3
import statistics
import time

from qi.evaluation import Corpus
from qi.game import in_check, moved, other, parse_move
from qi.training_data.v1 import reserved_inputs

ROOT = pathlib.Path(__file__).resolve().parents[4]
OUT = ROOT / "artifacts/learning/generated-sample-audit-v1"
OUT.mkdir(parents=True, exist_ok=True)
DB = ROOT / "artifacts/learning/overnight-batches-20260911/collection.sqlite"
started = time.time()
db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
db.execute("PRAGMA query_only=ON")
db.execute("BEGIN")


def counts(values):
    return dict(sorted(collections.Counter(values).items()))


def quantiles(values):
    v = sorted(values)
    if not v:
        return {"n": 0}
    return {
        "n": len(v),
        "min": v[0],
        "p10": v[int((len(v) - 1) * 0.1)],
        "median": statistics.median(v),
        "p90": v[int((len(v) - 1) * 0.9)],
        "max": v[-1],
        "mean": statistics.mean(v),
    }


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


files = [p for p in [DB, pathlib.Path(str(DB) + "-wal")] if p.exists()]
before = {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in files}
result = {
    "schema_version": 1,
    "scope": "descriptive-data-only-no-export-no-fits",
    "produced_by": "experiment@1.0.0 · agent=GPT-6 · effort=unspecified · 2026-09-11",
    "source": str(DB.relative_to(ROOT)),
    "high_water": {
        t: db.execute(f"SELECT max(id) FROM {t}").fetchone()[0] for t in ["games", "position_occurrences", "analyses"]
    },
}
specs = {
    i: {"identity": identity, **json.loads(p)}
    for i, identity, p in db.execute("SELECT id,identity,json(payload) FROM analysis_specs")
}
result["specs"] = specs
runs = {i: json.loads(p) for i, p in db.execute("SELECT id,json(payload) FROM generation_runs")}
corpus = Corpus.model_validate(next(iter(runs.values()))["config"]["recipe"]["corpus"])
reserved = reserved_inputs(corpus)
games = {}
for i, run, split, status, trajectory, outcome, payload in db.execute(
    "SELECT id,run_id,split,status,trajectory,outcome,json(payload) FROM games"
):
    p = json.loads(payload)
    a = p["actor"]
    g = a.get("generation_result", {})
    teacher = runs[run]["config"]["recipe"]["teachers"]["100k"]
    games[i] = {
        "id": i,
        "run": run,
        "split": split,
        "status": status,
        "trajectory": trajectory,
        "policy": a["policy"]["mode"],
        "threads": teacher.get("threads", 1),
        "source": a["source"],
        "block": int(a["source"].rsplit("-", 1)[1]),
        "plies": len(p["snapshot"]["moves"]),
        "outcome": json.loads(outcome) if outcome else None,
        "intervention_ply": g.get("intervention_planned_ply"),
        "intervention_applied": g.get("intervention_applied", False),
        "sampling": g.get("sampling"),
        "reasons": g.get("decision_reasons", {}),
        "multi_choice": sum(
            d["reason"] == "uniform-eligible" and len(d["eligible_moves"]) > 1 for d in g.get("decisions", [])
        ),
    }
accepted = [g for g in games.values() if g["status"] == "complete"]
result["games"] = {
    "statuses": counts(g["status"] for g in games.values()),
    "accepted_policy": counts(g["policy"] for g in accepted),
    "accepted_split": counts(g["split"] for g in accepted),
    "accepted_threads": counts(g["threads"] for g in accepted),
    "distinct_trajectories": len({g["trajectory"] for g in accepted}),
}
result["game_strata"] = []
for threads in [1, 8]:
    for policy in ["plausible", "intervention", "random"]:
        gs = [g for g in accepted if g["threads"] == threads and g["policy"] == policy]
        reason = collections.Counter()
        req, actual = collections.Counter(), collections.Counter()
        for g in gs:
            reason.update(g["reasons"])
            req.update(g["sampling"]["requested"])
            actual.update(g["sampling"]["actual"])
        result["game_strata"].append(
            {
                "threads": threads,
                "policy": policy,
                "games": len(gs),
                "plies": quantiles([g["plies"] for g in gs]),
                "outcomes": counts(g["outcome"]["reason"] if g["outcome"] else "none" for g in gs),
                "winners": counts(str(g["outcome"]["winner"]) if g["outcome"] else "none" for g in gs),
                "requested": dict(req),
                "selected": dict(actual),
                "decision_reasons": dict(reason),
                "multi_choice_decisions": sum(g["multi_choice"] for g in gs),
                "intervention_applied": sum(g["intervention_applied"] for g in gs),
            }
        )
print("game census complete", flush=True)

all_splits = collections.defaultdict(set)
selected = {}
for i, game, ply, board, turn, input_hash, phase, payload in db.execute(
    "SELECT id,game_id,ply_count,board,turn,input_hash,phase,json(payload) FROM position_occurrences"
):
    g = games[game]
    if g["status"] != "complete":
        continue
    all_splits[input_hash].add(g["split"])
    meta = json.loads(payload)["metadata"]
    if meta.get("selected"):
        selected[i] = {
            "id": i,
            "game": game,
            "ply": ply,
            "board": board,
            "turn": turn,
            "input": input_hash,
            "phase": phase,
            "meta": meta,
            "labels": {},
        }
selected_splits = collections.defaultdict(set)
for o in selected.values():
    selected_splits[o["input"]].add(games[o["game"]]["split"])
all_overlap = {k for k, v in all_splits.items() if len(v) > 1}
selected_overlap = {k for k, v in selected_splits.items() if len(v) > 1}
result["observations"] = {
    "stored_occurrences": db.execute("SELECT count(*) FROM position_occurrences").fetchone()[0],
    "selected_occurrences": len(selected),
    "distinct_selected_inputs": len(selected_splits),
    "selected_by_phase": counts(o["phase"] for o in selected.values()),
    "selected_by_split": counts(games[o["game"]]["split"] for o in selected.values()),
    "distinct_by_split": {s: sum(s in v for v in selected_splits.values()) for s in ["train", "validation"]},
    "cross_split_selected_distinct_inputs": len(selected_overlap),
    "cross_split_all_stored_distinct_inputs": len(all_overlap),
    "cross_split_all_stored_nonreserved_inputs": len(all_overlap - reserved),
    "selected_occurrences_touching_all_stored_overlap": sum(o["input"] in all_overlap for o in selected.values()),
    "selected_reserved_occurrences": sum(o["input"] in reserved for o in selected.values()),
}
print("occurrence census complete", flush=True)
result["analysis_status"] = dict(db.execute("SELECT status,count(*) FROM analyses GROUP BY status"))
for i, occurrence, spec, move, _order, score, depth, nodes in db.execute("""
    SELECT id,occurrence_id,spec_id,move,success_order,
           json_extract(payload,'$.answer.score'),json_extract(payload,'$.answer.reported_depth'),
           json_extract(payload,'$.answer.reported_nodes')
    FROM analyses WHERE status='success' ORDER BY success_order"""):
    if occurrence in selected and specs[spec]["supervision"]["settings"]["MultiPV"] == "1":
        o = selected[occurrence]
        if spec not in o["labels"]:
            o["labels"][spec] = {
                "id": i,
                "move": move,
                "score": json.loads(score) if score else None,
                "depth": depth,
                "nodes": nodes,
            }
print("label census complete", flush=True)
result["paired_labels"] = []
result["conflicts"] = []
conflicts = {}
overlap_exclusions = all_overlap | reserved
for spec, s in specs.items():
    if s["supervision"]["settings"]["MultiPV"] != "1":
        continue
    targets = collections.defaultdict(set)
    for o in selected.values():
        if spec in o["labels"] and o["input"] not in overlap_exclusions:
            targets[o["input"]].add(o["labels"][spec]["move"])
    conflicts[spec] = {k for k, v in targets.items() if len(v) > 1}
    result["conflicts"].append(
        {
            "spec": spec,
            "distinct_after_overlap_exclusion": len(targets),
            "conflicting_inputs": len(conflicts[spec]),
            "occurrences_on_conflicting_inputs": sum(
                o["input"] in conflicts[spec] and spec in o["labels"] for o in selected.values()
            ),
        }
    )
for threads, low, high in [(1, 2, 3), (8, 5, 6)]:
    for policy in ["plausible", "intervention", "random"]:
        for phase in ["opening", "middlegame", "endgame"]:
            rows = [
                o
                for o in selected.values()
                if games[o["game"]]["threads"] == threads
                and games[o["game"]]["policy"] == policy
                and o["phase"] == phase
            ]
            paired = [o for o in rows if low in o["labels"] and high in o["labels"]]
            strong = [o["labels"][high] for o in paired]
            scorekeys = counts(
                "missing" if a["score"] is None else a["score"]["kind"] + ":" + a["score"]["bound"] for a in strong
            )
            cp = [
                a["score"]["value"]
                for a in strong
                if a["score"] and a["score"]["kind"] == "cp" and a["score"]["bound"] == "exact"
            ]
            result["paired_labels"].append(
                {
                    "threads": threads,
                    "policy": policy,
                    "phase": phase,
                    "occurrences": len(rows),
                    "paired": len(paired),
                    "disagree": sum(o["labels"][low]["move"] != o["labels"][high]["move"] for o in paired),
                    "strong_score_status": scorekeys,
                    "strong_cp": quantiles(cp),
                    "strong_depth": quantiles([a["depth"] for a in strong if a["depth"] is not None]),
                    "reported_nodes": quantiles([a["nodes"] for a in strong if a["nodes"] is not None]),
                }
            )

# Provisional clean pools are diagnostic sets, not exports or an adopted rejection policy.
# Remove every recorded cross-split input and within-spec conflicting target input.
result["provisional_clean_pools"] = []
tags = collections.defaultdict(collections.Counter)
clean_rows = []
for threads, low, high in [(1, 2, 3), (8, 5, 6)]:
    excluded = all_overlap | reserved | conflicts[high]
    candidates = [o for o in selected.values() if high in o["labels"] and o["input"] not in excluded]
    # Lowest occurrence ID is used only for a descriptive deduplicated census.
    unique = {}
    for o in candidates:
        unique.setdefault(o["input"], o)
    for split in ["train", "validation"]:
        for policy in ["plausible", "intervention", "random"]:
            os = [
                o
                for o in unique.values()
                if games[o["game"]]["split"] == split and games[o["game"]]["policy"] == policy
            ]
            result["provisional_clean_pools"].append(
                {
                    "threads": threads,
                    "split": split,
                    "policy": policy,
                    "unique_inputs": len(os),
                    "contributing_games": len({o["game"] for o in os}),
                    "phases": counts(o["phase"] for o in os),
                    "block_groups": counts(games[o["game"]]["block"] // 10 for o in os),
                }
            )
    for o in unique.values():
        g = games[o["game"]]
        a = o["labels"][high]
        src, dst = parse_move(a["move"])
        check = in_check(o["board"], o["turn"])
        capture = o["board"][dst] != "."
        gives_check = in_check(moved(o["board"], src, dst), other(o["turn"]))
        disagreement = low in o["labels"] and o["labels"][low]["move"] != a["move"]
        it = g["intervention_ply"]
        since = o["ply"] - it if g["intervention_applied"] and it is not None else None
        timing = (
            "not-applied"
            if since is None
            else "before"
            if since < 0
            else "at-deviation"
            if since == 0
            else "after-1-8"
            if since <= 8
            else "after-9-plus"
        )
        sc = a["score"]
        score_band = "missing-or-bound"
        if sc and sc["bound"] == "exact":
            if sc["kind"] == "mate":
                score_band = "teacher-mate-positive" if sc["value"] > 0 else "teacher-mate-nonpositive"
            elif sc["kind"] == "cp":
                score_band = (
                    "cp-below-minus300"
                    if sc["value"] < -300
                    else "cp-above300"
                    if sc["value"] > 300
                    else "cp-within300"
                )
        key = f"threads{threads}:{g['split']}:{g['policy']}:{o['phase']}"
        tags[key].update(
            {
                "n": 1,
                "in-check": check,
                "teacher-capture": capture,
                "teacher-gives-check": gives_check,
                "budget-disagreement": disagreement,
                score_band: 1,
                "intervention:" + timing: 1,
            }
        )
        clean_rows.append(
            {
                "occurrence": o["id"],
                "game": o["game"],
                "input": o["input"],
                "threads": threads,
                "split": g["split"],
                "policy": g["policy"],
                "phase": o["phase"],
                "block": g["block"],
                "in_check": check,
                "teacher_capture": capture,
                "teacher_gives_check": gives_check,
                "budget_disagreement": disagreement,
                "score_band": score_band,
                "intervention_timing": timing,
            }
        )
result["provisional_clean_semantics"] = dict(tags)
capacity = {}
for block in range(3):
    for policy in ["plausible", "intervention", "random"]:
        grouped = collections.defaultdict(collections.Counter)
        for row in clean_rows:
            if (
                row["threads"] == 1
                and row["split"] == "train"
                and (row["block"] // 10) % 3 == block
                and row["policy"] == policy
                and row["phase"] != "opening"
            ):
                grouped[row["game"]][row["phase"]] += 1
        capacity[f"{block}:{policy}"] = {
            "games": len(grouped),
            "total_cap8": sum(min(8, sum(v.values())) for v in grouped.values()),
            "phase_cap8": {
                phase: sum(min(8, v[phase]) for v in grouped.values()) for phase in ["middlegame", "endgame"]
            },
        }
result["capacity_preflight"] = {
    "scope": "Necessary capacity bounds only; trajectory grouping and cross-block exclusion remain.",
    "grouping": "(source_block//10)%3",
    "counts": capacity,
}
sql_counts = db.execute("""
    SELECT count(*),count(DISTINCT o.input_hash) FROM position_occurrences o
    JOIN games g ON g.id=o.game_id
    WHERE g.status='complete' AND json_extract(o.payload,'$.metadata.selected')=1
""").fetchone()
assert sql_counts == (len(selected), len(selected_splits))
assert all(len(o["labels"]) == 2 for o in selected.values()), "Missing paired supervision"
assert sum(v["paired"] for v in result["paired_labels"]) == len(selected)
result["verification"] = {
    "independent_sql_selected_counts": list(sql_counts),
    "all_selected_occurrences_have_two_single_pv_labels": True,
    "strata_partition_selected_occurrences": True,
}
result["notes"] = [
    "All paired label comparisons count occurrences; they are not independent games or a truth audit.",
    "Provisional clean census excludes all recorded cross-split inputs and all chosen-spec target conflicts.",
    "Policy census uses lowest occurrence ID for multi-source inputs; selection must preserve all lineage.",
    "Full-history validity uses existing retained final validation; this audit does not replay every trajectory.",
    "Nonretained intermediate boards and earlier external datasets are not exhaustively overlap-audited here.",
    "One/eight threads occupy different source blocks; differences are confounded with generated data.",
    "cp bands use engine-native side-to-move scores; neither mate scores nor budget agreement proves correctness.",
    "No snapshot exported, recipe changed, teacher queried, trainer changed or model fitted.",
]
db.rollback()
db.close()
after = {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in files}
assert before == after, "Source collection changed during read-only census"
result["source_files"] = {str(p.relative_to(ROOT)): {"bytes": p.stat().st_size, "sha256": digest(p)} for p in files}
assert after == {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in files}
result["audit_script_sha256"] = digest(pathlib.Path(__file__))
result["elapsed_seconds"] = time.time() - started
(OUT / "results.json").write_text(json.dumps(result, indent=2) + "\n")
with (OUT / "provisional-tags.jsonl").open("w") as f:
    for row in clean_rows:
        f.write(json.dumps(row, sort_keys=True) + "\n")
print(
    json.dumps({k: result[k] for k in ["games", "observations", "conflicts", "elapsed_seconds"]}, indent=2), flush=True
)
