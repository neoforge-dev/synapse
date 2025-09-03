"""Performance monitoring for encryption operations to ensure <5ms overhead."""

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric record."""
    operation_type: str
    execution_time: float
    data_size_bytes: int
    timestamp: datetime
    tenant_id: Optional[str] = None


class EncryptionPerformanceMonitor:
    """Monitor encryption performance to ensure sub-5ms overhead compliance."""
    
    # Performance thresholds (in seconds)
    PERFORMANCE_THRESHOLDS = {
        "encryption_max_time": 0.005,    # 5ms max
        "decryption_max_time": 0.005,    # 5ms max
        "search_max_time": 0.010,        # 10ms max for searches
        "key_rotation_max_time": 0.100,  # 100ms max for key operations
        "warning_threshold": 0.004,      # 4ms warning threshold
        "critical_threshold": 0.008      # 8ms critical threshold
    }
    
    def __init__(self, max_metrics_history: int = 10000):
        """Initialize performance monitor."""
        self.max_metrics_history = max_metrics_history
        self.metrics_history: deque = deque(maxlen=max_metrics_history)
        
        # Real-time statistics
        self.current_stats = {
            "total_operations": 0,
            "total_encryption_ops": 0,
            "total_decryption_ops": 0,
            "total_search_ops": 0,
            "total_key_ops": 0,
            "avg_encryption_time": 0.0,
            "avg_decryption_time": 0.0,
            "avg_search_time": 0.0,
            "max_encryption_time": 0.0,
            "max_decryption_time": 0.0,
            "performance_violations": 0,
            "last_violation_time": None
        }
        
        # Performance alerts
        self.performance_alerts: deque = deque(maxlen=1000)
        
        # Tenant-specific metrics
        self.tenant_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "operations": 0,
            "avg_time": 0.0,
            "violations": 0
        })
    
    def record_encryption(self, execution_time: float, data_size: int, 
                         tenant_id: Optional[str] = None):
        """Record encryption operation performance."""
        metric = PerformanceMetric(
            operation_type="encryption",
            execution_time=execution_time,
            data_size_bytes=data_size,
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id
        )
        
        self._record_metric(metric)
        self._check_performance_threshold(metric)
    
    def record_decryption(self, execution_time: float, data_size: int,
                         tenant_id: Optional[str] = None):
        """Record decryption operation performance."""
        metric = PerformanceMetric(
            operation_type="decryption", 
            execution_time=execution_time,
            data_size_bytes=data_size,
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id
        )
        
        self._record_metric(metric)
        self._check_performance_threshold(metric)
    
    def record_search(self, execution_time: float, documents_searched: int, 
                     results_found: int, tenant_id: Optional[str] = None):
        """Record search operation performance."""
        metric = PerformanceMetric(
            operation_type="search",
            execution_time=execution_time,
            data_size_bytes=documents_searched,  # Use as proxy for workload
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id
        )
        
        self._record_metric(metric)
        self._check_performance_threshold(metric)
    
    def record_key_operation(self, operation_name: str, execution_time: float,
                           tenant_id: Optional[str] = None):
        """Record key management operation performance."""
        metric = PerformanceMetric(
            operation_type=f"key_{operation_name}",
            execution_time=execution_time,
            data_size_bytes=0,
            timestamp=datetime.utcnow(), 
            tenant_id=tenant_id
        )
        
        self._record_metric(metric)
        self._check_performance_threshold(metric)
    
    def _record_metric(self, metric: PerformanceMetric):
        """Record metric and update statistics."""
        self.metrics_history.append(metric)
        self._update_statistics(metric)
        
        if metric.tenant_id:
            self._update_tenant_statistics(metric)
    
    def _update_statistics(self, metric: PerformanceMetric):
        """Update real-time statistics."""
        self.current_stats["total_operations"] += 1
        
        if metric.operation_type == "encryption":
            self.current_stats["total_encryption_ops"] += 1
            
            # Update encryption averages
            current_avg = self.current_stats["avg_encryption_time"]
            total_ops = self.current_stats["total_encryption_ops"]
            self.current_stats["avg_encryption_time"] = (
                (current_avg * (total_ops - 1) + metric.execution_time) / total_ops
            )
            
            # Track maximum times
            if metric.execution_time > self.current_stats["max_encryption_time"]:
                self.current_stats["max_encryption_time"] = metric.execution_time
        
        elif metric.operation_type == "decryption":
            self.current_stats["total_decryption_ops"] += 1
            
            current_avg = self.current_stats["avg_decryption_time"]
            total_ops = self.current_stats["total_decryption_ops"]
            self.current_stats["avg_decryption_time"] = (
                (current_avg * (total_ops - 1) + metric.execution_time) / total_ops
            )
            
            if metric.execution_time > self.current_stats["max_decryption_time"]:
                self.current_stats["max_decryption_time"] = metric.execution_time
        
        elif metric.operation_type == "search":
            self.current_stats["total_search_ops"] += 1
            
            current_avg = self.current_stats["avg_search_time"]
            total_ops = self.current_stats["total_search_ops"] 
            self.current_stats["avg_search_time"] = (
                (current_avg * (total_ops - 1) + metric.execution_time) / total_ops
            )
    
    def _update_tenant_statistics(self, metric: PerformanceMetric):
        """Update tenant-specific statistics."""
        tenant_stats = self.tenant_metrics[metric.tenant_id]
        
        tenant_stats["operations"] += 1
        current_avg = tenant_stats["avg_time"]
        total_ops = tenant_stats["operations"]
        
        tenant_stats["avg_time"] = (
            (current_avg * (total_ops - 1) + metric.execution_time) / total_ops
        )
    
    def _check_performance_threshold(self, metric: PerformanceMetric):
        """Check if performance exceeds thresholds and generate alerts."""
        operation_key = f"{metric.operation_type}_max_time"
        threshold = self.PERFORMANCE_THRESHOLDS.get(operation_key, 
                                                   self.PERFORMANCE_THRESHOLDS["encryption_max_time"])
        
        if metric.execution_time > threshold:
            self.current_stats["performance_violations"] += 1
            self.current_stats["last_violation_time"] = metric.timestamp
            
            if metric.tenant_id:
                self.tenant_metrics[metric.tenant_id]["violations"] += 1
            
            # Generate performance alert
            alert = self._create_performance_alert(metric, threshold)
            self.performance_alerts.append(alert)
            
            logger.warning(f"Performance threshold exceeded: {metric.operation_type} "
                         f"took {metric.execution_time*1000:.2f}ms (threshold: {threshold*1000:.1f}ms)")
    
    def _create_performance_alert(self, metric: PerformanceMetric, threshold: float) -> Dict[str, Any]:
        """Create performance alert record."""
        severity = "critical" if metric.execution_time > self.PERFORMANCE_THRESHOLDS["critical_threshold"] else "warning"
        
        return {
            "timestamp": metric.timestamp.isoformat(),
            "tenant_id": metric.tenant_id,
            "operation_type": metric.operation_type,
            "execution_time_ms": metric.execution_time * 1000,
            "threshold_ms": threshold * 1000,
            "data_size_bytes": metric.data_size_bytes,
            "severity": severity,
            "overhead_percentage": ((metric.execution_time - threshold) / threshold) * 100
        }
    
    def get_performance_statistics(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        recent_metrics = self._get_recent_metrics(minutes=5)
        
        stats = self.current_stats.copy()
        
        # Add recent performance trends
        if recent_metrics:
            recent_encryption_times = [m.execution_time for m in recent_metrics 
                                     if m.operation_type == "encryption"]
            recent_decryption_times = [m.execution_time for m in recent_metrics 
                                     if m.operation_type == "decryption"]
            
            if recent_encryption_times:
                stats["recent_avg_encryption_time"] = statistics.mean(recent_encryption_times)
                stats["recent_p95_encryption_time"] = (
                    sorted(recent_encryption_times)[int(len(recent_encryption_times) * 0.95)]
                    if len(recent_encryption_times) > 1 else recent_encryption_times[0]
                )
            
            if recent_decryption_times:
                stats["recent_avg_decryption_time"] = statistics.mean(recent_decryption_times)
                stats["recent_p95_decryption_time"] = (
                    sorted(recent_decryption_times)[int(len(recent_decryption_times) * 0.95)]
                    if len(recent_decryption_times) > 1 else recent_decryption_times[0]
                )
        
        # Performance compliance status
        max_time = max(
            stats.get("max_encryption_time", 0),
            stats.get("max_decryption_time", 0)
        )
        
        stats["compliance_status"] = "compliant" if max_time <= 0.005 else "non_compliant"
        stats["performance_score"] = self._calculate_performance_score(stats)
        
        # Convert times to milliseconds for readability
        for key in stats:
            if "time" in key and isinstance(stats[key], float):
                stats[f"{key}_ms"] = stats[key] * 1000
        
        return stats
    
    def _get_recent_metrics(self, minutes: int = 5) -> List[PerformanceMetric]:
        """Get metrics from the last N minutes."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return [m for m in self.metrics_history if m.timestamp > cutoff_time]
    
    def _calculate_performance_score(self, stats: Dict[str, Any]) -> int:
        """Calculate performance score (0-100) based on compliance."""
        base_score = 100
        
        # Penalize for violations
        violation_rate = (stats["performance_violations"] / max(stats["total_operations"], 1))
        violation_penalty = min(violation_rate * 50, 50)  # Max 50 point penalty
        
        # Penalize for high average times
        avg_encryption_penalty = 0
        if stats["avg_encryption_time"] > 0.003:  # 3ms
            avg_encryption_penalty = min((stats["avg_encryption_time"] - 0.003) * 10000, 25)
        
        avg_decryption_penalty = 0  
        if stats["avg_decryption_time"] > 0.003:
            avg_decryption_penalty = min((stats["avg_decryption_time"] - 0.003) * 10000, 25)
        
        final_score = base_score - violation_penalty - avg_encryption_penalty - avg_decryption_penalty
        return max(int(final_score), 0)
    
    def get_performance_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent performance alerts."""
        return list(self.performance_alerts)[-limit:] if self.performance_alerts else []
    
    def get_tenant_performance_report(self, tenant_id: str) -> Dict[str, Any]:
        """Get performance report for specific tenant."""
        if tenant_id not in self.tenant_metrics:
            return {"tenant_id": tenant_id, "metrics": "no_data"}
        
        tenant_stats = self.tenant_metrics[tenant_id]
        
        # Get tenant-specific recent metrics
        tenant_recent_metrics = [
            m for m in self._get_recent_metrics(minutes=15)
            if m.tenant_id == tenant_id
        ]
        
        report = {
            "tenant_id": tenant_id,
            "total_operations": tenant_stats["operations"],
            "average_time_ms": tenant_stats["avg_time"] * 1000,
            "violations": tenant_stats["violations"],
            "violation_rate": tenant_stats["violations"] / max(tenant_stats["operations"], 1),
            "recent_operations": len(tenant_recent_metrics),
            "compliance_status": "compliant" if tenant_stats["violations"] == 0 else "non_compliant"
        }
        
        if tenant_recent_metrics:
            recent_times = [m.execution_time for m in tenant_recent_metrics]
            report["recent_avg_time_ms"] = statistics.mean(recent_times) * 1000
            report["recent_max_time_ms"] = max(recent_times) * 1000
        
        return report
    
    def reset_metrics(self):
        """Reset all performance metrics (for testing or maintenance)."""
        self.metrics_history.clear()
        self.performance_alerts.clear()
        self.tenant_metrics.clear()
        
        self.current_stats = {
            "total_operations": 0,
            "total_encryption_ops": 0,
            "total_decryption_ops": 0,
            "total_search_ops": 0,
            "total_key_ops": 0,
            "avg_encryption_time": 0.0,
            "avg_decryption_time": 0.0,
            "avg_search_time": 0.0,
            "max_encryption_time": 0.0,
            "max_decryption_time": 0.0,
            "performance_violations": 0,
            "last_violation_time": None
        }
        
        logger.info("Performance metrics reset")
    
    def export_metrics_summary(self) -> Dict[str, Any]:
        """Export comprehensive metrics summary for reporting."""
        return {
            "summary": self.get_performance_statistics(),
            "recent_alerts": self.get_performance_alerts(limit=20),
            "tenant_reports": {
                tenant_id: self.get_tenant_performance_report(tenant_id)
                for tenant_id in list(self.tenant_metrics.keys())[:10]  # Top 10 tenants
            },
            "thresholds": self.PERFORMANCE_THRESHOLDS,
            "export_timestamp": datetime.utcnow().isoformat()
        }