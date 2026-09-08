"""Read the vocabulary authority for offline report help; no duplicate definitions."""

from hashlib import sha256
from pathlib import Path

from qi.experiments.model import ROOT

SOURCE = Path("docs/glossary/ddd.md")


def load_glossary(path: Path = ROOT / SOURCE) -> dict:
    source = path.read_text()
    entries = []
    names: dict[str, str] = {}
    category = ""
    for line in source.splitlines():
        if line.startswith("## "):
            category = line[3:]
        if not line.startswith("| ") or line.startswith(("| Term |", "| :")):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 5 or not category:
            raise ValueError(f"Invalid glossary row: {line}")
        term, chinese, meaning, avoid, aliases = cells
        entry = dict(term=term, chinese=chinese, meaning=meaning, avoid=avoid, category=category)
        entry["aliases"] = [] if aliases == "—" else aliases.split("; ")
        for name in [term, *entry["aliases"]]:
            key = name.casefold()
            if key in names and names[key] != term:
                raise ValueError(f"Ambiguous glossary name {name}: {names[key]} / {term}")
            names[key] = term
        if any(item["term"] == term for item in entries):
            raise ValueError(f"Duplicate glossary term: {term}")
        entries.append(entry)
    if not entries:
        raise ValueError("Glossary contains no terms.")
    return {"source": str(SOURCE), "glossary_sha256": sha256(source.encode()).hexdigest(), "entries": entries}
