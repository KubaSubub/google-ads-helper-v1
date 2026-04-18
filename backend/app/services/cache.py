"""In-memory caches with TTL — replaces Redis for the local app.

Three caches are exposed:
    - `cache`              — default, TTL from settings (used for generic values)
    - `dashboard_kpis_cache` — 60s TTL, invalidated after sync / manual triggers
    - `recommendations_cache` — 120s TTL, invalidated after apply/dismiss actions
"""

from cachetools import TTLCache
from app.config import settings

# Generic cache — legacy users pass arbitrary TTL via the global setting.
cache = TTLCache(maxsize=2000, ttl=settings.cache_ttl)

# Hot-path caches sized for dashboard churn (filter toggles, re-renders).
dashboard_kpis_cache = TTLCache(maxsize=512, ttl=60)
recommendations_cache = TTLCache(maxsize=512, ttl=120)


def get_cached(key: str):
    """Get a value from cache, returns None if expired or missing."""
    return cache.get(key)


def set_cached(key: str, value):
    """Set a value in the cache. TTL is global (set in TTLCache constructor)."""
    cache[key] = value


def invalidate(key: str):
    """Remove a specific key from cache."""
    cache.pop(key, None)


def clear_cache():
    """Clear entire cache."""
    cache.clear()


def invalidate_client(client_id: int) -> None:
    """Drop every dashboard/recommendations entry for a given client.

    Called after sync completes or after a user action (apply/dismiss) so the
    next request recomputes fresh numbers.
    """
    prefix = f"client={client_id}|"
    for bucket in (dashboard_kpis_cache, recommendations_cache):
        for key in [k for k in bucket if k.startswith(prefix)]:
            bucket.pop(key, None)
