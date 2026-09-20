"""Learning source identity; safe to inspect without importing the trainer."""

import sys

from qi.artifacts import source_provenance


def source_identity() -> dict:
    source = source_provenance(include_assets=False, paths=("src/qi", "packages", "pyproject.toml", "uv.lock"))
    return {
        "source_sha256": source["source_sha256"],
        "python": sys.version,
        "git_revision": source["commit"],
        "git_dirty": bool(source["working_tree"]) if source["working_tree"] is not None else None,
    }
