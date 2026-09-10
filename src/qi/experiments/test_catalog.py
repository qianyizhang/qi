"""Recall survives absent runs; recording retains authority and rejects ambiguous updates."""

import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from typer.testing import CliRunner

from qi.api import create_app
from qi.artifacts import ROOT
from qi.experiments.catalog import (
    EvidenceRef,
    ExperimentEntry,
    catalog,
    check_catalog,
    evidence_path,
    get_entry,
    read_owner,
    record_entry,
)
from qi.experiments.cli import app

OWNER = "records/work-items/items/AB-TEST-001.md"


def entry(**overrides):
    return ExperimentEntry.model_validate(
        {
            "id": "teacher-budget",
            "title": "Teacher search budget",
            "question": "Does more work help a stronger teacher?",
            "kind": "teacher",
            "topics": ["teacher quality", "1M reference"],
            "execution": "complete",
            "conclusion": "inconclusive",
            "finding": "24/36 agreement; no student training.",
            "conditions": "Fixed small corpus and teacher.",
            "limitations": "Related positions; reference is an estimate.",
            "decision": "Keep defaults.",
            "revisit": "Independent held-out positions.",
            "evidence": [{"path": "artifacts/pilot/results.json", "role": "results"}],
            "novelty": "Historical pilot; no previous registered study.",
            **overrides,
        }
    )


def seed(root, record=None, owner=OWNER):
    path = root / owner
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Owning record\n\nOriginal interpretation.\n\n```experiment\n"
        + (record or entry()).model_dump_json()
        + "\n```\n"
    )
    return path


def test_recall_without_manifest_or_local_artifacts(tmp_path):
    seed(tmp_path)
    for query in ("teacher quality", "STRONGER teacher", "1M reference"):
        result = catalog(query, root=tmp_path)
        assert not result.issues and len(result.entries) == 1
        row = result.entries[0]
        assert row.execution == "complete" and row.conclusion == "inconclusive"
        assert not row.evidence_locations[0].available
    assert not catalog("student improvement demonstrated", root=tmp_path).entries
    assert "unregistered" in result.scope


def test_revision_retains_prior_bytes_and_rejects_stale_owner(tmp_path):
    path = seed(tmp_path)
    # Preserve CRLF exactly as well as ordinary UTF-8 text.
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    before = path.read_bytes()
    owner = read_owner(OWNER, root=tmp_path)
    revised = entry(finding="Corrected denominator: 24/35, one invalid position excluded.")
    row = record_entry(OWNER, revised, owner["owner_sha256"], root=tmp_path)
    assert path.read_bytes().startswith(before)
    assert row.revision == 2 and row.finding == revised.finding
    assert row.owner_sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    after = path.read_bytes()
    with pytest.raises(ValueError, match="Owner changed"):
        record_entry(OWNER, entry(), owner["owner_sha256"], root=tmp_path)
    assert path.read_bytes() == after


def test_invalid_owner_is_visible_without_hiding_other_records(tmp_path):
    seed(tmp_path)
    bad = tmp_path / "records/reports/bad.md"
    bad.parent.mkdir(parents=True)
    bad.write_text('```experiment\n{"id":"broken"}\n```\n')
    result = catalog(root=tmp_path)
    assert len(result.entries) == 1 and len(result.issues) == 1
    assert result.issues[0].owner.endswith("bad.md")
    with pytest.raises(ValueError, match="Resolve catalog issues"):
        record_entry(OWNER, entry(), read_owner(OWNER, root=tmp_path)["owner_sha256"], root=tmp_path)
    bad.write_text('```experiment\n{"id":"broken"}\n')
    assert "Unclosed" in catalog(root=tmp_path).issues[0].message


def test_duplicate_ids_and_missing_prior_are_issues(tmp_path):
    seed(tmp_path)
    other = "records/reports/other.md"
    seed(tmp_path, owner=other)
    result = catalog(root=tmp_path)
    assert not result.entries and "Duplicate" in result.issues[0].message
    (tmp_path / other).unlink()
    seed(tmp_path, entry(prior_work=[{"id": "missing", "relationship": "extends", "contribution": "More positions."}]))
    assert "Unresolved prior" in catalog(root=tmp_path).issues[0].message


def test_record_rejects_owner_theft_and_unresolved_prior(tmp_path):
    seed(tmp_path)
    other = "records/reports/other.md"
    (tmp_path / other).parent.mkdir(parents=True)
    (tmp_path / other).write_text("# Other report\n")
    sha = read_owner(other, root=tmp_path)["owner_sha256"]
    with pytest.raises(ValueError, match="another owner"):
        record_entry(other, entry(), sha, root=tmp_path)
    with pytest.raises(ValueError, match="Prior experiment"):
        record_entry(
            other,
            entry(
                id="follow-up",
                prior_work=[{"id": "missing", "relationship": "extends", "contribution": "Broader data."}],
            ),
            sha,
            root=tmp_path,
        )
    assert (tmp_path / other).read_text() == "# Other report\n"


@pytest.mark.parametrize(
    "path", ["", ".", "../secret", "/etc/passwd", "artifacts/../../secret", "artifacts\\secret", ".git/config"]
)
def test_evidence_rejects_arbitrary_paths(path):
    with pytest.raises(ValidationError):
        EvidenceRef(path=path, role="results")


def test_symlink_escape_and_preview_limits(tmp_path):
    seed(tmp_path)
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts/pilot").symlink_to(tmp_path.parent, target_is_directory=True)
    assert "escapes" in catalog(root=tmp_path).issues[0].message
    (tmp_path / "artifacts/pilot").unlink()
    (tmp_path / "artifacts/pilot").mkdir()
    data = tmp_path / "artifacts/pilot/results.json"
    data.write_text('{"answer":24}')
    assert evidence_path("teacher-budget", 0, root=tmp_path) == data
    with pytest.raises(ValueError, match="Unknown evidence"):
        evidence_path("teacher-budget", -1, root=tmp_path)
    data.write_bytes(b" " * (4 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="preview limit"):
        evidence_path("teacher-budget", 0, root=tmp_path)
    with pytest.raises(ValueError, match="Owner must"):
        read_owner("src/README.md", root=tmp_path)


def test_optional_digest_verification_does_not_treat_missing_as_failed(tmp_path):
    seed(tmp_path, entry(evidence=[{"path": "artifacts/results.json", "role": "results", "sha256": "0" * 64}]))
    assert not check_catalog(root=tmp_path, verify_evidence=True).issues
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts/results.json").write_text("{}")
    assert not check_catalog(root=tmp_path).issues
    assert "digest mismatch" in check_catalog(root=tmp_path, verify_evidence=True).issues[0].message


@pytest.mark.parametrize(
    "overrides",
    [
        {"finding": " "},
        {"limitations": ""},
        {"topics": [" "]},
        {"evidence": []},
        {"execution": "running"},
        {"schema_version": 2},
        {"invented": "field"},
    ],
)
def test_conclusion_requires_supported_record_shape(overrides):
    with pytest.raises(ValidationError):
        entry(**overrides)


def test_cli_record_to_http_dashboard_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("QI_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("QI_LAB_STATE", str(tmp_path / "jobs"))
    path = tmp_path / OWNER
    path.parent.mkdir(parents=True)
    path.write_text("# Existing research owner\n")
    runner = CliRunner()
    read = runner.invoke(app, ["owner", OWNER])
    assert read.exit_code == 0
    proposed = tmp_path / "proposed.json"
    proposed.write_text(entry(execution="failed").model_dump_json())
    result = runner.invoke(
        app,
        [
            "record",
            "--owner",
            OWNER,
            "--entry",
            str(proposed),
            "--expected-sha256",
            json.loads(read.stdout)["owner_sha256"],
        ],
    )
    assert result.exit_code == 0, result.output
    cli = runner.invoke(app, ["search", "teacher quality"])
    assert cli.exit_code == 0
    with TestClient(create_app()) as client:
        response = client.get("/api/experiment-catalog", params={"q": "teacher quality"})
        assert response.json() == json.loads(cli.stdout)
        detail = client.get("/api/experiment-catalog/teacher-budget")
        assert detail.json() == json.loads(result.stdout)
        owner = client.get("/api/experiment-catalog/teacher-budget/owner")
        assert owner.text == path.read_text()
        assert owner.headers["x-content-type-options"] == "nosniff"
        assert client.get("/api/experiment-catalog/teacher-budget/evidence/0").status_code == 409
        assert client.post("/api/experiment-catalog").status_code == 405
    assert runner.invoke(app, ["check-catalog"]).exit_code == 0


def test_registered_history_recalls_teacher_pilots_and_keeps_negative_results():
    # Only tracked owners/compact evidence are required, never ignored raw artifacts.
    for query in ("teacher quality", "stronger teacher", "1M reference"):
        ids = {row.id for row in catalog(query, root=ROOT).entries}
        assert {"teacher-budget-20260909", "teacher-multipv-20260909"} <= ids
    assert get_entry("policy-tuning-v1", root=ROOT).conclusion == "not-supported"
    assert get_entry("search-components-v1", root=ROOT).execution == "incomplete"
