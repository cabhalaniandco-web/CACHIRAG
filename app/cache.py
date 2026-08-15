"""An LRU cache with hit/miss statistics.

This is the "CACHI" in CACHIRAG: repeated queries are served from the cache
instead of re-running retrieval and answer assembly, which is the main reason to
cache in a RAG service.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


@dataclass
class CacheStats:
    """Snapshot of cache activity."""

    hits: int
    misses: int
    size: int
    capacity: int

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return round(self.hits / total, 4) if total else 0.0


class LRUCache(Generic[K, V]):
    """A thread-safe, fixed-capacity least-recently-used cache."""

    def __init__(self, capacity: int = 128) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self._capacity = capacity
        self._store: OrderedDict[K, V] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._lock = Lock()

    def get(self, key: K) -> V | None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                self._hits += 1
                return self._store[key]
            self._misses += 1
            return None

    def set(self, key: K, value: V) -> None:
        with self._lock:
            self._store[key] = value
            self._store.move_to_end(key)
            while len(self._store) > self._capacity:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def reset_stats(self) -> None:
        with self._lock:
            self._hits = 0
            self._misses = 0

    def stats(self) -> CacheStats:
        with self._lock:
            return CacheStats(
                hits=self._hits,
                misses=self._misses,
                size=len(self._store),
                capacity=self._capacity,
            )
