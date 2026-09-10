"""Shared discovery over experiment entries in their owning Markdown records.

The catalog never executes a run or infers scientific conclusions from metrics.
"""

import fcntl
import hashlib
import os
import re
from pathlib import Path, PurePosixPath
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from qi.artifacts import ROOT

BLOCK = re.compile(r"^```experiment\s*\n(.*?)^```\s*$", re.MULTILINE | re.DOTALL)
OWNER_DIRS = ("records/work-items/items", "records/reports")
MAX_RECORD = 2 * 1024 * 1024


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    path: str
    role: Literal["report", "results", "config", "data", "source", "run"]
    sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @field_validator("path")
    @classmethod
    def relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not value
            or not path.parts
            or path.is_absolute()
            or ".." in path.parts
            or "\\" in value
            or path.parts[0] not in ("artifacts", "data", "records", "docs", "src", "scripts")
        ):
            raise ValueError("Evidence must use a repository-relative evidence path.")
        return value


class PriorExperiment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,95}$")
    relationship: Literal["extends", "reproduces", "challenges", "uses"]
    contribution: str = Field(min_length=1)


class ExperimentEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,95}$")
    title: str = Field(min_length=1)
    question: str = Field(min_length=1)
    kind: Literal["teacher", "learning", "search", "data", "performance", "other"]
    topics: list[str] = Field(min_length=1)
    execution: Literal["planned", "running", "complete", "incomplete", "failed", "unknown"]
    conclusion: Literal["unassessed", "supported", "not-supported", "mixed", "inconclusive"]
    finding: str = ""
    conditions: str = Field(min_length=1)
    limitations: str = ""
    decision: str = ""
    revisit: str = ""
    evidence: list[EvidenceRef] = Field(default_factory=list)
    prior_work: list[PriorExperiment] = Field(default_factory=list)
    novelty: str = Field(min_length=1)

    @field_validator("topics")
    @classmethod
    def nonempty_topics(cls, topics: list[str]) -> list[str]:
        if any(not topic.strip() for topic in topics):
            raise ValueError("Topics must not be blank.")
        return topics

    @model_validator(mode="after")
    def assessment(self) -> Self:
        if self.execution in ("planned", "running") and self.conclusion != "unassessed":
            raise ValueError("Planned/running work cannot carry a final conclusion.")
        if self.execution in ("complete", "incomplete", "failed") and not self.evidence:
            raise ValueError("Executed work needs an evidence reference, including partial or failed work.")
        if self.conclusion != "unassessed" and not all((self.finding, self.limitations, self.decision, self.revisit)):
            raise ValueError("A conclusion needs a finding, limitations, decision and revisit trigger.")
        if self.id in {prior.id for prior in self.prior_work}:
            raise ValueError("An experiment cannot cite itself as prior work.")
        return self


class EvidenceLocation(EvidenceRef):
    available: bool
    previewable: bool


class CatalogEntry(ExperimentEntry):
    owner: str
    owner_sha256: str
    revision: int
    evidence_locations: list[EvidenceLocation]


class CatalogIssue(BaseModel):
    owner: str
    message: str


class ExperimentCatalog(BaseModel):
    entries: list[CatalogEntry]
    issues: list[CatalogIssue]
    scope: str = "Experiment entries in records/work-items/items and records/reports; unregistered work is not covered."


def workspace(root: Path | None = None) -> Path:
    return (root or Path(os.environ.get("QI_WORKSPACE", str(ROOT)))).resolve()


def contained(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Evidence path escapes the workspace.")
    return path


def owner_path(root: Path, relative: str) -> Path:
    path = contained(root, relative)
    if path.suffix != ".md" or path.parent not in {root / directory for directory in OWNER_DIRS}:
        raise ValueError("Owner must be a Markdown work item or report in the catalog scope.")
    return path


def read_owner(owner: str, *, root: Path | None = None) -> dict[str, str]:
    path = owner_path(workspace(root), owner)
    if path.stat().st_size > MAX_RECORD:
        raise ValueError("Record exceeds 2 MiB.")
    raw = path.read_bytes()
    return {"owner": owner, "owner_sha256": hashlib.sha256(raw).hexdigest(), "text": raw.decode()}


def parse_entries(text: str) -> list[ExperimentEntry]:
    matches = list(BLOCK.finditer(text))
    if len(matches) != len(re.findall(r"^```experiment(?:\s|$)", text, re.MULTILINE)):
        raise ValueError("Unclosed experiment block.")
    return [ExperimentEntry.model_validate_json(match[1]) for match in matches]


def catalog(query: str = "", *, root: Path | None = None) -> ExperimentCatalog:
    root = workspace(root)
    entries: dict[str, CatalogEntry] = {}
    issues = []
    collisions = set()
    for directory in OWNER_DIRS:
        for source in sorted((root / directory).glob("*.md")):
            relative = source.relative_to(root).as_posix()
            try:
                path = owner_path(root, relative)
                if path.stat().st_size > MAX_RECORD:
                    raise ValueError("Record exceeds 2 MiB.")
                raw = path.read_bytes()
                revisions = {}
                for record in parse_entries(raw.decode()):
                    if record.id in entries and entries[record.id].owner != relative:
                        collisions.add(record.id)
                        raise ValueError(f"Duplicate experiment ID across owners: {record.id}")
                    revisions[record.id] = revisions.get(record.id, 0) + 1
                    locations = [
                        EvidenceLocation(
                            **ref.model_dump(),
                            available=contained(root, ref.path).exists(),
                            previewable=can_preview(contained(root, ref.path)),
                        )
                        for ref in record.evidence
                    ]
                    entries[record.id] = CatalogEntry(
                        **record.model_dump(),
                        owner=relative,
                        owner_sha256=hashlib.sha256(raw).hexdigest(),
                        revision=revisions[record.id],
                        evidence_locations=locations,
                    )
            except (ValueError, OSError) as exc:
                issues.append(CatalogIssue(owner=relative, message=str(exc)))
    for id_ in collisions:
        entries.pop(id_, None)
    for entry in entries.values():
        for prior in entry.prior_work:
            if prior.id not in entries:
                issues.append(CatalogIssue(owner=entry.owner, message=f"Unresolved prior experiment: {prior.id}"))
    terms = query.casefold().split()
    ranked = []
    for entry in entries.values():
        # Search claims and limits as well as labels; results are candidates for reading.
        text = " ".join(
            [
                entry.id,
                entry.title,
                entry.question,
                *entry.topics,
                entry.finding,
                entry.conditions,
                entry.limitations,
                entry.decision,
                entry.revisit,
                entry.novelty,
            ]
        ).casefold()
        if all(term in text for term in terms):
            ranked.append(entry)
    return ExperimentCatalog(entries=sorted(ranked, key=lambda entry: entry.id), issues=issues)


def get_entry(id_: str, *, root: Path | None = None) -> CatalogEntry:
    result = catalog(root=root)
    entry = next((entry for entry in result.entries if entry.id == id_), None)
    if entry is None:
        raise ValueError(f"Unknown or invalid experiment: {id_}")
    return entry


def can_preview(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix in (".md", ".json", ".jsonl", ".txt", ".log")
        and path.stat().st_size <= 4 * 1024 * 1024
    )


def evidence_path(id_: str, index: int, *, root: Path | None = None) -> Path:
    root = workspace(root)
    entry = get_entry(id_, root=root)
    if not 0 <= index < len(entry.evidence):
        raise ValueError("Unknown evidence reference.")
    path = contained(root, entry.evidence[index].path)
    if not path.is_file() or path.suffix not in (".md", ".json", ".jsonl", ".txt", ".log"):
        raise ValueError("Evidence is missing or has no text preview; use its recorded local path.")
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("Evidence exceeds the 4 MiB preview limit; use its recorded local path.")
    return path


def check_catalog(*, root: Path | None = None, verify_evidence: bool = False) -> ExperimentCatalog:
    root = workspace(root)
    result = catalog(root=root)
    if verify_evidence:
        for entry in result.entries:
            for ref in entry.evidence:
                path = contained(root, ref.path)
                if ref.sha256 and path.is_file():
                    with path.open("rb") as stream:
                        actual = hashlib.file_digest(stream, "sha256").hexdigest()
                    if actual != ref.sha256:
                        result.issues.append(
                            CatalogIssue(owner=entry.owner, message=f"Evidence digest mismatch: {ref.path}")
                        )
    return result


def record_entry(owner: str, entry: ExperimentEntry, expected_sha256: str, *, root: Path | None = None) -> CatalogEntry:
    """Append a revision in its existing owner, retaining prior text and artifact bytes."""
    root = workspace(root)
    path = owner_path(root, owner)
    current = catalog(root=root)
    if current.issues:
        raise ValueError("Resolve catalog issues before recording an entry.")
    existing = next((row for row in current.entries if row.id == entry.id), None)
    if existing and existing.owner != owner:
        raise ValueError("Experiment ID already belongs to another owner.")
    known = {row.id for row in current.entries}
    if any(prior.id not in known for prior in entry.prior_work):
        raise ValueError("Prior experiment must be registered before recording its follow-up.")
    for ref in entry.evidence:
        contained(root, ref.path)
    addition = "\n\n```experiment\n" + entry.model_dump_json(indent=2) + "\n```\n"
    with path.open("r+b") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        raw = stream.read()
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("Owner changed; read it again before recording a conclusion.")
        if len(raw) + len(addition.encode()) > MAX_RECORD:
            raise ValueError("Record would exceed 2 MiB.")
        stream.seek(0, os.SEEK_END)
        stream.write(addition.encode())
        stream.flush()
        os.fsync(stream.fileno())
    return get_entry(entry.id, root=root)
