"""In-memory cache with TTL — replaces Redis for the local app."""

from cachetools import TTLCache
from app.config import settings

# Global cache instance — max 2000 entries, default TTL from config
cache = TTLCache(maxsize=2000, ttl=settings.cache_ttl)


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
