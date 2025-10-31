from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Tuple, List


_COUNTERS: Dict[str, int] = {}
_COUNTERS_LABELLED: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], int] = {}


def inc(name: str, value: int = 1) -> None:
    _COUNTERS[name] = _COUNTERS.get(name, 0) + value


def get_counter(name: str) -> int:
    return _COUNTERS.get(name, 0)


def inc_labelled(name: str, labels: Dict[str, str], value: int = 1) -> None:
    key = (name, tuple(sorted(labels.items())))
    _COUNTERS_LABELLED[key] = _COUNTERS_LABELLED.get(key, 0) + value


def get_counter_labelled(name: str, labels: Dict[str, str]) -> int:
    key = (name, tuple(sorted(labels.items())))
    return _COUNTERS_LABELLED.get(key, 0)


def list_counters() -> List[Tuple[str, int]]:
    return sorted(_COUNTERS.items())


def list_counters_labelled() -> List[Tuple[str, Tuple[Tuple[str, str], ...], int]]:
    return sorted((name, labels, val) for (name, labels), val in _COUNTERS_LABELLED.items())


@dataclass
class Timer:
    name: str
    start: float = 0.0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        dur_ms = int((time.perf_counter() - self.start) * 1000)
        inc(f"{self.name}_ms_sum", dur_ms)
        inc(f"{self.name}_count", 1)


def reset() -> None:
    """Reset all in-process metrics (for tests)."""
    _COUNTERS.clear()
    _COUNTERS_LABELLED.clear()
