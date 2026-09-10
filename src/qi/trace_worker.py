"""Owned subprocess entry point; publish only through the parent job manager."""

import os
import signal
import sys
import threading
from pathlib import Path

from qi.experiments.inspect import inspect_decision


def watch_parent(parent: int):
    while not threading.Event().wait(0.5):
        if os.getppid() != parent:
            os._exit(1)


if __name__ == "__main__":
    directory, unit, turn, output, limit, deadline, parent = sys.argv[1:]
    signal.setitimer(signal.ITIMER_REAL, float(deadline))
    threading.Thread(target=watch_parent, args=(int(parent),), daemon=True).start()
    inspect_decision(Path(directory), unit, int(turn), Path(output), int(limit))
