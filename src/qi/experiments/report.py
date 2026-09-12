"""Recomputed comparisons and a portable, offline HTML projection."""

import json
from collections import defaultdict
from html import escape
from pathlib import Path
from statistics import mean

from qi.artifacts import digest
from qi.experiments.evidence import require
from qi.experiments.model import Plan
from qi.scoring import GameScore, score_pairs


def summarize(run: dict, opening: str | None = None) -> dict:
    plan = run["manifest"]["plan"]
    groups = defaultdict(list)
    for unit in run["units"]:
        if unit["status"] != "complete":
            continue
        job = unit["job"]
        if opening is not None and job["opening"] != opening:
            continue
        if job["kind"] == "probe":
            groups[(job["a"]["kind"], job["a"]["nodes"])].append(unit)
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
    units_by_id = {unit["job"]["id"]: unit for unit in run["units"]}
    comparisons = defaultdict(list)
    for job in Plan.model_validate(plan).jobs():
        if job["kind"] != "game" or (opening is not None and job["opening"] != opening):
            continue
        unit = units_by_id.get(job["id"])
        status = unit["status"] if unit else "pending"
        result = None
        turns = []
        if status == "complete":
            winner = unit["outcome"]["winner"]
            result = "draw" if winner is None else "win" if winner == job["a_side"] else "loss"
            turns = [turn for turn in unit.get("turns", []) if turn["side"] == job["a_side"]]
        comparisons[(job["a"]["kind"], job["b"]["kind"], job["a"]["nodes"])].append(
            GameScore(
                pair_id=digest([job["opening"], job["a"], job["b"]]),
                a_side=job["a_side"],
                status=status,
                result=result,
                decisions=len(turns),
                elapsed_ms=sum(turn["choice"]["elapsed_ms"] for turn in turns),
            )
        )
    matches = []
    unmatched = 0
    for (a, b, budget), games in comparisons.items():
        score = score_pairs(games)
        unmatched += score.unpaired_completed_games
        matches.append({"a": a, "b": b, "budget": budget, "pairs": score.completed_pairs, **score.model_dump()})
    return {"probes": probes, "matches": matches, "unpaired_completed_games": unmatched}


def render_export(bundle, format: str) -> str:
    data = bundle.data
    if format == "md":
        lines = [
            f"# {data.plan.name}",
            "",
            data.plan.question,
            "",
            f"Status: {data.status} · {data.completed}/{data.planned} completed units.",
            "",
            "## Authored narrative",
            "",
            data.narrative or "No narrative supplied.",
            "",
            "## Measured comparisons",
            "",
            "| Player | Budget | Samples / planned | Mean ms | Mean visits | Depth | Solved / tested |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in data.summary.probes:
            lines.append(
                f"| {row.player} | {row.budget} | {row.samples}/{row.expected} | {row.mean_ms:.3f} | "
                f"{row.mean_nodes:.2f} | {row.mean_depth:.2f} | {row.tactical_solved}/{row.tactical_tested} |"
            )
        lines += [
            "",
            "## Paired games",
            "",
            "| A / B | Budget | Pairs / planned | W / D / L | Score rate |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for row in data.summary.matches:
            rate = "unknown" if row.score_rate is None else str(row.score_rate)
            lines.append(
                f"| {row.a} / {row.b} | {row.budget} | {row.pairs}/{row.planned_pairs} | "
                f"{row.wins}/{row.draws}/{row.losses} | {rate} |"
            )
        lines += [
            "",
            "## Evidence and limits",
            "",
            data.validation,
            "",
            "Interactive boards, timelines and trees are available in the HTML export and app.",
            "Small exploratory samples do not establish general playing strength.",
            f"Unpaired completed games excluded from scoring: {data.summary.unpaired_completed_games}.",
            "",
            f"Evidence SHA-256: `{data.evidence_sha256}`",
            f"Narrative SHA-256: `{data.narrative_sha256}`",
            "",
        ]
        lines += [f"- [{unit.job.id}](units/{unit.job.id}.json) · {unit.status} · {unit.sha256}" for unit in data.units]
        lines += ["", "```json", json.dumps(data.provenance, indent=2), "```", ""]
        return "\n".join(lines)
    require(format == "html", "Supported report formats are html and md.")
    return portable_html(bundle.model_dump(), "Qi · Search experiments")


def portable_html(bundle: dict, title: str) -> str:
    """Package either report projection with the same offline viewer assets."""
    assets = Path(__file__).parent.parent / "static-report"
    require((assets / "viewer.js").exists(), "Build report assets first: npm run build --prefix web.")
    payload = (
        json.dumps(bundle, ensure_ascii=False, allow_nan=False)
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    css = (assets / "viewer.css").read_text() if (assets / "viewer.css").exists() else ""
    script = (assets / "viewer.js").read_text().replace("</script", "<\\/script")
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>" + escape(title) + "</title><style>" + css + "</style>"
        '<div id="root"></div><script type="application/json" id="data">'
        + payload
        + "</script><script>"
        + script
        + "</script></html>"
    )


def report(directory: Path, output: Path) -> dict:
    from qi.experiments.presentation import read_bundle

    require(
        output.suffix.lower() in (".html", ".md"),
        "Report output must be HTML or Markdown, separate from raw JSON evidence.",
    )
    target = output.resolve()
    require(
        target != (directory / "narrative.md").resolve()
        and not any(target.is_relative_to((directory / area).resolve()) for area in ("units", "traces", "source")),
        "Export must not overwrite narrative or evidence.",
    )
    bundle = read_bundle(directory)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_export(bundle, output.suffix.lower()[1:]))
    return {
        "path": str(target),
        "completed": bundle.data.completed,
        "planned": bundle.data.planned,
        "validation": bundle.data.validation,
        "summary": bundle.data.summary.model_dump(),
    }
