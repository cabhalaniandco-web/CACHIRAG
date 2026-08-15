import pytest

from app.cache import LRUCache


def test_hit_and_miss_tracking():
    cache: LRUCache[str, int] = LRUCache(capacity=2)
    assert cache.get("x") is None
    cache.set("x", 1)
    assert cache.get("x") == 1
    stats = cache.stats()
    assert stats.hits == 1
    assert stats.misses == 1
    assert stats.hit_rate == 0.5


def test_lru_eviction():
    cache: LRUCache[str, int] = LRUCache(capacity=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")  # touch "a" so "b" is least recently used
    cache.set("c", 3)  # evicts "b"
    assert cache.get("a") == 1
    assert cache.get("c") == 3
    assert cache.get("b") is None


def test_invalid_capacity():
    with pytest.raises(ValueError):
        LRUCache(capacity=0)


def test_clear_and_reset_stats():
    cache: LRUCache[str, int] = LRUCache(capacity=2)
    cache.set("a", 1)
    cache.get("a")
    cache.clear()
    cache.reset_stats()
    stats = cache.stats()
    assert stats.size == 0
    assert stats.hits == 0
    assert stats.misses == 0
