"""Startup helpers: warm up the bundled video engine in a background thread while the splash keeps animating."""
from __future__ import annotations

import subprocess
import threading
import time
from typing import Callable, List, Tuple

from .paths import find_tool, no_window_flags


def warm_engine(on_step: Callable[[str, float], None], pump: Callable[[], None], lo: float = 70, hi: float = 96,
                timeout: float = 240.0) -> List[Tuple[str, float, str]]:
    """Run each bundled tool once (this is when antivirus scans it for the first time) and report how long each took.

    The work happens in a thread so the splash window stays responsive; ``pump`` is called while waiting.
    """
    tools = [("video engine (ffmpeg)", "ffmpeg", ["-version"]), ("media reader (ffprobe)", "ffprobe", ["-version"])]
    results: List[Tuple[str, float, str]] = []
    state = {"i": 0, "done": False}

    def work():
        for label, exe, args in tools:
            state["i"] = len(results)
            t = time.perf_counter()
            note = "ok"
            try:
                subprocess.run([find_tool(exe), *args], capture_output=True, timeout=200, creationflags=no_window_flags())
            except Exception as e:  # noqa: BLE001
                note = f"unavailable ({type(e).__name__})"
            results.append((label, time.perf_counter() - t, note))
        state["done"] = True

    th = threading.Thread(target=work, daemon=True)
    th.start()
    t0, last = time.perf_counter(), -1
    while not state["done"] and time.perf_counter() - t0 < timeout:
        if state["i"] != last:
            last = state["i"]
            on_step(f"Checking the {tools[min(last, len(tools) - 1)][0]}...", lo + (hi - lo) * last / len(tools))
        pump()
        time.sleep(0.03)
    for label, secs, note in results:
        on_step(f"{label}: {note} ({secs:.1f}s)", hi)
    return results
