"""Performance optimizations and caching utilities."""

import asyncio
import hashlib
import json
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

logger = logging.getLogger(__name__)


class SimpleCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, default_ttl: float = 300.0, max_size: int = 1000):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        return time.time() > entry["expires_at"]
    
    def _cleanup_expired(self):
        """Remove expired entries."""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time > entry["expires_at"]
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def _evict_if_full(self):
        """Evict oldest entries if cache is full."""
        if len(self.cache) >= self.max_size:
            # Remove 10% of oldest entries
            entries_to_remove = max(1, int(self.max_size * 0.1))
            sorted_entries = sorted(
                self.cache.items(), 
                key=lambda x: x[1]["created_at"]
            )
            for key, _ in sorted_entries[:entries_to_remove]:
                del self.cache[key]
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        self._cleanup_expired()
        
        if key in self.cache:
            entry = self.cache[key]
            if not self._is_expired(entry):
                entry["access_count"] += 1
                entry["last_accessed"] = time.time()
                return entry["value"]
            else:
                del self.cache[key]
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        self._cleanup_expired()
        self._evict_if_full()
        
        ttl = ttl or self.default_ttl
        current_time = time.time()
        
        self.cache[key] = {
            "value": value,
            "created_at": current_time,
            "last_accessed": current_time,
            "expires_at": current_time + ttl,
            "access_count": 1
        }
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self._cleanup_expired()
        
        total_access_count = sum(entry["access_count"] for entry in self.cache.values())
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "total_accesses": total_access_count,
            "hit_rate": None  # Would need to track misses to calculate
        }


# Global cache instance
_global_cache = SimpleCache()


def cache_key(*args, **kwargs) -> str:
    """Generate a cache key from function arguments."""
    # Create deterministic key from args and kwargs
    key_data = {
        "args": [str(arg) for arg in args],
        "kwargs": {k: str(v) for k, v in sorted(kwargs.items())}
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(
    ttl: float = 300.0,
    key_func: Optional[Callable] = None,
    cache_instance: Optional[SimpleCache] = None
):
    """Cache decorator for functions."""
    
    def decorator(func: Callable):
        cache = cache_instance or _global_cache
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    key = f"{func.__name__}:{key_func(*args, **kwargs)}"
                else:
                    key = f"{func.__name__}:{cache_key(*args, **kwargs)}"
                
                # Try to get from cache
                cached_result = cache.get(key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached_result
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                cache.set(key, result, ttl)
                logger.debug(f"Cache miss for {func.__name__}, result cached")
                return result
                
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    key = f"{func.__name__}:{key_func(*args, **kwargs)}"
                else:
                    key = f"{func.__name__}:{cache_key(*args, **kwargs)}"
                
                # Try to get from cache
                cached_result = cache.get(key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached_result
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                cache.set(key, result, ttl)
                logger.debug(f"Cache miss for {func.__name__}, result cached")
                return result
                
            return sync_wrapper
    
    return decorator


class BatchProcessor:
    """Batch requests to reduce API calls and improve performance."""
    
    def __init__(self, batch_size: int = 10, batch_timeout: float = 1.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_requests: Dict[str, list] = {}
        self.batch_tasks: Dict[str, asyncio.Task] = {}
    
    async def add_to_batch(
        self, 
        batch_key: str, 
        item: Any, 
        processor_func: Callable
    ) -> Any:
        """Add item to batch and return result when batch is processed."""
        
        # Initialize batch if doesn't exist
        if batch_key not in self.pending_requests:
            self.pending_requests[batch_key] = []
            # Schedule batch processing
            task = asyncio.create_task(
                self._process_batch_after_timeout(batch_key, processor_func)
            )
            self.batch_tasks[batch_key] = task
        
        # Create future for this request
        future = asyncio.Future()
        self.pending_requests[batch_key].append({
            "item": item,
            "future": future
        })
        
        # Process immediately if batch is full
        if len(self.pending_requests[batch_key]) >= self.batch_size:
            if batch_key in self.batch_tasks:
                task = self.batch_tasks[batch_key]
                if not task.done():
                    task.cancel()
                await self._process_batch(batch_key, processor_func)
        
        return await future
    
    async def _process_batch_after_timeout(
        self, 
        batch_key: str, 
        processor_func: Callable
    ):
        """Process batch after timeout."""
        try:
            await asyncio.sleep(self.batch_timeout)
            await self._process_batch(batch_key, processor_func)
        except asyncio.CancelledError:
            # Batch was processed early due to size limit
            pass
    
    async def _process_batch(self, batch_key: str, processor_func: Callable):
        """Process a batch of requests."""
        if batch_key not in self.pending_requests:
            return
        
        requests = self.pending_requests.pop(batch_key)
        if batch_key in self.batch_tasks:
            del self.batch_tasks[batch_key]
        
        if not requests:
            return
        
        try:
            # Extract items and process batch
            items = [req["item"] for req in requests]
            results = await processor_func(items)
            
            # Distribute results to individual futures
            if len(results) == len(requests):
                for req, result in zip(requests, results):
                    req["future"].set_result(result)
            else:
                # Fallback: set all futures to first result or error
                error = ValueError(f"Batch processor returned {len(results)} results for {len(requests)} requests")
                for req in requests:
                    req["future"].set_exception(error)
                    
        except Exception as e:
            # Set exception for all futures
            for req in requests:
                req["future"].set_exception(e)


def batch_process(batch_size: int = 10, batch_timeout: float = 1.0):
    """Decorator for batch processing functions."""
    processor = BatchProcessor(batch_size, batch_timeout)
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(item: Any, batch_key: str = "default"):
            return await processor.add_to_batch(batch_key, item, func)
        return wrapper
    
    return decorator


class PerformanceMonitor:
    """Monitor function performance and identify bottlenecks."""
    
    def __init__(self):
        self.stats: Dict[str, Dict[str, Any]] = {}
    
    def record_execution(
        self, 
        func_name: str, 
        duration: float, 
        success: bool = True,
        **metadata
    ):
        """Record function execution statistics."""
        if func_name not in self.stats:
            self.stats[func_name] = {
                "total_calls": 0,
                "total_duration": 0.0,
                "success_count": 0,
                "error_count": 0,
                "min_duration": float("inf"),
                "max_duration": 0.0,
                "recent_durations": [],
                "metadata": {}
            }
        
        stat = self.stats[func_name]
        stat["total_calls"] += 1
        stat["total_duration"] += duration
        stat["min_duration"] = min(stat["min_duration"], duration)
        stat["max_duration"] = max(stat["max_duration"], duration)
        
        if success:
            stat["success_count"] += 1
        else:
            stat["error_count"] += 1
        
        # Keep recent durations for calculating percentiles
        stat["recent_durations"].append(duration)
        if len(stat["recent_durations"]) > 100:
            stat["recent_durations"] = stat["recent_durations"][-100:]
        
        # Store metadata
        for key, value in metadata.items():
            if key not in stat["metadata"]:
                stat["metadata"][key] = []
            stat["metadata"][key].append(value)
            if len(stat["metadata"][key]) > 10:
                stat["metadata"][key] = stat["metadata"][key][-10:]
    
    def get_stats(self, func_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a function."""
        if func_name not in self.stats:
            return None
        
        stat = self.stats[func_name]
        recent_durations = sorted(stat["recent_durations"])
        
        result = {
            "total_calls": stat["total_calls"],
            "success_rate": stat["success_count"] / stat["total_calls"],
            "avg_duration": stat["total_duration"] / stat["total_calls"],
            "min_duration": stat["min_duration"],
            "max_duration": stat["max_duration"],
        }
        
        # Calculate percentiles if we have recent data
        if recent_durations:
            n = len(recent_durations)
            result.update({
                "p50_duration": recent_durations[int(n * 0.5)],
                "p90_duration": recent_durations[int(n * 0.9)],
                "p95_duration": recent_durations[int(n * 0.95)],
                "p99_duration": recent_durations[int(n * 0.99)] if n > 10 else recent_durations[-1]
            })
        
        return result
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all monitored functions."""
        return {name: self.get_stats(name) for name in self.stats.keys()}


# Global performance monitor
_global_monitor = PerformanceMonitor()


def monitor_performance(monitor: Optional[PerformanceMonitor] = None):
    """Decorator to monitor function performance."""
    
    def decorator(func: Callable):
        perf_monitor = monitor or _global_monitor
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    duration = time.time() - start_time
                    perf_monitor.record_execution(
                        func.__name__,
                        duration,
                        success,
                        args_count=len(args),
                        kwargs_count=len(kwargs)
                    )
                    
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    duration = time.time() - start_time
                    perf_monitor.record_execution(
                        func.__name__,
                        duration,
                        success,
                        args_count=len(args),
                        kwargs_count=len(kwargs)
                    )
                    
            return sync_wrapper
    
    return decorator


# Utility functions
def get_cache_stats() -> Dict[str, Any]:
    """Get global cache statistics."""
    return _global_cache.stats()


def clear_cache() -> None:
    """Clear global cache."""
    _global_cache.clear()


def get_performance_stats() -> Dict[str, Any]:
    """Get global performance statistics."""
    return _global_monitor.get_all_stats()