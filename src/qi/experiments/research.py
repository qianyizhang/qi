"""Project authored Markdown and pinned measurements into a portable reading view."""

import base64
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, ConfigDict, Field

from qi.experiments.catalog import workspace
from qi.experiments.evidence import require
from qi.experiments.report import portable_html

MAX_TEXT = 2 * 1024 * 1024
MAX_IMAGE = 8 * 1024 * 1024
MAX_TOTAL = 16 * 1024 * 1024
Format = Literal["percent", "decimal", "integer"]
REFERENCE = re.compile(r"^(\s{0,3}\[([^\]\n]+)\]:\s*)(<[^>\n]+>|[^\s]+)(.*)$")


def unfenced_lines(markdown: str):
    """Find Markdown references without interpreting examples in fenced code."""
    fence = None
    for line in markdown.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker[1]
            elif marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
        elif fence is None:
            yield line


def reference_label(label: str) -> str:
    return " ".join(label.split()).casefold()


class ViewModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class DataSource(ViewModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ValueRef(ViewModel):
    source: str
    pointer: str


class Stat(ViewModel):
    label: str
    value: ValueRef
    format: Format = "integer"
    note: str = ""


class Takeaway(ViewModel):
    title: str
    body: str


class Facet(ViewModel):
    key: str
    label: str
    pointer: str
    initial: str | int


class Metric(ViewModel):
    key: str
    label: str
    pointer: str
    format: Format = "decimal"
    precision: int = Field(default=2, ge=0, le=6)
    unit: str = ""
    note: str = ""
    denominator_pointer: str | None = None
    denominator_unit: str = "positions"


class Explorer(ViewModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    title: str
    description: str = ""
    caveat: str = ""
    source: str
    rows_pointer: str
    label_pointer: str
    labels: dict[str, str] = Field(default_factory=dict)
    facets: list[Facet] = Field(default_factory=list)
    metrics: list[Metric] = Field(min_length=1)


class ResearchView(ViewModel):
    version: Literal["research-view-v1"]
    summary: str | None = None
    data_sources: dict[str, DataSource] = Field(default_factory=dict)
    stats: list[Stat] = Field(default_factory=list)
    takeaways: list[Takeaway] = Field(default_factory=list)
    section_notes: dict[str, str] = Field(default_factory=dict)
    explorers: list[Explorer] = Field(default_factory=list)


def pointer(value, path: str):
    """Resolve a JSON Pointer; absent evidence is an error, explicit null is unknown."""
    require(not path or path.startswith("/"), f"Invalid JSON pointer: {path}")
    try:
        for part in path.split("/")[1:]:
            require(re.search(r"~(?![01])", part) is None, f"Invalid JSON pointer: {path}")
            key = part.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                require(re.fullmatch(r"0|[1-9][0-9]*", key) is not None, f"Invalid array pointer: {path}")
                value = value[int(key)]
            else:
                value = value[key]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError(f"Missing JSON pointer: {path}") from error
    return value


def number(value) -> int | float | None:
    require(
        value is None or (type(value) in (int, float) and math.isfinite(value)),
        "Measurement must be a finite number or explicit null.",
    )
    return value


def formatted(value, format: Format) -> str:
    value = number(value)
    if value is None:
        return "Unknown"
    if format == "percent":
        return f"{value * 100:.2f}%"
    return f"{value:,.0f}" if format == "integer" else f"{value:,.2f}"


def local(root: Path, path: Path) -> Path:
    resolved = (root / path).resolve()
    require(resolved.is_relative_to(root), "Report input escapes the workspace.")
    return resolved


def read_text(path: Path) -> bytes:
    require(path.is_file() and path.stat().st_size <= MAX_TEXT, f"Missing or oversized report input: {path}")
    return path.read_bytes()


class Attachments:
    """Embed only first-level references; missing/large files remain explicit receipts."""

    def __init__(self, root: Path):
        self.root = root
        self.resources: dict[str, dict] = {}
        self.images: dict[str, str] = {}
        self.keys: dict[tuple[str, bool], str] = {}
        self.total = 0

    def add(self, path: Path, *, image: bool = False) -> str:
        identity = (str(path.resolve()), image)
        if identity in self.keys:
            return self.keys[identity]
        key = f"image-{len(self.images)}" if image else f"evidence-{len(self.resources)}"
        resolved = path.resolve()
        name = str(resolved.relative_to(self.root)) if resolved.is_relative_to(self.root) else str(path)
        suffix = resolved.suffix.lower()
        mime = {".md": "text/markdown", ".json": "application/json", ".txt": "text/plain"}.get(suffix, "text/plain")
        reason = None
        raw = None
        if not resolved.is_relative_to(self.root):
            reason = "Outside the workspace; not embedded."
        elif not resolved.is_file():
            reason = "File is unavailable in this checkout."
        elif suffix not in ((".png", ".jpg", ".jpeg", ".gif", ".webp") if image else (".md", ".json", ".txt", ".py")):
            reason = "This file type is not embedded; consult the source checkout."
        elif resolved.stat().st_size > (MAX_IMAGE if image else MAX_TEXT):
            reason = "File exceeds the per-file embedding limit."
        elif self.total + resolved.stat().st_size > MAX_TOTAL:
            reason = "Report attachment budget reached."
        else:
            raw = resolved.read_bytes()
            self.total += len(raw)
        if image and raw is not None:
            subtype = "jpeg" if suffix in (".jpg", ".jpeg") else suffix[1:]
            self.images[key] = f"data:image/{subtype};base64,{base64.b64encode(raw).decode()}"
        else:
            key = f"evidence-{len(self.resources)}"
            content = None
            if raw is not None:
                try:
                    content = raw.decode("utf-8")
                except UnicodeDecodeError:
                    reason = "File is not UTF-8 text."
            self.resources[key] = {
                "path": name,
                "sha256": hashlib.sha256(raw).hexdigest() if raw is not None else None,
                "mime": mime,
                "content": content,
                "reason": reason,
            }
        self.keys[identity] = key
        return key

    def rewrite(self, markdown: str, base: Path, image_labels: set[str] | None = None) -> str:
        def replace(match):
            prefix, destination, suffix = match.groups()
            target = destination.strip("<>")
            url = urlsplit(target)
            if target.startswith("#"):
                return match[0]
            if url.scheme or url.netloc:
                # External images must not cause network requests on opening an export.
                return f"[External image: {prefix[2:-2]}]({target})" if prefix.startswith("!") else match[0]
            key = self.add(base / unquote(url.path), image=prefix.startswith("!"))
            if key.startswith("evidence-") and prefix.startswith("!"):
                prefix = prefix[1:]
            return f"{prefix}#{key}{suffix}"

        lines = []
        fence = None
        for line in markdown.splitlines():
            marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
            if marker:
                if fence is None:
                    fence = marker[1]
                elif marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                    fence = None
                lines.append(line)
                continue
            if fence is None:
                definition = REFERENCE.match(line)
                if definition:
                    prefix, label, destination, suffix = definition.groups()
                    target = destination.strip("<>")
                    url = urlsplit(target)
                    if not (target.startswith("#") or url.scheme or url.netloc):
                        key = self.add(
                            base / unquote(url.path), image=reference_label(label) in (image_labels or set())
                        )
                        line = f"{prefix}#{key}{suffix}"
                else:
                    line = re.sub(r"(!?\[[^\]\n]*\]\()(<[^>\n]+>|[^\s)]+)([^)\n]*\))", replace, line)
            lines.append(line)
        return "\n".join(lines)


def narrative(text: str) -> tuple[dict, str, list[dict]]:
    # Presentation normalizes line endings; source fingerprints retain original bytes.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    metadata = {}
    if text.startswith("---\n"):
        header, separator, text = text[4:].partition("\n---\n")
        require(bool(separator), "Unclosed report frontmatter.")
        for line in header.splitlines():
            key, colon, value = line.partition(":")
            if colon:
                metadata[key] = value.strip().strip("\"'")
    title = "Research report"
    sections = [{"id": "overview", "title": "Overview", "markdown": ""}]
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker[1]
            elif marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
        elif fence is None and line.startswith("# ") and title == "Research report":
            title = line[2:].strip()
            continue
        elif fence is None and line.startswith("## "):
            heading = line[3:].strip()
            slug = re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-") or "section"
            key = slug
            while any(section["id"] == key for section in sections):
                key += "-2"
            sections.append({"id": key, "title": heading, "markdown": ""})
            continue
        sections[-1]["markdown"] += line + "\n"
    for section in sections:
        section["markdown"] = section["markdown"].strip()
    return metadata, title, sections


def compile_explorer(spec: Explorer, sources: dict) -> dict:
    require(spec.source in sources, f"Unknown data source: {spec.source}")
    raw_rows = pointer(sources[spec.source], spec.rows_pointer)
    require(isinstance(raw_rows, list), "Explorer rows must be a JSON array.")
    require(len({f.key for f in spec.facets}) == len(spec.facets), "Duplicate facet key.")
    require(len({m.key for m in spec.metrics}) == len(spec.metrics), "Duplicate metric key.")
    rows = []
    identities = set()
    for raw in raw_rows:
        label = str(pointer(raw, spec.label_pointer))
        facets = {f.key: pointer(raw, f.pointer) for f in spec.facets}
        require(all(type(v) in (int, str) for v in facets.values()), "Facet values must be strings or integers.")
        label = spec.labels.get(label, label)
        identity = (label, tuple(facets.values()))
        require(identity not in identities, "Duplicate explorer label and facet combination.")
        identities.add(identity)
        values = {m.key: number(pointer(raw, m.pointer)) for m in spec.metrics}
        notes = {}
        for metric in spec.metrics:
            if metric.denominator_pointer is not None:
                denominator = number(pointer(raw, metric.denominator_pointer))
                notes[metric.key] = f"{formatted(denominator, 'integer')} {metric.denominator_unit}"
            else:
                notes[metric.key] = ""
        rows.append({"label": label, "facets": facets, "values": values, "notes": notes})
    order = list(spec.labels.values())
    rows.sort(key=lambda row: order.index(row["label"]) if row["label"] in order else len(order))
    facets = []
    for facet in spec.facets:
        values = list(dict.fromkeys(row["facets"][facet.key] for row in rows))
        require(facet.initial in values, f"Initial facet value absent: {facet.key}")
        facets.append({"key": facet.key, "label": facet.label, "values": values, "initial": facet.initial})
    return {
        **spec.model_dump(include={"id", "title", "description", "caveat"}),
        "facets": facets,
        "metrics": [
            m.model_dump(include={"key", "label", "format", "precision", "unit", "note"}) for m in spec.metrics
        ],
        "rows": rows,
    }


def build_research(owner: Path, view: Path | None = None, root: Path | None = None) -> dict:
    root = workspace(root)
    owner = local(root, owner)
    require(owner.suffix.lower() == ".md", "Authored report must be Markdown.")
    raw = read_text(owner)
    metadata, title, sections = narrative(raw.decode())
    attachments = Attachments(root)
    attachments.add(owner)
    spec = ResearchView(version="research-view-v1")
    sources = {}
    if view is not None:
        view = local(root, view)
        spec = ResearchView.model_validate_json(read_text(view))
        attachments.add(view)
        for key, source in spec.data_sources.items():
            path = local(root, Path(source.path))
            data = read_text(path)
            require(hashlib.sha256(data).hexdigest() == source.sha256, f"Data source hash mismatch: {key}")
            sources[key] = json.loads(data)
            attachments.add(path)
    outside_code = "\n".join(unfenced_lines(raw.decode()))
    definitions = "\n".join(line for line in outside_code.splitlines() if REFERENCE.match(line))
    image_labels = {
        reference_label(match[2] or match[1])
        for match in re.finditer(r"!\[([^\]\n]*)\](?:\[([^\]\n]*)\])?(?!\()", outside_code)
    }
    require(
        set(spec.section_notes).issubset(section["id"] for section in sections),
        "Section note references an unknown report section.",
    )
    for section in sections:
        # Each section is rendered separately, while reference definitions are document-wide.
        markdown = section["markdown"] + ("\n\n" + definitions if definitions else "")
        section["markdown"] = attachments.rewrite(markdown, owner.parent, image_labels)
        if section["id"] in spec.section_notes:
            section["note"] = spec.section_notes[section["id"]]
    stats = []
    for stat in spec.stats:
        require(stat.value.source in sources, f"Unknown data source: {stat.value.source}")
        value = pointer(sources[stat.value.source], stat.value.pointer)
        stats.append({"label": stat.label, "value": formatted(value, stat.format), "note": stat.note})
    require(len({s.id for s in spec.explorers}) == len(spec.explorers), "Duplicate explorer ID.")
    return {
        "kind": "research-report-v1",
        "title": title,
        "description": metadata.get("description", "Authored research report"),
        "date": metadata.get("last_update", ""),
        "outcome": metadata.get("report_outcome", metadata.get("status", "unassessed")),
        "source": {"path": str(owner.relative_to(root)), "sha256": hashlib.sha256(raw).hexdigest()},
        "summary": spec.summary or "",
        "stats": stats,
        "takeaways": [item.model_dump() for item in spec.takeaways],
        "sections": sections,
        "explorers": [compile_explorer(explorer, sources) for explorer in spec.explorers],
        "resources": attachments.resources,
        "images": attachments.images,
    }


def present(owner: Path, output: Path, view: Path | None = None, root: Path | None = None) -> dict:
    root = workspace(root)
    output = root / output
    require(output.suffix.lower() == ".html", "Authored report output must be HTML.")
    require(output.resolve().suffix.lower() == ".html", "HTML output cannot overwrite a source through a symlink.")
    bundle = build_research(owner, view, root)
    require(
        all(output.resolve() != (root / item["path"]).resolve() for item in bundle["resources"].values()),
        "Export must not overwrite report inputs or linked evidence.",
    )
    html = portable_html(bundle, bundle["title"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return {
        "path": str(output.resolve()),
        "source": bundle["source"],
        "sections": len(bundle["sections"]),
        "explorers": len(bundle["explorers"]),
        "embedded_resources": sum(r["content"] is not None for r in bundle["resources"].values()),
        "unavailable_resources": sum(r["content"] is None for r in bundle["resources"].values()),
        "images": len(bundle["images"]),
        "html_sha256": hashlib.sha256(html.encode()).hexdigest(),
    }
