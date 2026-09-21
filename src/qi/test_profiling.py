"""Profiling keeps its accounting and patches inside the requested interval."""

import json
import pstats

import pytest

from qi.profiling import Measurement, Timings


def test_nested_spans_unwind_and_snapshots_are_detached():
    ticks = iter([0.0, 1.0, 3.0, 5.0])
    timings = Timings(clock=lambda: next(ticks))
    with pytest.raises(ValueError), timings.span("parent"):
        with timings.span("child"):
            with pytest.raises(RuntimeError):
                timings.reset()
            with pytest.raises(RuntimeError):
                timings.snapshot()
            raise ValueError("measured failure")
    rows = timings.snapshot()
    assert rows["parent"]["exclusive_seconds"] == 3.0
    assert rows["child"]["exclusive_seconds"] == 2.0
    assert sum(r["exclusive_seconds"] for r in rows.values()) == 5.0
    rows["parent"]["calls"] = 99
    assert timings.snapshot()["parent"]["calls"] == 1
    timings.reset()
    assert timings.snapshot() == {}


def test_wrapping_restores_inherited_method_after_failure():
    class Parent:
        def call(self):
            raise ValueError("failed call")

    class Child(Parent):
        pass

    timings = Timings()
    with pytest.raises(ValueError), timings.wrap(Child, "call", "call"):
        Child().call()
    assert "call" not in Child.__dict__
    assert Child.call is Parent.call
    assert timings.snapshot()["call"]["calls"] == 1


def test_measurement_freezes_before_validation_and_exports_after_error(tmp_path):
    def measured():
        raise ValueError("failure inside measured interval")

    def validation():
        return sum(range(5))

    measurement = Measurement(functions=True)
    with pytest.raises(RuntimeError):
        _ = measurement.result
    with pytest.raises(ValueError), measurement, measurement.timings.span("work"):
        measured()
    before = measurement.result
    with measurement.timings.span("validation"):
        validation()
    assert measurement.result == before
    assert 0 <= before["worker_cpu_seconds"]
    assert before["worker_peak_rss_mib"] > 0
    assert 0 < before["spans"]["work"]["exclusive_seconds"] <= before["wall_seconds"]
    before["spans"]["work"]["calls"] = 0
    assert measurement.result["spans"]["work"]["calls"] == 1
    output = tmp_path / "profile"
    measurement.export_functions(output)
    rows = json.loads((output / "functions.json").read_text())
    assert any(row["name"] == "measured" for row in rows)
    assert not any(row["name"] == "validation" for row in rows)
    assert pstats.Stats(str(output / "diagnostic.prof")).total_calls > 0
    with pytest.raises(FileExistsError):
        measurement.export_functions(output)
    with pytest.raises(RuntimeError), measurement:
        pass


@pytest.mark.parametrize("name", ["static", "class_method"])
def test_wrapping_preserves_descriptor_binding(name):
    class Parent:
        @staticmethod
        def static(value):
            return value

        @classmethod
        def class_method(cls, value):
            return cls, value

    class Child(Parent):
        pass

    expected = getattr(Child, name)(3)
    timings = Timings()
    with timings.wrap(Child, name, "method"):
        assert getattr(Child, name)(3) == expected
        assert getattr(Child(), name)(3) == expected
    assert name not in Child.__dict__
    assert timings.snapshot()["method"]["calls"] == 2


def test_function_export_requires_enabled_completed_measurement(tmp_path):
    measurement = Measurement()
    with measurement:
        pass
    with pytest.raises(RuntimeError):
        measurement.export_functions(tmp_path / "disabled")
