"""Background CPU/memory sampler used to profile a trial without blocking it.

Usage:
    with ResourceSampler(interval_seconds=0.05) as sampler:
        run_query(...)
    peak_rss_mb, avg_cpu_pct = sampler.summary()
"""
from __future__ import annotations

import statistics
import threading
import time

import psutil


class ResourceSampler:
    def __init__(self, interval_seconds: float = 0.05, pid: int | None = None):
        self.interval_seconds = interval_seconds
        self.process = psutil.Process(pid)
        self._samples_rss: list[int] = []
        self._samples_cpu: list[float] = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _sample_loop(self):
        self.process.cpu_percent(interval=None)  # prime the counter
        while not self._stop_event.is_set():
            self._samples_rss.append(self.process.memory_info().rss)
            self._samples_cpu.append(self.process.cpu_percent(interval=None))
            time.sleep(self.interval_seconds)

    def __enter__(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        return False

    def summary(self) -> tuple[int, float]:
        """Returns (peak_rss_bytes, mean_cpu_percent)."""
        peak_rss = max(self._samples_rss) if self._samples_rss else 0
        mean_cpu = statistics.mean(self._samples_cpu) if self._samples_cpu else 0.0
        return peak_rss, mean_cpu


def drop_os_page_cache():
    """Best-effort OS cache drop between trials (Linux only, needs sudo).
    Silently no-ops if it can't run — callers should not depend on it succeeding
    in CI/dev environments without root.
    """
    import subprocess

    try:
        subprocess.run(
            ["sudo", "sh", "-c", "sync; echo 3 > /proc/sys/vm/drop_caches"],
            check=True,
            timeout=5,
        )
    except Exception:
        pass
