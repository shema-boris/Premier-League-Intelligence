"""Simple in-memory cache for API responses."""

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

T = TypeVar('T')


class SimpleCache:
    """Thread-safe in-memory cache with TTL."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[float, Any]] = {}
    
    def get(self, key: str) -> Any | None:
        """Get cached value if not expired."""
        if key not in self._cache:
            return None
        
        timestamp, value = self._cache[key]
        if time.time() - timestamp > self.ttl_seconds:
            del self._cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set cached value with current timestamp."""
        self._cache[key] = (time.time(), value)
    
    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
    
    def cached(self, key_fn: Callable[..., str]) -> Callable:
        """Decorator to cache function results."""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args, **kwargs) -> T:
                key = key_fn(*args, **kwargs)
                cached_value = self.get(key)
                if cached_value is not None:
                    return cached_value
                
                result = func(*args, **kwargs)
                self.set(key, result)
                return result
            return wrapper
        return decorator


# Global cache instances
match_cache = SimpleCache(ttl_seconds=1800)  # 30 minutes for match data
team_cache = SimpleCache(ttl_seconds=3600)   # 1 hour for team stats
lineup_cache = SimpleCache(ttl_seconds=7200)  # 2 hours for lineup predictions
