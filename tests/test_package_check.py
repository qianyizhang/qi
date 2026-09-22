from pathlib import Path

import pytest

from scripts.package_check import PackageRunner, only_artifact


def test_package_runner_removes_checkout_imports_and_preserves_explicit_cache(tmp_path: Path) -> None:
    runner = PackageRunner.create(
        tmp_path,
        {"PYTHONPATH": "/unrelated/checkout", "UV_CACHE_DIR": "/shared/uv-cache"},
    )

    assert "PYTHONPATH" not in runner.environment
    assert runner.environment["UV_CACHE_DIR"] == "/shared/uv-cache"
    runner.use_offline_cache()
    assert runner.environment["UV_OFFLINE"] == "true"

    relative_cache = PackageRunner.create(tmp_path, {"UV_CACHE_DIR": ".cache/uv"})
    assert relative_cache.environment["UV_CACHE_DIR"] == str(tmp_path / ".cache/uv")
    assert relative_cache.resolve_path(Path("dist")) == tmp_path / "dist"


def test_only_artifact_rejects_missing_and_stale_build_outputs(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be absolute"):
        only_artifact(Path("dist"), "*.whl")

    with pytest.raises(RuntimeError, match="found 0"):
        only_artifact(tmp_path, "*.whl")

    first = tmp_path / "package-1.whl"
    first.touch()
    assert only_artifact(tmp_path, "*.whl") == first

    (tmp_path / "package-2.whl").touch()
    with pytest.raises(RuntimeError, match="found 2"):
        only_artifact(tmp_path, "*.whl")
