"""Opt-in, synchronous profiling with detached results and scoped instrumentation.

POSIX resource counters include all waited children. Peak RSS is a process-lifetime
maximum, not an interval delta or a simultaneous parent/children memory total.
Use isolated workers for comparisons; instrumentation changes execution cost.
"""

import cProfile
import json
import pstats
import resource
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from inspect import getattr_static
from pathlib import Path
from time import perf_counter, process_time
from typing import TypedDict
from unittest.mock import patch


class Timing(TypedDict):
    calls: int
    inclusive_seconds: float
    exclusive_seconds: float


@dataclass
class _Frame:
    started: float
    children: float = 0.0


class Timings:
    """Nested wall spans for one synchronous call stack; snapshots are detached."""

    def __init__(self, *, clock: Callable[[], float] = perf_counter):
        self._clock = clock
        self._stack: list[_Frame] = []
        self._rows: dict[str, Timing] = {}

    @contextmanager
    def span(self, name: str) -> Iterator[None]:
        frame = _Frame(self._clock())
        self._stack.append(frame)
        try:
            yield
        finally:
            elapsed = self._clock() - frame.started
            self._stack.pop()
            if self._stack:
                self._stack[-1].children += elapsed
            row = self._rows.setdefault(name, Timing(calls=0, inclusive_seconds=0.0, exclusive_seconds=0.0))
            row["calls"] += 1
            row["inclusive_seconds"] += elapsed
            row["exclusive_seconds"] += elapsed - frame.children

    @contextmanager
    def wrap(self, owner: object, name: str, label: str) -> Iterator[None]:
        """Temporarily time a callable attribute, restoring it even on failure.

        A class patch affects other callers while active; use only in an exclusively
        owned synchronous worker. Inherited attributes retain their original lookup.
        """
        original = getattr(owner, name)
        descriptor = getattr_static(owner, name) if isinstance(owner, type) else None
        if isinstance(descriptor, (staticmethod, classmethod)):
            original = descriptor.__func__
        if not callable(original):
            raise TypeError(f"{name} is not callable.")

        @wraps(original)
        def timed(*args, **kwargs):
            with self.span(label):
                return original(*args, **kwargs)

        replacement = type(descriptor)(timed) if isinstance(descriptor, (staticmethod, classmethod)) else timed
        with patch.object(owner, name, replacement):
            yield

    def snapshot(self) -> dict[str, Timing]:
        if self._stack:
            raise RuntimeError("Finish active spans before reading their totals.")
        return {name: row.copy() for name, row in self._rows.items()}

    def reset(self) -> None:
        if self._stack:
            raise RuntimeError("Cannot reset active spans.")
        self._rows.clear()


class MeasurementResult(TypedDict):
    wall_seconds: float
    worker_cpu_seconds: float
    waited_child_cpu_seconds: float
    worker_peak_rss_mib: float
    waited_child_max_rss_mib: float
    spans: dict[str, Timing]
    unwrapped_seconds: float


class Measurement:
    """Measure one interval, stopping before subsequent validation/export work.

    Each instance is single-use. An exception still stops profiling and records
    costs, then propagates. Function-profile export requires a fresh directory.
    """

    def __init__(self, *, functions: bool = False):
        self.timings = Timings()
        self._profile = cProfile.Profile() if functions else None
        self._started = False
        self._result: MeasurementResult | None = None

    def __enter__(self) -> "Measurement":
        if self._started:
            raise RuntimeError("Use a new measurement for each interval.")
        self.timings.reset()
        self._started = True
        self._child = resource.getrusage(resource.RUSAGE_CHILDREN)
        self._wall, self._cpu = perf_counter(), process_time()
        if self._profile is not None:
            self._profile.enable()
        return self

    def __exit__(self, *_exc) -> None:
        if self._profile is not None:
            self._profile.disable()
        elapsed, cpu = perf_counter() - self._wall, process_time() - self._cpu
        child = resource.getrusage(resource.RUSAGE_CHILDREN)
        scale = 1024**2 if sys.platform == "darwin" else 1024
        spans = self.timings.snapshot()
        self._result = MeasurementResult(
            wall_seconds=elapsed,
            worker_cpu_seconds=cpu,
            waited_child_cpu_seconds=(child.ru_utime + child.ru_stime) - (self._child.ru_utime + self._child.ru_stime),
            worker_peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / scale,
            waited_child_max_rss_mib=child.ru_maxrss / scale,
            spans=spans,
            unwrapped_seconds=elapsed - sum(row["exclusive_seconds"] for row in spans.values()),
        )

    @property
    def result(self) -> MeasurementResult:
        if self._result is None:
            raise RuntimeError("Measurement has not finished.")
        return self._result | {"spans": {name: row.copy() for name, row in self._result["spans"].items()}}

    def export_functions(self, output: Path) -> None:
        """Write binary, readable and structured cProfile results without overwrite."""
        if self._result is None or self._profile is None:
            raise RuntimeError("Finish a measurement with functions=True before exporting.")
        output.mkdir(parents=True, exist_ok=False)
        self._profile.dump_stats(str(output / "diagnostic.prof"))
        stats = pstats.Stats(self._profile)
        with (output / "diagnostic.txt").open("x") as stream:
            stats.stream = stream
            stats.sort_stats("tottime").print_stats(60)
            stats.sort_stats("cumulative").print_stats(60)
        rows = [
            {
                "file": key[0],
                "line": key[1],
                "name": key[2],
                "primitive_calls": value[0],
                "calls": value[1],
                "self_seconds": value[2],
                "cumulative_seconds": value[3],
            }
            for key, value in sorted(stats.stats.items(), key=lambda row: -row[1][2])
        ]
        (output / "functions.json").write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
