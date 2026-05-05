"""
Resource monitor — tracks CPU and memory usage for any ingestor process.
"""

import os
import time

import psutil

_process = psutil.Process(os.getpid())


def snapshot() -> dict:
    """Return current CPU % and memory usage for this process."""
    return {
        "cpu_percent": _process.cpu_percent(interval=0.1),
        "memory_mb": _process.memory_info().rss / 1024 / 1024,
    }


def print_snapshot(label: str = "") -> None:
    """Print a single resource usage line, optionally prefixed with a label."""
    s = snapshot()
    prefix = f"[{label}] " if label else ""
    print(f"  {prefix}CPU: {s['cpu_percent']:.1f}%  MEM: {s['memory_mb']:.1f} MB")


class ResourceMonitor:
    """
    Context manager that tracks peak CPU and memory over a block of work.

    Usage:
        with ResourceMonitor("scrape page") as monitor:
            await scrape_page(page, url)
        print(monitor.summary())
    """

    def __init__(self, label: str = ""):
        self.label = label
        self.peak_memory_mb = 0.0
        self.peak_cpu_percent = 0.0
        self._start = None

    def __enter__(self):
        self._start = time.time()
        s = snapshot()
        self.peak_memory_mb = s["memory_mb"]
        self.peak_cpu_percent = s["cpu_percent"]
        return self

    def __exit__(self, *_):
        s = snapshot()
        self.peak_memory_mb = max(self.peak_memory_mb, s["memory_mb"])
        self.peak_cpu_percent = max(self.peak_cpu_percent, s["cpu_percent"])
        self.elapsed = time.time() - self._start

    def summary(self) -> str:
        prefix = f"[{self.label}] " if self.label else ""
        return (
            f"  {prefix}elapsed: {self.elapsed:.2f}s  "
            f"peak CPU: {self.peak_cpu_percent:.1f}%  "
            f"peak MEM: {self.peak_memory_mb:.1f} MB"
        )
