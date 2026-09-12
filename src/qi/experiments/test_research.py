"""Research presentations preserve authored meaning and frozen evidence boundaries."""

import base64
import hashlib
import json
from pathlib import Path

import pytest

from qi.experiments.research import build_research, present

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=")


def write_owner(root, content="# Historical pilot\n\n## Findings\n\nA bounded result.\n"):
    owner = Path("records/reports/historical.md")
    path = root / owner
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return owner


def write_view(root, data=None, **overrides):
    if data is None:
        data = {
            "fits": 0,
            "rows": [
                {"case": "a", "update": 50, "agreement": 0, "n": 12},
                {"case": "b", "update": 50, "agreement": None, "n": 0},
            ],
        }
    source = root / "data/results.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps(data))
    view = {
        "version": "research-view-v1",
        "data_sources": {
            "findings": {"path": "data/results.json", "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
        },
        "stats": [{"label": "Fits", "value": {"source": "findings", "pointer": "/fits"}, "format": "integer"}],
        "explorers": [
            {
                "id": "learning",
                "title": "Learning evidence",
                "description": "Observed agreement under fixed conditions.",
                "caveat": "Imitation agreement does not establish playing strength.",
                "source": "findings",
                "rows_pointer": "/rows",
                "label_pointer": "/case",
                "labels": {"a": "A"},
                "facets": [{"key": "update", "label": "Updates", "pointer": "/update", "initial": 50}],
                "metrics": [
                    {
                        "key": "agreement",
                        "label": "Agreement",
                        "pointer": "/agreement",
                        "format": "percent",
                        "unit": "",
                        "note": "Same target pool.",
                        "denominator_pointer": "/n",
                    }
                ],
            }
        ],
        **overrides,
    }
    path = root / "data/view.json"
    path.write_text(json.dumps(view))
    return Path("data/view.json"), view


def rewrite_view(root, path, view):
    (root / path).write_text(json.dumps(view))


def test_historical_markdown_preserves_sections_frontmatter_and_exact_source_hash(tmp_path):
    content = (
        "---\n"
        "description: A report written before the presentation viewer.\n"
        "last_update: 2026-09-11\n"
        "report_outcome: mixed\n"
        "---\n\n"
        "# Historical report\n\n"
        "The initial interpretation.\n\n"
        "## Why agreement changed\n\n"
        "A bounded observation.\n\n"
        "```text\n## This is code, not a section\n```\n\n"
        "~~~text\n## Another fenced heading\n~~~\n\n"
        "## Next question\n\n"
        "Separate coverage from transfer.\n"
    )
    owner = write_owner(tmp_path, content)
    raw = content.replace("\n", "\r\n").encode()
    (tmp_path / owner).write_bytes(raw)
    payload = build_research(owner, root=tmp_path)
    assert payload["kind"] == "research-report-v1"
    assert payload["title"] == "Historical report"
    assert payload["description"] == "A report written before the presentation viewer."
    assert payload["date"] == "2026-09-11"
    assert payload["outcome"] == "mixed"
    assert payload["source"] == {"path": owner.as_posix(), "sha256": hashlib.sha256(raw).hexdigest()}
    assert [section["title"] for section in payload["sections"]] == [
        "Overview",
        "Why agreement changed",
        "Next question",
    ]
    assert "The initial interpretation." in payload["sections"][0]["markdown"]
    assert "# Historical report" not in payload["sections"][0]["markdown"]
    assert "## This is code, not a section" in payload["sections"][1]["markdown"]
    assert "## Another fenced heading" in payload["sections"][1]["markdown"]
    assert len({section["id"] for section in payload["sections"]}) == 3


def test_linked_text_evidence_and_image_are_embedded_for_offline_reading(tmp_path):
    owner = write_owner(
        tmp_path,
        "# Reading evidence\n\n"
        "[Results](../../data/results.json) and [prior report](previous.md).\n\n"
        "![Observed overlap](../../data/overlap.png)\n",
    )
    data = tmp_path / "data"
    data.mkdir()
    (data / "results.json").write_text('{"tested": 12, "agreed": 0}')
    (tmp_path / "records/reports/previous.md").write_text("# Prior result\n\nInconclusive.\n")
    (data / "overlap.png").write_bytes(PNG)
    payload = build_research(owner, root=tmp_path)
    markdown = "\n".join(section["markdown"] for section in payload["sections"])
    for path in ("data/results.json", "records/reports/previous.md"):
        resource_id, resource = next(
            (key, value) for key, value in payload["resources"].items() if value["path"] == path
        )
        assert resource_id.startswith("evidence-")
        assert f"(#{resource_id})" in markdown
        assert resource["content"] == (tmp_path / path).read_text()
        assert resource["sha256"] == hashlib.sha256((tmp_path / path).read_bytes()).hexdigest()
        assert resource["reason"] is None
    image_id, image_uri = next(iter(payload["images"].items()))
    assert image_id.startswith("image-") and f"(#{image_id})" in markdown
    assert image_uri == "data:image/png;base64," + base64.b64encode(PNG).decode()


def test_document_wide_reference_links_and_images_work_across_sections(tmp_path):
    owner = write_owner(
        tmp_path,
        "# Referenced evidence\n\n"
        "[Recorded results][results] and [previous].\n\n"
        "![Observed overlap][Plot]\n\n"
        "## Supporting references\n\n"
        "[results]: ../../data/results.json\n"
        '[previous]: previous.md "Earlier report"\n'
        '[plot]: <../../data/overlap.png> "Coverage figure"\n\n'
        "```markdown\n[sealed]: ../../data/sealed.json\n```\n",
    )
    data = tmp_path / "data"
    data.mkdir()
    (data / "results.json").write_text('{"count": 12}')
    (data / "overlap.png").write_bytes(PNG)
    (data / "sealed.json").write_text('{"unread": "sealed marker"}')
    (tmp_path / "records/reports/previous.md").write_text("# Previous report\n")
    payload = build_research(owner, root=tmp_path)
    overview = payload["sections"][0]["markdown"]
    results_id = next(key for key, item in payload["resources"].items() if item["path"] == "data/results.json")
    prior_id = next(key for key, item in payload["resources"].items() if item["path"] == "records/reports/previous.md")
    image_id = next(iter(payload["images"]))
    assert f"[results]: #{results_id}" in overview
    assert f'[previous]: #{prior_id} "Earlier report"' in overview
    assert f'[plot]: #{image_id} "Coverage figure"' in overview
    assert "[Recorded results][results]" in overview and "![Observed overlap][Plot]" in overview
    assert not any(item["path"] == "data/sealed.json" for item in payload["resources"].values())
    assert "sealed marker" not in json.dumps(payload)


def test_missing_and_escaping_links_are_unavailable_without_reading_them(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text('{"private": "never embed this outside marker"}')
    owner = write_owner(
        root,
        "# Evidence availability\n\n"
        "[Missing](../../data/missing.json)\n"
        "[Outside](../../../outside.json)\n"
        "[Symlink](../../data/linked.json)\n",
    )
    (root / "data").mkdir()
    (root / "data/linked.json").symlink_to(outside)
    read_bytes, read_text = Path.read_bytes, Path.read_text

    def guarded_bytes(path, *args, **kwargs):
        assert path.resolve() != outside, "Export must not read evidence outside its workspace."
        return read_bytes(path, *args, **kwargs)

    def guarded_text(path, *args, **kwargs):
        assert path.resolve() != outside, "Export must not read evidence outside its workspace."
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", guarded_bytes)
    monkeypatch.setattr(Path, "read_text", guarded_text)
    payload = build_research(owner, root=root)
    unavailable = [resource for resource in payload["resources"].values() if resource["reason"]]
    # The direct path and symlink resolve to one unavailable evidence identity.
    assert len(unavailable) == 2
    assert all(resource["content"] is None and resource["sha256"] is None for resource in unavailable)
    markdown = "\n".join(section["markdown"] for section in payload["sections"])
    assert markdown.count("](#evidence-") == 3
    assert "never embed this outside marker" not in json.dumps(payload)


def test_unknown_metrics_remain_distinct_from_observed_zero(tmp_path):
    owner = write_owner(tmp_path)
    path, _ = write_view(tmp_path)
    payload = build_research(owner, path, root=tmp_path)
    assert payload["stats"][0]["value"] == "0"
    explorer = payload["explorers"][0]
    assert explorer["facets"][0]["values"] == [50]
    assert explorer["facets"][0]["initial"] == 50
    assert [row["label"] for row in explorer["rows"]] == ["A", "b"]
    assert [row["values"]["agreement"] for row in explorer["rows"]] == [0, None]
    assert "12" in explorer["rows"][0]["notes"]["agreement"]
    assert "0" in explorer["rows"][1]["notes"]["agreement"]
    assert explorer["caveat"] == "Imitation agreement does not establish playing strength."


def test_explicit_section_note_preserves_the_authored_narrative_and_source_hash(tmp_path):
    owner = write_owner(tmp_path)
    before = (tmp_path / owner).read_bytes()
    note = "Presentation correction: the exact recorded ratio rounds to 15.53%."
    path, _ = write_view(tmp_path, section_notes={"findings": note})
    payload = build_research(owner, path, root=tmp_path)
    findings = next(section for section in payload["sections"] if section["id"] == "findings")
    assert findings["note"] == note
    assert findings["markdown"] == "A bounded result."
    assert payload["source"]["sha256"] == hashlib.sha256(before).hexdigest()
    assert (tmp_path / owner).read_bytes() == before


def test_section_note_typo_cannot_silently_hide_a_correction(tmp_path):
    owner = write_owner(tmp_path)
    path, _ = write_view(tmp_path, section_notes={"missing-section": "An explicit correction."})
    with pytest.raises(ValueError, match="unknown report section"):
        build_research(owner, path, root=tmp_path)


def test_presentation_reads_saved_evidence_without_launching_evaluation(tmp_path, monkeypatch):
    from qi import teacher
    from qi.experiments import runner

    owner = write_owner(tmp_path)
    path, _ = write_view(tmp_path)
    before = {item.relative_to(tmp_path): item.read_bytes() for item in tmp_path.rglob("*") if item.is_file()}

    def forbidden(*args, **kwargs):
        raise AssertionError("Presentation must not execute an experiment or ask a teacher.")

    monkeypatch.setattr(teacher, "analyze", forbidden)
    monkeypatch.setattr(runner, "run", forbidden)
    build_research(owner, path, root=tmp_path)
    after = {item.relative_to(tmp_path): item.read_bytes() for item in tmp_path.rglob("*") if item.is_file()}
    assert after == before


@pytest.mark.parametrize("relative", ["../outside.md", "records/../../outside.md"])
def test_owner_must_stay_inside_workspace(tmp_path, relative):
    with pytest.raises(ValueError):
        build_research(Path(relative), root=tmp_path)


def test_owner_symlink_cannot_read_an_external_record(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("# Private outside record\n")
    (root / "linked.md").symlink_to(outside)
    with pytest.raises(ValueError):
        build_research(Path("linked.md"), root=root)


def test_view_must_stay_inside_workspace(tmp_path):
    owner = write_owner(tmp_path)
    with pytest.raises(ValueError):
        build_research(owner, Path("../outside.json"), root=tmp_path)


def test_frozen_source_hash_mismatch_is_rejected(tmp_path):
    owner = write_owner(tmp_path)
    path, _ = write_view(tmp_path)
    (tmp_path / "data/results.json").write_text('{"fits": 999, "rows": []}')
    with pytest.raises(ValueError, match=r"(?i)(hash|sha|changed|mismatch)"):
        build_research(owner, path, root=tmp_path)


def test_view_source_cannot_escape_via_a_symlink(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    owner = write_owner(root)
    path, _ = write_view(root)
    source = root / "data/results.json"
    outside = tmp_path / "outside.json"
    outside.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(outside)
    with pytest.raises(ValueError):
        build_research(owner, path, root=root)


@pytest.mark.parametrize("missing", ["stat", "metric", "denominator", "facet", "label", "rows"])
def test_missing_view_pointer_cannot_silently_become_zero_or_unknown(tmp_path, missing):
    owner = write_owner(tmp_path)
    path, view = write_view(tmp_path)
    explorer = view["explorers"][0]
    if missing == "stat":
        view["stats"][0]["value"]["pointer"] = "/missing"
    elif missing == "metric":
        explorer["metrics"][0]["pointer"] = "/missing"
    elif missing == "denominator":
        explorer["metrics"][0]["denominator_pointer"] = "/missing"
    elif missing == "facet":
        explorer["facets"][0]["pointer"] = "/missing"
    elif missing == "label":
        explorer["label_pointer"] = "/missing"
    else:
        explorer["rows_pointer"] = "/missing"
    rewrite_view(tmp_path, path, view)
    with pytest.raises(ValueError):
        build_research(owner, path, root=tmp_path)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("field", ["fits", "agreement", "n"])
def test_nonfinite_numeric_evidence_cannot_enter_a_chart(tmp_path, value, field):
    owner = write_owner(tmp_path)
    data = {"fits": 1, "rows": [{"case": "a", "update": 50, "agreement": 0.25, "n": 12}]}
    if field == "fits":
        data[field] = value
    else:
        data["rows"][0][field] = value
    path, _ = write_view(tmp_path, data)
    with pytest.raises(ValueError):
        build_research(owner, path, root=tmp_path)


def test_present_cannot_overwrite_owning_markdown_or_evidence(tmp_path):
    owner = write_owner(tmp_path)
    path, _ = write_view(tmp_path)
    before_owner = (tmp_path / owner).read_bytes()
    before_source = (tmp_path / "data/results.json").read_bytes()
    for output in (owner, Path("data/results.json")):
        with pytest.raises(ValueError):
            present(owner, output, path, root=tmp_path)
    assert (tmp_path / owner).read_bytes() == before_owner
    assert (tmp_path / "data/results.json").read_bytes() == before_source


def test_present_resolves_relative_output_against_workspace_and_returns_exact_receipt(tmp_path, monkeypatch):
    from qi.experiments import research

    owner = write_owner(tmp_path)
    html = "<!doctype html><html><body>Saved report.</body></html>"
    monkeypatch.setattr(research, "portable_html", lambda payload, title: html)
    receipt = present(owner, Path("exports/report.html"), root=tmp_path)
    output = tmp_path / "exports/report.html"
    assert output.read_text() == html
    assert receipt["path"] == str(output.resolve())
    assert receipt["html_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert receipt["source"]["sha256"] == hashlib.sha256((tmp_path / owner).read_bytes()).hexdigest()
    assert receipt["sections"] == 2 and receipt["explorers"] == 0


@pytest.mark.parametrize("target", ["records/reports/historical.md", "data/view.json", "data/results.json"])
def test_html_output_symlink_cannot_overwrite_a_source(tmp_path, target):
    owner = write_owner(tmp_path)
    path, _ = write_view(tmp_path)
    source = tmp_path / target
    before = source.read_bytes()
    output = tmp_path / "report.html"
    output.symlink_to(source)
    with pytest.raises(ValueError):
        present(owner, output, path, root=tmp_path)
    assert source.read_bytes() == before


def test_portable_html_escapes_script_payload_and_title_without_changing_data(tmp_path, monkeypatch):
    from qi.experiments import report

    assets = tmp_path / "qi/static-report"
    assets.mkdir(parents=True)
    (assets / "viewer.js").write_text('window.fixture = "</script>";')
    (assets / "viewer.css").write_text("body { color: black; }")
    monkeypatch.setattr(report, "__file__", str(tmp_path / "qi/experiments/report.py"))
    payload = {"narrative": "</script><script>window.injected = true;</script>\u2028\u2029"}
    title = "</title><script>window.titleInjected = true;</script>"
    html = report.portable_html(payload, title)
    assert html.count("<script") == 2
    assert "<title>&lt;/title&gt;&lt;script&gt;" in html
    assert 'window.fixture = "<\\/script>";' in html
    embedded_json = html.split('id="data">', 1)[1].split("</script>", 1)[0]
    assert json.loads(embedded_json) == payload
    assert "<" not in embedded_json and "\u2028" not in embedded_json and "\u2029" not in embedded_json
