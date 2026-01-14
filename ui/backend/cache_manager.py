"""
Cache Manager Module for Azure Cost Optimizer

Provides a simple in-memory caching layer with TTL (time-to-live) support.
Can be extended to use Redis or other caching backends.

Usage:
    from cache_manager import cache_manager

    # Cache a value
    cache_manager.set("my_key", {"data": "value"}, ttl=300)

    # Get a cached value
    value = cache_manager.get("my_key")

    # Use as a decorator
    @cache_manager.cached(ttl=300)
    def expensive_function(param):
        return compute_result(param)
"""

import time
import threading
import hashlib
import json
from typing import Any, Optional, Callable, Dict
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a single cache entry with expiration."""
    
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
    
    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl
    
    @property
    def age(self) -> float:
        return time.time() - self.created_at


class CacheManager:
    """
    Thread-safe in-memory cache with TTL support.
    
    Features:
    - Automatic expiration of entries
    - Thread-safe operations
    - Cache statistics
    - Decorator for function caching
    - Namespace support for grouped invalidation
    """
    
    def __init__(self, default_ttl: int = 300, max_entries: int = 1000):
        """
        Initialize the cache manager.
        
        Args:
            default_ttl: Default time-to-live in seconds (5 minutes)
            max_entries: Maximum number of entries to store
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl
        self._max_entries = max_entries
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        with self._lock:
            # Enforce max entries limit
            if len(self._cache) >= self._max_entries and key not in self._cache:
                self._evict_oldest()
            
            self._cache[key] = CacheEntry(value, ttl or self._default_ttl)
            logger.debug(f"Cached key: {key} (TTL: {ttl or self._default_ttl}s)")
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Deleted key: {key}")
                return True
            return False
    
    def clear(self, namespace: Optional[str] = None) -> int:
        """
        Clear the cache.
        
        Args:
            namespace: If provided, only clear keys starting with this prefix
            
        Returns:
            Number of entries cleared
        """
        with self._lock:
            if namespace:
                keys_to_delete = [k for k in self._cache.keys() if k.startswith(namespace)]
                for key in keys_to_delete:
                    del self._cache[key]
                logger.info(f"Cleared {len(keys_to_delete)} keys in namespace: {namespace}")
                return len(keys_to_delete)
            else:
                count = len(self._cache)
                self._cache.clear()
                logger.info(f"Cleared entire cache ({count} entries)")
                return count
    
    def _evict_oldest(self) -> None:
        """Evict the oldest entry from the cache."""
        if not self._cache:
            return
        
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]
        logger.debug(f"Evicted oldest key: {oldest_key}")
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired]
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired entries")
            
            return len(expired_keys)
    
    @property
    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            
            return {
                "entries": len(self._cache),
                "max_entries": self._max_entries,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.1f}%",
                "default_ttl": self._default_ttl,
            }
    
    def cached(
        self,
        ttl: Optional[int] = None,
        namespace: str = "",
        key_builder: Optional[Callable] = None
    ):
        """
        Decorator to cache function results.
        
        Args:
            ttl: Time-to-live in seconds
            namespace: Prefix for cache keys
            key_builder: Custom function to build cache key from args
            
        Usage:
            @cache_manager.cached(ttl=300, namespace="policies")
            def get_policies():
                return load_policies_from_file()
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Build cache key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    # Default key builder using function name and args hash
                    args_key = hashlib.md5(
                        json.dumps((args, kwargs), sort_keys=True, default=str).encode()
                    ).hexdigest()[:8]
                    cache_key = f"{func.__name__}:{args_key}"
                
                if namespace:
                    cache_key = f"{namespace}:{cache_key}"
                
                # Check cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value
                
                # Call function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                
                return result
            
            # Add cache control methods to the wrapper
            wrapper.cache_clear = lambda: self.clear(namespace or func.__name__)
            wrapper.cache_key = lambda *a, **kw: f"{namespace}:{func.__name__}" if namespace else func.__name__
            
            return wrapper
        return decorator


# Global cache instance
cache_manager = CacheManager(default_ttl=300, max_entries=1000)


# Pre-defined cache namespaces and TTLs
class CacheNamespaces:
    """Standard cache namespaces for the optimizer."""
    POLICIES = "policies"
    SUBSCRIPTIONS = "subscriptions"
    COST_DATA = "cost_data"
    RESOURCES = "resources"
    RECOMMENDATIONS = "recommendations"


class CacheTTL:
    """Standard cache TTL values in seconds."""
    SHORT = 60          # 1 minute
    MEDIUM = 300        # 5 minutes
    LONG = 900          # 15 minutes
    VERY_LONG = 3600    # 1 hour
    
    # Specific TTLs for different data types
    POLICIES = 60       # Policies might be updated frequently
    SUBSCRIPTIONS = 300 # Subscription list rarely changes
    COST_DATA = 900     # Cost data updates periodically
    RESOURCES = 300     # Resource lists change moderately
