"""Versioned, validated presentation data shared by HTTP and export renderers."""

import json
import re
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, ConfigDict
from qi_game.contracts import Snapshot

from qi.artifacts import digest, provenance
from qi.experiments.evidence import load_run, require
from qi.experiments.glossary import load_glossary
from qi.experiments.inspect import validate_trace
from qi.experiments.model import Plan
from qi.players import Choice, PlayerConfig
from qi.scoring import PairedScore


class GlossaryEntry(BaseModel):
    term: str
    chinese: str
    meaning: str
    avoid: str
    category: str
    aliases: list[str]


class Glossary(BaseModel):
    source: str
    glossary_sha256: str
    entries: list[GlossaryEntry]


class ProbeSummary(BaseModel):
    player: str
    budget: int
    samples: int
    expected: int
    mean_ms: float
    mean_nodes: float
    mean_depth: float
    tactical_solved: int
    tactical_tested: int
    mean_qnodes: float
    mean_see_nodes: float
    tt_hits: int
    tt_cutoffs: int
    leaf_aborts: int


class MatchSummary(PairedScore):
    a: str
    b: str
    budget: int
    pairs: int


class Summary(BaseModel):
    probes: list[ProbeSummary]
    matches: list[MatchSummary]
    unpaired_completed_games: int


class UnitJob(BaseModel):
    id: str
    kind: Literal["probe", "game"]
    opening: str
    a: PlayerConfig
    b: PlayerConfig | None = None
    a_side: Literal["red", "black"] | None = None


class UnitSummary(BaseModel):
    job: UnitJob
    status: str
    sha256: str
    decisions: int


class Frame(BaseModel):
    board: str
    side: Literal["red", "black"]


class RecordedTurn(BaseModel):
    ply: int
    side: Literal["red", "black"]
    choice: Choice


class UnitDetail(UnitSummary):
    model_config = ConfigDict(extra="allow")
    frames: list[Frame]
    turns: list[RecordedTurn]
    snapshot: Snapshot


class TraceEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: int
    parent: int | None
    kind: str
    board: str | None = None
    side: Literal["red", "black"] | None = None
    move: str | None = None
    value: float | None = None
    value_perspective: str | None = None
    bound: str | None = None
    status: str | None = None


class TraceSummary(BaseModel):
    id: str
    unit_id: str
    turn_index: int
    complete: bool
    events: int
    dropped_events: int
    event_limit: int


class TracePage(BaseModel):
    events: list[TraceEvent]
    total: int
    offset: int


class TraceBundle(BaseModel):
    summary: TraceSummary
    events: list[TraceEvent]


class ReportData(BaseModel):
    schema_version: Literal[1] = 1
    kind: Literal["search"] = "search"
    plan: Plan
    provenance: dict[str, Any]
    status: str
    completed: int
    planned: int
    validation: str
    evidence_sha256: str
    presentation_sha256: str
    glossary: Glossary
    summary: Summary
    by_position: dict[str, Summary]
    units: list[UnitSummary]
    traces: list[TraceSummary]
    warnings: list[str]
    narrative: str
    narrative_sha256: str
    trace_unavailable_reason: str | None


class ReportBundle(BaseModel):
    data: ReportData
    units: list[UnitDetail]
    traces: list[TraceBundle]


def contained(directory: Path, candidate: Path) -> Path:
    resolved = candidate.resolve()
    require(resolved.is_relative_to(directory.resolve()), "Artifact reference escapes the configured run.")
    return resolved


def check_files(directory: Path) -> None:
    for name in ("manifest.json", "status.json", "narrative.md", "units", "traces"):
        target = directory / name
        contained(directory, target)
        if target.is_dir():
            for item in target.glob("*.json"):
                contained(directory, item)
                require(item.stat().st_size <= 256 * 1024 * 1024, "Evidence file exceeds 256 MiB.")


def trace_compatibility(run: dict) -> str | None:
    current, saved = provenance(), run["manifest"]["provenance"]
    if current["source_sha256"] is None or any(
        current[key] != saved[key] for key in ("source_sha256", "python", "packages")
    ):
        return "Code or runtime changed; run a new benchmark before tracing. Saved evidence remains readable."
    return None


def narrative(directory: Path) -> tuple[str, list[str]]:
    path = contained(directory, directory / "narrative.md")
    if not path.exists():
        return "", []
    require(path.stat().st_size <= 1024 * 1024, "Narrative exceeds 1 MiB.")
    content = path.read_text()
    warnings = []
    # References are ordinary Markdown links/images. Rendering separately rejects active URL schemes.
    for target in re.findall(r"\]\(([^\s)]+)(?:\s+[^)]*)?\)", content):
        url = urlsplit(target.strip("<>"))
        if url.scheme or not url.path:
            if url.scheme and url.scheme not in ("https", "http", "mailto"):
                warnings.append(f"Unsupported narrative reference: {target}")
            continue
        try:
            reference = contained(directory, directory / unquote(url.path))
            require(
                reference.is_file() and reference.suffix in (".json", ".md"),
                "Use a saved JSON or Markdown evidence file.",
            )
        except ValueError as exc:
            warnings.append(f"Unsupported narrative reference {target}: {exc}")
    return content, warnings


def _fingerprint(directory: Path) -> tuple:
    files = [
        directory / "manifest.json",
        directory / "status.json",
        directory / "narrative.md",
        Path(__file__).resolve().parents[3] / "docs/glossary/ddd.md",
    ]
    files += sorted((directory / "units").glob("*.json")) + sorted((directory / "traces").glob("*.json"))
    require(len(files) <= 25000, "Run exceeds the presentation file limit.")
    directory_stat = directory.stat()
    records = [(str(directory), 0, directory_stat.st_mtime_ns, directory_stat.st_ctime_ns)]
    for path in files:
        if path.exists():
            stat = path.stat()
            records.append((str(path), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns))
    require(sum(row[1] for row in records) <= 512 * 1024 * 1024, "Run exceeds the 512 MiB presentation limit.")
    return tuple(records)


def read_bundle(directory: Path) -> ReportBundle:
    try:
        directory = directory.resolve()
        check_files(directory)
        fingerprint = _fingerprint(directory)
        bundle = _read_bundle(directory, fingerprint, digest(provenance()))
        require(fingerprint == _fingerprint(directory), "Evidence changed during validation; refresh the run.")
        return bundle
    except (OSError, KeyError, TypeError) as exc:
        raise ValueError(f"Cannot validate recorded evidence: {exc}") from exc


@lru_cache(maxsize=2)
def _read_bundle(directory: Path, fingerprint: tuple, runtime_identity: str) -> ReportBundle:
    # Cache only validated projections. File replacement, narrative/glossary edits and
    # code/runtime changes invalidate this bounded cache; callers treat DTOs as immutable.
    from qi.experiments.report import summarize

    check_files(directory)
    run = load_run(directory)
    units = [UnitDetail.model_validate({**unit, "decisions": len(unit["turns"])}) for unit in run["units"]]
    source_units = {unit["job"]["id"]: unit for unit in run["units"]}
    traces, warnings = [], []
    for path in sorted((directory / "traces").glob("*.json")):
        try:
            trace = json.loads(path.read_text())
            require(trace["unit_id"] in source_units, "Trace names an unknown unit.")
            validate_trace(trace, source_units[trace["unit_id"]], run["manifest"])
            record = trace["recording"]
            traces.append(
                TraceBundle(
                    summary=TraceSummary(
                        id=path.stem,
                        unit_id=trace["unit_id"],
                        turn_index=trace["turn_index"],
                        complete=record["complete"],
                        events=len(record["events"]),
                        dropped_events=record["dropped_events"],
                        event_limit=record["event_limit"],
                    ),
                    events=record["events"],
                )
            )
        except (ValueError, KeyError, TypeError, OSError) as exc:
            warnings.append(f"Invalid trace {path.name}: {exc}")
    authored, reference_warnings = narrative(directory)
    glossary = load_glossary()
    evidence = digest({"manifest": run["manifest"], "units": [unit.sha256 for unit in units]})
    narrative_sha = sha256(authored.encode()).hexdigest()
    data = ReportData(
        plan=run["manifest"]["plan"],
        provenance=run["manifest"]["provenance"],
        status=run["status"]["status"],
        completed=run["completed"],
        planned=run["planned"],
        validation=run["validation"],
        evidence_sha256=evidence,
        presentation_sha256=digest(
            [1, evidence, narrative_sha, glossary["glossary_sha256"], [trace.model_dump() for trace in traces]]
        ),
        glossary=glossary,
        summary=summarize(run),
        by_position={
            entry["id"]: summarize(run, entry["id"]) for entry in run["manifest"]["plan"]["corpus"]["openings"]
        },
        units=[UnitSummary.model_validate(unit.model_dump()) for unit in units],
        traces=[trace.summary for trace in traces],
        warnings=warnings + reference_warnings,
        narrative=authored,
        narrative_sha256=narrative_sha,
        trace_unavailable_reason=trace_compatibility(run),
    )
    return ReportBundle(data=data, units=units, traces=traces)
