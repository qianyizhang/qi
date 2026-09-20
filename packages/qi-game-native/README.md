---
description: Optional C++ trajectory execution, ownership, and conformance checks.
scope: native game package
status: experimental
last_update: 2026-09-21
document_class: coordination
---

# Native game package

`qi-game-native` is an optional uv workspace package. Its C++17 core derives from
the minimal implementation in [AB-ARCH-003](../../records/work-items/items/AB-ARCH-003-native-backend-experiment.md).
The original study remains frozen. This maintained implementation uses pybind11
for managed object lifetimes and exception translation. Runtime dependencies
belong to this package; setuptools and pybind11 are build-only dependencies.

```bash
uv sync --locked --extra native
make test-native
```

A C++17 compiler is required to build the extension. Default installation does
not install or build it. Importing `qi_game_native` alone does not load the
extension; importing `qi_game_native.backend` explicitly does. Missing native
execution fails with an installation instruction. There is no silent fallback.

```python
from qi_game.contracts import Snapshot
from qi_game_native.backend import NativeTrajectory, step_many

games = [NativeTrajectory(Snapshot()), NativeTrajectory(Snapshot())]
try:
    positions = step_many(games, ["b2e2", "a3a4"])
    assert positions[0].snapshot.moves == ["b2e2"]
finally:
    for game in games:
        game.close()
```

Each handle exclusively owns one game. Full replay history determines repetition
and outcomes; restoration validates every action. No arbitrary-diagram API or
automatic reset is exposed. `inspect()` and `step()` return detached contract
objects; callers may retain or modify those objects without changing a handle.
Explicit idempotent `close()` releases state; Python ownership also releases it
when an abandoned handle is collected. Operations after close fail.

`step_many` advances 1..128 distinct handles once each, preserving caller order.
Actions are coordinate strings copied into C++; no borrowed array/pointer survives
the call. All supplied stale guards are checked before action validation. A rule,
guard or invalid-input rejection leaves every handle unchanged. Native changes
are staged before commit. C++ retains the GIL; handles are exclusively owned by
one caller. This is serial batch execution, with no worker or thread scheduler.
Workload truncation belongs to the caller; only referee outcomes terminate games.

`NativeReferee` also implements snapshot-based inspect/apply for explicit HTTP
injection. `NativeTrajectory.identity()` records the package version, compiler
and actual extension SHA-256. Semantic state hashes exclude backend identity.

## Generation integration

```python
from qi.training_data.generation_runner import generate_policies
from qi_game_native.backend import NativeTrajectory

result = generate_policies(store, config, trajectory_factory=NativeTrajectory)
```

The existing runner remains serial, driven by its Python actor and per-game RNG.
It uses native legality, transitions and outcomes, then materializes immutable
Python values for the existing teacher and sampler interfaces. Collection writes
continue reference replay validation and retain every-move crash recovery.
Backend identity lives in run execution metadata, outside actor/RNG identities.
Referee, append and sampling phase timers are diagnostic; they do not exhaust
wall time. Search, the older library generator and collection validation remain
separate consumers of the Python reference.

This integration's throughput conclusion belongs to
[AB-ARCH-004](../../records/work-items/items/AB-ARCH-004-native-generation.md).
The earlier complete-native-loop speedup does not establish generation speed.

## Verification

`make test-native` builds an sdist and wheel, tests the installed package in an
isolated environment, then exercises generation and HTTP integration. The native
wheel needs only `qi-game` and its declared dependencies. Core headers/sources and
colocated tests ship with the wheel. CI defines macOS and Linux lanes;
configured coverage is distinct from a locally executed result.

For the standalone memory/undefined-behavior check from the repository root:

```bash
clang++ -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer \
  packages/qi-game-native/sanitizer.cpp -o /tmp/qi-native-sanitizer
/tmp/qi-native-sanitizer
```
