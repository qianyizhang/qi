"""Recomputed comparisons and a portable, offline HTML projection."""

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from qi.experiments.evidence import load_run, require
from qi.experiments.glossary import load_glossary
from qi.experiments.inspect import load_traces


def summarize(run: dict, opening: str | None = None) -> dict:
    plan = run["manifest"]["plan"]
    groups = defaultdict(list)
    pairs = defaultdict(list)
    for unit in run["units"]:
        if unit["status"] != "complete":
            continue
        job = unit["job"]
        if opening is not None and job["opening"] != opening:
            continue
        if job["kind"] == "probe":
            groups[(job["a"]["kind"], job["a"]["nodes"])].append(unit)
        else:
            key = (job["opening"], json.dumps(job["a"], sort_keys=True), json.dumps(job["b"], sort_keys=True))
            pairs[key].append(unit)
    probes = []
    for (player, budget), units in groups.items():
        choices = [unit["turns"][0]["choice"] for unit in units]
        targets = [unit for unit in units if unit["job"]["opening"] in plan["winning_moves"]]
        solved = sum(
            unit["turns"][0]["choice"]["move"] in plan["winning_moves"][unit["job"]["opening"]] for unit in targets
        )
        probes.append(
            {
                "player": player,
                "budget": budget,
                "samples": len(units),
                "expected": (1 if opening is not None else len(plan["corpus"]["openings"])) * len(plan["seeds"]),
                "mean_ms": mean(choice["elapsed_ms"] for choice in choices),
                "mean_nodes": mean(choice["nodes"] for choice in choices),
                "mean_depth": mean(choice["completed_depth"] for choice in choices),
                "tactical_solved": solved,
                "tactical_tested": len(targets),
                "mean_qnodes": mean(choice["qnodes"] for choice in choices),
                "mean_see_nodes": mean((choice["search_stats"] or {}).get("see_nodes", 0) for choice in choices),
                "tt_hits": sum((choice["search_stats"] or {}).get("tt_hits", 0) for choice in choices),
                "tt_cutoffs": sum((choice["search_stats"] or {}).get("tt_cutoffs", 0) for choice in choices),
                "leaf_aborts": sum((choice["mcts"] or {}).get("leaf_aborts", 0) for choice in choices),
            }
        )
    matches = defaultdict(lambda: {"wins": 0, "draws": 0, "losses": 0, "pairs": 0})
    unmatched = 0
    for units in pairs.values():
        if len(units) != 2 or {unit["job"]["a_side"] for unit in units} != {"red", "black"}:
            unmatched += len(units)
            continue
        job = units[0]["job"]
        group = matches[(job["a"]["kind"], job["b"]["kind"], job["a"]["nodes"])]
        group["pairs"] += 1
        for unit in units:
            winner = unit["outcome"]["winner"]
            group["draws" if winner is None else "wins" if winner == unit["job"]["a_side"] else "losses"] += 1
    return {
        "probes": probes,
        "matches": [{"a": a, "b": b, "budget": budget, **values} for (a, b, budget), values in matches.items()],
        "unpaired_completed_games": unmatched,
    }


def report(directory: Path, output: Path) -> dict:
    require(output.suffix.lower() == ".html", "Report output must be an HTML file, separate from raw JSON evidence.")
    run = load_run(directory)
    data = {
        **run,
        "glossary": load_glossary(),
        "summary": summarize(run),
        "traces": load_traces(directory, run),
        "by_position": {
            entry["id"]: summarize(run, entry["id"]) for entry in run["manifest"]["plan"]["corpus"]["openings"]
        },
    }
    assets = Path(__file__).parent
    payload = (
        json.dumps(data, separators=(",", ":"), allow_nan=False)
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    html = (assets / "report.html").read_text().replace("/* REPORT_STYLE */", (assets / "report.css").read_text())
    html = html.replace("/* REPORT_SCRIPT */", (assets / "report.js").read_text())
    html = html.replace("/* REPORT_HELP */", (assets / "report-help.js").read_text()).replace("REPORT_DATA", payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)
    return {
        "path": str(output.resolve()),
        "completed": run["completed"],
        "planned": run["planned"],
        "validation": run["validation"],
        "summary": data["summary"],
    }
