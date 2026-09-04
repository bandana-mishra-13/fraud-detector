"""Focused tests for the bounded query-response cache."""

from app.utils.query_cache import QueryResponseCache, build_query_cache_key


def _key(**overrides: object) -> str:
    inputs: dict[str, object] = {
        "query": "Find structuring",
        "dataset_path": "synthetic_transactions.csv",
        "normal_sample_size": None,
        "filters": {"window": "30d", "rules": ["structuring"]},
    }
    inputs.update(overrides)
    return build_query_cache_key(**inputs)  # type: ignore[arg-type]


def test_cache_key_normalizes_query_and_dictionary_order_but_not_effective_inputs():
    baseline = _key()

    assert baseline == _key(query="  Find structuring  ")
    assert baseline == _key(filters={"rules": ["structuring"], "window": "30d"})
    assert baseline != _key(query="Find fan-out")
    assert baseline != _key(dataset_path="other.csv")
    assert baseline != _key(normal_sample_size=5)
    assert baseline != _key(filters={"window": "7d", "rules": ["structuring"]})


def test_cache_expires_entries_using_an_injected_clock_and_returns_safe_copies():
    now = [100.0]
    cache = QueryResponseCache(ttl_seconds=10.0, clock=lambda: now[0])
    cache.set("entry", {"nested": {"value": 1}})

    cached = cache.get("entry")
    assert cached == {"nested": {"value": 1}}
    assert cached is not None
    cached["nested"]["value"] = 2
    assert cache.get("entry") == {"nested": {"value": 1}}

    now[0] = 110.0
    assert cache.get("entry") is None
    assert len(cache) == 0


def test_cache_evicts_least_recently_used_entries_at_its_bound():
    cache = QueryResponseCache(max_entries=2)
    cache.set("first", {"value": 1})
    cache.set("second", {"value": 2})
    assert cache.get("first") == {"value": 1}

    cache.set("third", {"value": 3})

    assert cache.get("first") == {"value": 1}
    assert cache.get("second") is None
    assert cache.get("third") == {"value": 3}
    assert len(cache) == 2
