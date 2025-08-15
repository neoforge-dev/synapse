"""Advanced performance optimization and metrics for production GraphRAG."""

import asyncio
import functools
import hashlib
import time
from collections import defaultdict, deque
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import weakref
import gc
import logging

from graph_rag.observability import (
    ComponentType,
    LogContext,
    PerformanceTimer,
    get_component_logger,
)

# Use structured logger for performance optimization
logger = get_component_logger(ComponentType.MONITORING, "performance_optimization")


@dataclass
class QueryPerformanceMetrics:
    """Detailed performance metrics for query operations."""
    
    query_id: str
    query_type: str  # vector, graph, hybrid, etc.
    
    # Timing breakdown
    total_duration_ms: float
    retrieval_duration_ms: float
    processing_duration_ms: float
    llm_duration_ms: float
    
    # Resource usage
    memory_before_mb: float
    memory_after_mb: float
    memory_peak_mb: float
    
    # Result metrics
    chunks_retrieved: int
    entities_found: int
    relationships_found: int
    response_length: int
    
    # Quality metrics
    cache_hit: bool
    cache_key: Optional[str] = None
    
    timestamp: float = field(default_factory=time.time)


@dataclass
class PerformanceProfile:
    """Performance profile for different operation types."""
    
    operation_type: str
    
    # Timing statistics
    avg_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    p50_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    
    # Throughput metrics
    operations_per_second: float
    total_operations: int
    
    # Resource efficiency
    avg_memory_usage_mb: float
    avg_cpu_percent: float
    
    # Cache effectiveness
    cache_hit_rate: float
    cache_miss_count: int
    
    # Error rates
    success_rate: float
    error_count: int
    
    timestamp: float = field(default_factory=time.time)


class AdvancedPerformanceMonitor:
    """Advanced performance monitoring with detailed breakdowns."""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.query_history: deque = deque(maxlen=max_history)
        self.operation_stats: Dict[str, List[float]] = defaultdict(list)
        self.memory_tracker = MemoryTracker()
        self.slow_query_threshold_ms = 2000.0
        self.slow_queries: deque = deque(maxlen=100)
        
    def start_query_tracking(self, query_id: str, query_type: str) -> Dict[str, Any]:
        """Start tracking a query operation."""
        context = {
            "query_id": query_id,
            "query_type": query_type,
            "start_time": time.time(),
            "memory_before": self.memory_tracker.get_current_memory_mb(),
            "gc_before": gc.get_count(),
        }
        
        logger.debug(
            "Started query tracking",
            LogContext(
                component=ComponentType.MONITORING,
                operation="start_query_tracking",
                query_id=query_id,
                metadata={"query_type": query_type}
            ),
            query_id=query_id,
            query_type=query_type
        )
        
        return context
    
    def finish_query_tracking(
        self,
        context: Dict[str, Any],
        retrieval_duration_ms: float,
        processing_duration_ms: float,
        llm_duration_ms: float,
        chunks_retrieved: int = 0,
        entities_found: int = 0,
        relationships_found: int = 0,
        response_length: int = 0,
        cache_hit: bool = False,
        cache_key: Optional[str] = None
    ) -> QueryPerformanceMetrics:
        """Finish tracking a query operation and record metrics."""
        
        end_time = time.time()
        total_duration_ms = (end_time - context["start_time"]) * 1000
        
        memory_after = self.memory_tracker.get_current_memory_mb()
        memory_peak = self.memory_tracker.get_peak_memory_mb()
        
        metrics = QueryPerformanceMetrics(
            query_id=context["query_id"],
            query_type=context["query_type"],
            total_duration_ms=total_duration_ms,
            retrieval_duration_ms=retrieval_duration_ms,
            processing_duration_ms=processing_duration_ms,
            llm_duration_ms=llm_duration_ms,
            memory_before_mb=context["memory_before"],
            memory_after_mb=memory_after,
            memory_peak_mb=memory_peak,
            chunks_retrieved=chunks_retrieved,
            entities_found=entities_found,
            relationships_found=relationships_found,
            response_length=response_length,
            cache_hit=cache_hit,
            cache_key=cache_key,
        )
        
        # Record metrics
        self.query_history.append(metrics)
        self.operation_stats[context["query_type"]].append(total_duration_ms)
        
        # Track slow queries
        if total_duration_ms > self.slow_query_threshold_ms:
            self.slow_queries.append(metrics)
            
            logger.warning(
                "Slow query detected",
                LogContext(
                    component=ComponentType.MONITORING,
                    operation="slow_query_detection",
                    query_id=context["query_id"],
                    duration_ms=total_duration_ms,
                    metadata={
                        "query_type": context["query_type"],
                        "threshold_ms": self.slow_query_threshold_ms
                    }
                ),
                duration_ms=total_duration_ms,
                query_type=context["query_type"]
            )
        
        logger.info(
            "Query tracking completed",
            LogContext(
                component=ComponentType.MONITORING,
                operation="finish_query_tracking",
                query_id=context["query_id"],
                duration_ms=total_duration_ms,
                metadata={
                    "query_type": context["query_type"],
                    "cache_hit": cache_hit,
                    "chunks_retrieved": chunks_retrieved
                }
            ),
            duration_ms=total_duration_ms,
            cache_hit=cache_hit
        )
        
        return metrics
    
    def get_performance_profile(self, operation_type: str) -> Optional[PerformanceProfile]:
        """Get performance profile for an operation type."""
        if operation_type not in self.operation_stats:
            return None
        
        durations = self.operation_stats[operation_type]
        if not durations:
            return None
        
        durations_sorted = sorted(durations)
        n = len(durations_sorted)
        
        # Calculate percentiles
        p50_idx = int(n * 0.5)
        p95_idx = int(n * 0.95) 
        p99_idx = int(n * 0.99)
        
        # Get recent queries for this operation type
        recent_queries = [
            q for q in self.query_history 
            if q.query_type == operation_type
        ]
        
        # Calculate cache hit rate
        cache_hits = sum(1 for q in recent_queries if q.cache_hit)
        cache_hit_rate = cache_hits / len(recent_queries) if recent_queries else 0.0
        
        # Calculate memory and timing stats
        avg_memory = sum(q.memory_peak_mb for q in recent_queries) / len(recent_queries) if recent_queries else 0.0
        
        # Calculate operations per second (based on recent window)
        recent_window_seconds = 60  # Last minute
        current_time = time.time()
        recent_ops = [
            q for q in recent_queries 
            if current_time - q.timestamp <= recent_window_seconds
        ]
        ops_per_second = len(recent_ops) / recent_window_seconds if recent_ops else 0.0
        
        profile = PerformanceProfile(
            operation_type=operation_type,
            avg_duration_ms=sum(durations) / len(durations),
            min_duration_ms=min(durations),
            max_duration_ms=max(durations),
            p50_duration_ms=durations_sorted[p50_idx],
            p95_duration_ms=durations_sorted[p95_idx],
            p99_duration_ms=durations_sorted[p99_idx],
            operations_per_second=ops_per_second,
            total_operations=len(durations),
            avg_memory_usage_mb=avg_memory,
            avg_cpu_percent=0.0,  # Would need CPU tracking
            cache_hit_rate=cache_hit_rate,
            cache_miss_count=len(recent_queries) - cache_hits,
            success_rate=1.0,  # Would need error tracking
            error_count=0,
        )
        
        return profile
    
    def get_slow_queries(self, limit: int = 10) -> List[QueryPerformanceMetrics]:
        """Get recent slow queries."""
        return list(self.slow_queries)[-limit:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        profiles = {}
        for op_type in self.operation_stats.keys():
            profile = self.get_performance_profile(op_type)
            if profile:
                profiles[op_type] = profile
        
        # Overall statistics
        all_queries = list(self.query_history)
        total_queries = len(all_queries)
        
        if total_queries > 0:
            avg_duration = sum(q.total_duration_ms for q in all_queries) / total_queries
            avg_memory = sum(q.memory_peak_mb for q in all_queries) / total_queries
            cache_hits = sum(1 for q in all_queries if q.cache_hit)
            cache_hit_rate = cache_hits / total_queries
        else:
            avg_duration = 0.0
            avg_memory = 0.0
            cache_hit_rate = 0.0
        
        summary = {
            "total_queries": total_queries,
            "avg_duration_ms": avg_duration,
            "avg_memory_usage_mb": avg_memory,
            "overall_cache_hit_rate": cache_hit_rate,
            "slow_query_count": len(self.slow_queries),
            "operation_profiles": profiles,
            "memory_stats": self.memory_tracker.get_stats(),
        }
        
        return summary


class MemoryTracker:
    """Track memory usage patterns for optimization."""
    
    def __init__(self):
        self.peak_memory = 0.0
        self.memory_samples: deque = deque(maxlen=100)
        
    def get_current_memory_mb(self) -> float:
        """Get current memory usage in MB."""
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        self.memory_samples.append((time.time(), memory_mb))
        self.peak_memory = max(self.peak_memory, memory_mb)
        
        return memory_mb
    
    def get_peak_memory_mb(self) -> float:
        """Get peak memory usage since tracking started."""
        return self.peak_memory
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        if not self.memory_samples:
            return {"error": "No memory samples available"}
        
        recent_memory = [sample[1] for sample in self.memory_samples]
        
        return {
            "current_mb": recent_memory[-1],
            "peak_mb": self.peak_memory,
            "avg_mb": sum(recent_memory) / len(recent_memory),
            "min_mb": min(recent_memory),
            "max_mb": max(recent_memory),
            "sample_count": len(self.memory_samples),
        }


class QueryOptimizer:
    """Optimize query performance based on usage patterns."""
    
    def __init__(self):
        self.query_patterns: Dict[str, int] = defaultdict(int)
        self.optimal_k_values: Dict[str, int] = {}
        self.query_complexity_cache: Dict[str, float] = {}
        
    def analyze_query_pattern(self, query: str, results_count: int, duration_ms: float):
        """Analyze query patterns to optimize future queries."""
        
        # Normalize query for pattern analysis
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()
        self.query_patterns[query_hash] += 1
        
        # Track query complexity (simple heuristic)
        complexity = self._calculate_query_complexity(query)
        self.query_complexity_cache[query_hash] = complexity
        
        # Optimize k value based on results vs duration
        if results_count > 0:
            efficiency = results_count / duration_ms  # results per ms
            current_k = self.optimal_k_values.get(query_hash, 5)
            
            # Simple optimization logic
            if efficiency > 0.1 and results_count >= current_k:
                # Query is efficient, could try higher k
                self.optimal_k_values[query_hash] = min(current_k + 1, 20)
            elif efficiency < 0.05 and current_k > 3:
                # Query is slow, reduce k
                self.optimal_k_values[query_hash] = max(current_k - 1, 3)
    
    def get_optimal_k(self, query: str) -> int:
        """Get optimal k value for a query based on patterns."""
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()
        return self.optimal_k_values.get(query_hash, 5)
    
    def should_use_cache(self, query: str) -> bool:
        """Determine if query should use cache based on patterns."""
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()
        frequency = self.query_patterns.get(query_hash, 0)
        complexity = self.query_complexity_cache.get(query_hash, 1.0)
        
        # Cache frequently asked complex queries
        return frequency >= 2 and complexity > 0.5
    
    def _calculate_query_complexity(self, query: str) -> float:
        """Calculate query complexity score (0-1)."""
        # Simple heuristic based on query characteristics
        length_factor = min(len(query.split()) / 20.0, 1.0)
        keyword_complexity = 0.0
        
        complex_keywords = ["analyze", "compare", "explain", "detailed", "comprehensive"]
        for keyword in complex_keywords:
            if keyword in query.lower():
                keyword_complexity += 0.2
        
        return min(length_factor + keyword_complexity, 1.0)
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get performance optimization recommendations."""
        recommendations = []
        
        # Analyze query patterns
        frequent_queries = [(hash_val, count) for hash_val, count in self.query_patterns.items() if count >= 5]
        
        if frequent_queries:
            recommendations.append(f"Consider pre-caching {len(frequent_queries)} frequently asked queries")
        
        # Analyze k values
        high_k_queries = [hash_val for hash_val, k in self.optimal_k_values.items() if k > 10]
        if high_k_queries:
            recommendations.append(f"{len(high_k_queries)} queries use high k values - consider query refinement")
        
        # Analyze complexity
        complex_queries = [(hash_val, complexity) for hash_val, complexity in self.query_complexity_cache.items() if complexity > 0.8]
        if complex_queries:
            recommendations.append(f"{len(complex_queries)} highly complex queries detected - consider query optimization")
        
        return recommendations


def performance_optimize(
    cache_ttl: int = 300,
    track_memory: bool = True,
    optimize_queries: bool = True
):
    """Decorator for comprehensive performance optimization."""
    
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            
            # Generate cache key
            cache_key = None
            if cache_ttl > 0:
                import json
                key_data = {
                    "func": func.__name__,
                    "args": [str(arg) for arg in args[:2]],  # Limit for performance
                    "kwargs": {k: str(v) for k, v in sorted(kwargs.items()) if k not in ["_cache_key"]}
                }
                cache_key = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
            
            # Check cache first
            from graph_rag.api.performance import _global_cache
            cached_result = None
            cache_hit = False
            
            if cache_key and cache_ttl > 0:
                cached_result = _global_cache.get(cache_key)
                if cached_result is not None:
                    cache_hit = True
                    logger.debug(f"Cache hit for {func.__name__}", extra={"cache_key": cache_key})
                    return cached_result
            
            # Performance tracking
            start_time = time.time()
            memory_before = 0.0
            
            if track_memory:
                import psutil
                process = psutil.Process()
                memory_before = process.memory_info().rss / 1024 / 1024
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Cache result
                if cache_key and cache_ttl > 0 and not cache_hit:
                    _global_cache.set(cache_key, result, cache_ttl)
                
                # Track performance
                duration_ms = (time.time() - start_time) * 1000
                
                if track_memory:
                    memory_after = process.memory_info().rss / 1024 / 1024
                    memory_used = memory_after - memory_before
                    
                    logger.info(
                        f"Performance: {func.__name__}",
                        extra={
                            "duration_ms": duration_ms,
                            "memory_used_mb": memory_used,
                            "cache_hit": cache_hit,
                            "cache_key": cache_key
                        }
                    )
                
                return result
                
            except Exception as e:
                logger.error(f"Performance tracking error in {func.__name__}: {e}")
                raise
        
        return wrapper
    return decorator


# Global instances
_global_performance_monitor = AdvancedPerformanceMonitor()
_global_query_optimizer = QueryOptimizer()


def get_performance_monitor() -> AdvancedPerformanceMonitor:
    """Get global performance monitor instance."""
    return _global_performance_monitor


def get_query_optimizer() -> QueryOptimizer:
    """Get global query optimizer instance."""
    return _global_query_optimizer


def get_advanced_performance_stats() -> Dict[str, Any]:
    """Get comprehensive performance statistics."""
    return _global_performance_monitor.get_performance_summary()


def get_optimization_recommendations() -> List[str]:
    """Get performance optimization recommendations."""
    return _global_query_optimizer.get_optimization_recommendations()