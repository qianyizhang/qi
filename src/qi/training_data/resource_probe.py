"""Bounded observational counters for generation pilots; no SQL or teacher mutations."""

import ctypes
import os
import resource
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter

from qi_game.core import GameError


class DarwinUsage(ctypes.Structure):
    # macOS SDK sys/resource.h rusage_info_v2: UUID followed by 18 uint64 fields.
    _fields_ = [("uuid", ctypes.c_ubyte * 16), ("values", ctypes.c_uint64 * 18)]


class MachTimebase(ctypes.Structure):
    _fields_ = [("numer", ctypes.c_uint32), ("denom", ctypes.c_uint32)]


def process_usage(pid: int | None = None) -> dict:
    pid = os.getpid() if pid is None else pid
    if sys.platform == "darwin":
        usage = DarwinUsage()
        lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
        lib.proc_pid_rusage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
        lib.proc_pid_rusage.restype = ctypes.c_int
        if lib.proc_pid_rusage(pid, 2, ctypes.byref(usage)) != 0:
            return {"available": False, "errno": ctypes.get_errno()}
        values = usage.values
        timebase = MachTimebase()
        ctypes.CDLL("/usr/lib/libSystem.B.dylib").mach_timebase_info(ctypes.byref(timebase))
        return {
            "available": True,
            "authority": "macOS proc_pid_rusage v2",
            "pid": pid,
            "cpu_seconds": (values[0] + values[1]) * timebase.numer / timebase.denom / 1e9,
            "cpu_timebase": [timebase.numer, timebase.denom],
            "rss_bytes": values[6],
            "footprint_bytes": values[7],
            "disk_read_bytes": values[16],
            "disk_write_bytes": values[17],
        }
    return {"available": False, "reason": "OS disk accounting implemented for macOS only"}


class ResourceProbe:
    """Counts callback SQL traffic separately from OS-attributed disk bytes.

    SQLite trace callbacks can repeat outer statements for triggers; traffic is
    explicitly callback traffic, not an exact count of physical writes or SQL VM
    operations. Samples are per game; expensive SQL summaries are caller-controlled.
    """

    def __init__(self, path: Path):
        self.path = path
        self.started = perf_counter()
        self.initial = process_usage()
        self.statements = Counter()
        self.sql_bytes = Counter()
        self.peak_rss = self.peak_combined_rss = self.peak_wal = 0

    def trace(self, statement: str):
        operation = statement.lstrip().split(None, 1)[0].upper() if statement.strip() else "EMPTY"
        self.statements[operation] += 1
        self.sql_bytes[operation] += len(statement.encode())

    def snapshot(self, teacher_pids=()) -> dict:
        current = process_usage()
        children = [process_usage(pid) for pid in teacher_pids]
        rss = current.get("rss_bytes", 0)
        self.peak_rss = max(self.peak_rss, rss)
        self.peak_combined_rss = max(self.peak_combined_rss, rss + sum(c.get("rss_bytes", 0) for c in children))
        sizes = {
            suffix or "db": p.stat().st_size if p.exists() else 0
            for suffix in ("", "-wal", "-shm")
            for p in [Path(str(self.path) + suffix)]
        }
        self.peak_wal = max(self.peak_wal, sizes["-wal"])
        return {
            "elapsed_seconds": perf_counter() - self.started,
            "process": current,
            "disk_write_bytes": current.get("disk_write_bytes", 0) - self.initial.get("disk_write_bytes", 0)
            if current.get("available") and self.initial.get("available")
            else None,
            "disk_read_bytes": current.get("disk_read_bytes", 0) - self.initial.get("disk_read_bytes", 0)
            if current.get("available") and self.initial.get("available")
            else None,
            "sql_callbacks": dict(self.statements),
            "sql_callback_bytes": dict(self.sql_bytes),
            "peak_sampled_rss_bytes": self.peak_rss,
            "peak_sampled_combined_rss_bytes": self.peak_combined_rss,
            "peak_wal_bytes": self.peak_wal,
            "files": sizes,
            "teachers": children,
            "peak_process_rss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        }


def enforce_resources(sample: dict, limits: dict, free_bytes: int):
    if limits.get("max_write_bytes") is not None:
        if sample["disk_write_bytes"] is None:
            raise GameError("resource_limit", "Requested OS write guard is unavailable on this host.")
        if sample["disk_write_bytes"] >= limits["max_write_bytes"]:
            raise GameError("resource_limit", "OS-attributed write allowance reached; completed games are retained.")
    if limits.get("max_rss_bytes") is not None:
        if not sample["process"].get("available"):
            raise GameError("resource_limit", "Requested RSS guard is unavailable on this host.")
        if sample["peak_sampled_combined_rss_bytes"] >= limits["max_rss_bytes"]:
            raise GameError("resource_limit", "Sampled runner plus teacher RSS allowance reached.")
    if limits.get("min_free_bytes") is not None and free_bytes < limits["min_free_bytes"]:
        raise GameError("resource_limit", "Free disk space fell below the configured reserve.")
