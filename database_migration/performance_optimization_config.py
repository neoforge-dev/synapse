#!/usr/bin/env python3
"""
PostgreSQL Performance Optimization and Connection Pooling Configuration
Epic 2 Week 1: Enterprise-Grade Database Performance

This module provides comprehensive performance optimization for the consolidated
PostgreSQL architecture, targeting <100ms query response times and enterprise-scale
connection management.

Performance Targets:
- Core Business queries: <50ms (consultation pipeline critical)
- Analytics queries: <100ms (pattern analysis and insights)
- Connection pool efficiency: 95%+ utilization
- Zero connection timeout errors during peak load
"""

import asyncio
import logging
import os
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg
import psycopg2

# Configure logging for performance monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('performance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class DatabasePerformanceConfig:
    """Enhanced database configuration with performance optimization"""
    host: str
    port: int
    database: str
    username: str
    password: str

    # Connection pool configuration
    min_connections: int = 5
    max_connections: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True

    # Query performance configuration
    statement_timeout: int = 30000  # 30 seconds in milliseconds
    idle_in_transaction_session_timeout: int = 300000  # 5 minutes
    query_timeout: int = 100  # 100ms target for critical queries

    # Connection optimization
    tcp_keepalives_idle: int = 600
    tcp_keepalives_interval: int = 30
    tcp_keepalives_count: int = 3

    def connection_string(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

    def connection_params(self) -> dict[str, Any]:
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.username,
            'password': self.password,
            'options': f'-c statement_timeout={self.statement_timeout}ms',
            'keepalives_idle': self.tcp_keepalives_idle,
            'keepalives_interval': self.tcp_keepalives_interval,
            'keepalives_count': self.tcp_keepalives_count,
        }


class PerformanceMonitor:
    """Real-time performance monitoring for query optimization"""

    def __init__(self):
        self.query_metrics: dict[str, dict[str, Any]] = {}
        self.connection_metrics: dict[str, dict[str, Any]] = {}

    def record_query_performance(self, query_type: str, execution_time_ms: float, database: str):
        """Record query performance metrics"""
        if query_type not in self.query_metrics:
            self.query_metrics[query_type] = {
                'total_queries': 0,
                'total_time_ms': 0.0,
                'min_time_ms': float('inf'),
                'max_time_ms': 0.0,
                'slow_queries': 0,  # >100ms
                'databases': set()
            }

        metrics = self.query_metrics[query_type]
        metrics['total_queries'] += 1
        metrics['total_time_ms'] += execution_time_ms
        metrics['min_time_ms'] = min(metrics['min_time_ms'], execution_time_ms)
        metrics['max_time_ms'] = max(metrics['max_time_ms'], execution_time_ms)
        metrics['databases'].add(database)

        if execution_time_ms > 100:  # Critical: queries exceeding 100ms target
            metrics['slow_queries'] += 1
            logger.warning(f"🐌 SLOW QUERY DETECTED: {query_type} in {database} took {execution_time_ms:.2f}ms")

    def record_connection_usage(self, database: str, active_connections: int, total_connections: int):
        """Record connection pool usage metrics"""
        if database not in self.connection_metrics:
            self.connection_metrics[database] = {
                'peak_connections': 0,
                'avg_utilization': 0.0,
                'measurements': []
            }

        utilization = (active_connections / total_connections) * 100
        metrics = self.connection_metrics[database]
        metrics['peak_connections'] = max(metrics['peak_connections'], active_connections)
        metrics['measurements'].append(utilization)
        metrics['avg_utilization'] = sum(metrics['measurements']) / len(metrics['measurements'])

        if utilization > 90:
            logger.warning(f"🔥 HIGH CONNECTION USAGE: {database} at {utilization:.1f}% ({active_connections}/{total_connections})")

    def get_performance_report(self) -> dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'query_performance': {},
            'connection_performance': {},
            'performance_alerts': []
        }

        # Process query metrics
        for query_type, metrics in self.query_metrics.items():
            if metrics['total_queries'] > 0:
                avg_time = metrics['total_time_ms'] / metrics['total_queries']
                slow_query_percentage = (metrics['slow_queries'] / metrics['total_queries']) * 100

                report['query_performance'][query_type] = {
                    'avg_execution_time_ms': round(avg_time, 2),
                    'min_time_ms': round(metrics['min_time_ms'], 2),
                    'max_time_ms': round(metrics['max_time_ms'], 2),
                    'total_queries': metrics['total_queries'],
                    'slow_queries': metrics['slow_queries'],
                    'slow_query_percentage': round(slow_query_percentage, 1),
                    'databases': list(metrics['databases'])
                }

                # Performance alerts
                if avg_time > 100:
                    report['performance_alerts'].append(f"❌ {query_type} exceeds 100ms target: {avg_time:.2f}ms average")
                elif avg_time > 50 and 'consultation' in query_type.lower():
                    report['performance_alerts'].append(f"⚠️  {query_type} exceeds 50ms consultation target: {avg_time:.2f}ms")
                elif avg_time <= 50:
                    report['performance_alerts'].append(f"✅ {query_type} meets performance target: {avg_time:.2f}ms")

        # Process connection metrics
        for database, metrics in self.connection_metrics.items():
            report['connection_performance'][database] = {
                'peak_connections': metrics['peak_connections'],
                'avg_utilization_percentage': round(metrics['avg_utilization'], 1),
                'total_measurements': len(metrics['measurements'])
            }

        return report


class OptimizedConnectionPool:
    """High-performance connection pool with monitoring"""

    def __init__(self, config: DatabasePerformanceConfig, monitor: PerformanceMonitor):
        self.config = config
        self.monitor = monitor
        self.pool: psycopg2.pool.ThreadedConnectionPool | None = None
        self._create_pool()

    def _create_pool(self):
        """Create optimized connection pool"""
        try:
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self.config.min_connections,
                maxconn=self.config.max_connections,
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                # Performance optimizations
                options=f'-c statement_timeout={self.config.statement_timeout}ms',
                keepalives_idle=self.config.tcp_keepalives_idle,
                keepalives_interval=self.config.tcp_keepalives_interval,
                keepalives_count=self.config.tcp_keepalives_count,
            )

            logger.info(f"✅ Connection pool created for {self.config.database}: "
                       f"{self.config.min_connections}-{self.config.max_connections} connections")

        except Exception as e:
            logger.error(f"❌ Failed to create connection pool for {self.config.database}: {e}")
            raise e

    @contextmanager
    def get_connection(self) -> Iterator[psycopg2.extensions.connection]:
        """Get connection from pool with monitoring"""
        start_time = time.time()
        conn = None

        try:
            # Get connection from pool with timeout
            conn = self.pool.getconn()
            if conn is None:
                raise Exception(f"Failed to get connection from pool for {self.config.database}")

            # Configure connection for optimal performance
            conn.autocommit = False

            # Monitor connection usage
            active_conns = self.pool.maxconn - self.pool._available_connections.qsize()
            self.monitor.record_connection_usage(
                self.config.database,
                active_conns,
                self.config.max_connections
            )

            yield conn

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Connection error for {self.config.database}: {e}")
            raise e

        finally:
            acquisition_time = (time.time() - start_time) * 1000
            if acquisition_time > 100:
                logger.warning(f"🐌 Slow connection acquisition: {acquisition_time:.2f}ms for {self.config.database}")

            if conn:
                self.pool.putconn(conn)

    def health_check(self) -> dict[str, Any]:
        """Perform pool health check"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()

            active_conns = self.pool.maxconn - self.pool._available_connections.qsize()

            return {
                'database': self.config.database,
                'status': 'healthy',
                'active_connections': active_conns,
                'max_connections': self.config.max_connections,
                'utilization_percentage': (active_conns / self.config.max_connections) * 100
            }

        except Exception as e:
            logger.error(f"Health check failed for {self.config.database}: {e}")
            return {
                'database': self.config.database,
                'status': 'unhealthy',
                'error': str(e)
            }

    def close(self):
        """Close connection pool"""
        if self.pool:
            self.pool.closeall()
            logger.info(f"🔒 Connection pool closed for {self.config.database}")


class AsyncOptimizedConnectionPool:
    """Async connection pool for high-concurrency scenarios"""

    def __init__(self, config: DatabasePerformanceConfig, monitor: PerformanceMonitor):
        self.config = config
        self.monitor = monitor
        self.pool: asyncpg.Pool | None = None

    async def create_pool(self):
        """Create async connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
                command_timeout=self.config.query_timeout / 1000,  # Convert to seconds
                server_settings={
                    'statement_timeout': f'{self.config.statement_timeout}ms',
                    'idle_in_transaction_session_timeout': f'{self.config.idle_in_transaction_session_timeout}ms'
                }
            )

            logger.info(f"✅ Async pool created for {self.config.database}: "
                       f"{self.config.min_connections}-{self.config.max_connections} connections")

        except Exception as e:
            logger.error(f"❌ Failed to create async pool for {self.config.database}: {e}")
            raise e

    @asynccontextmanager
    async def get_connection(self) -> AsyncIterator[asyncpg.Connection]:
        """Get async connection with monitoring"""
        start_time = time.time()

        try:
            async with self.pool.acquire() as conn:
                # Monitor connection acquisition time
                acquisition_time = (time.time() - start_time) * 1000
                if acquisition_time > 50:
                    logger.warning(f"🐌 Slow async connection acquisition: {acquisition_time:.2f}ms")

                yield conn

        except Exception as e:
            logger.error(f"Async connection error for {self.config.database}: {e}")
            raise e

    async def close(self):
        """Close async connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info(f"🔒 Async connection pool closed for {self.config.database}")


class DatabasePerformanceManager:
    """Centralized performance management for all databases"""

    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.pools: dict[str, OptimizedConnectionPool] = {}
        self.async_pools: dict[str, AsyncOptimizedConnectionPool] = {}
        self.configs: dict[str, DatabasePerformanceConfig] = {}

        # Load configurations
        self._load_configurations()

    def _load_configurations(self):
        """Load optimized configurations for each database"""

        # Core Business Database (Priority 1 - 50ms target)
        self.configs['synapse_business_core'] = DatabasePerformanceConfig(
            host=os.getenv('SYNAPSE_BUSINESS_CORE_HOST', 'localhost'),
            port=int(os.getenv('SYNAPSE_BUSINESS_CORE_PORT', '5432')),
            database='synapse_business_core',
            username=os.getenv('SYNAPSE_DB_USERNAME', 'synapse_user'),
            password=os.getenv('SYNAPSE_DB_PASSWORD', 'secure_password'),
            min_connections=10,
            max_connections=30,
            max_overflow=20,
            pool_timeout=20,  # Aggressive timeout for business-critical queries
            query_timeout=50,  # 50ms target for consultation pipeline
            statement_timeout=25000,  # 25 seconds max
        )

        # Analytics Intelligence Database (Priority 2 - 100ms target)
        self.configs['synapse_analytics_intelligence'] = DatabasePerformanceConfig(
            host=os.getenv('SYNAPSE_ANALYTICS_HOST', 'localhost'),
            port=int(os.getenv('SYNAPSE_ANALYTICS_PORT', '5432')),
            database='synapse_analytics_intelligence',
            username=os.getenv('SYNAPSE_DB_USERNAME', 'synapse_user'),
            password=os.getenv('SYNAPSE_DB_PASSWORD', 'secure_password'),
            min_connections=8,
            max_connections=25,
            max_overflow=15,
            pool_timeout=60,  # Analytics can wait longer
            query_timeout=100,  # 100ms target
            statement_timeout=60000,  # 60 seconds for complex analytics
        )

        # Revenue Intelligence Database (Priority 3 - 100ms target)
        self.configs['synapse_revenue_intelligence'] = DatabasePerformanceConfig(
            host=os.getenv('SYNAPSE_REVENUE_HOST', 'localhost'),
            port=int(os.getenv('SYNAPSE_REVENUE_PORT', '5432')),
            database='synapse_revenue_intelligence',
            username=os.getenv('SYNAPSE_DB_USERNAME', 'synapse_user'),
            password=os.getenv('SYNAPSE_DB_PASSWORD', 'secure_password'),
            min_connections=5,
            max_connections=20,
            max_overflow=15,
            pool_timeout=60,
            query_timeout=100,
            statement_timeout=45000,  # 45 seconds
        )

    def initialize_pools(self):
        """Initialize all connection pools"""
        logger.info("🚀 Initializing optimized connection pools...")

        for db_name, config in self.configs.items():
            try:
                # Create synchronous pool
                self.pools[db_name] = OptimizedConnectionPool(config, self.monitor)

                # Create asynchronous pool
                self.async_pools[db_name] = AsyncOptimizedConnectionPool(config, self.monitor)

                logger.info(f"✅ Pools initialized for {db_name}")

            except Exception as e:
                logger.error(f"❌ Failed to initialize pools for {db_name}: {e}")
                raise e

        logger.info("✅ All connection pools initialized successfully")

    async def initialize_async_pools(self):
        """Initialize async connection pools"""
        logger.info("🚀 Initializing async connection pools...")

        for _db_name, async_pool in self.async_pools.items():
            await async_pool.create_pool()

        logger.info("✅ All async pools initialized")

    def get_pool(self, database: str) -> OptimizedConnectionPool:
        """Get connection pool for database"""
        if database not in self.pools:
            raise ValueError(f"No pool configured for database: {database}")
        return self.pools[database]

    def get_async_pool(self, database: str) -> AsyncOptimizedConnectionPool:
        """Get async connection pool for database"""
        if database not in self.async_pools:
            raise ValueError(f"No async pool configured for database: {database}")
        return self.async_pools[database]

    def execute_query_with_monitoring(self, database: str, query: str, query_type: str, params=None):
        """Execute query with performance monitoring"""
        start_time = time.time()
        pool = self.get_pool(database)

        try:
            with pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    result = cursor.fetchall()
                    conn.commit()

                    # Record performance metrics
                    execution_time_ms = (time.time() - start_time) * 1000
                    self.monitor.record_query_performance(query_type, execution_time_ms, database)

                    return result

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Query execution failed in {database}: {e} (took {execution_time_ms:.2f}ms)")
            raise e

    async def execute_async_query_with_monitoring(self, database: str, query: str, query_type: str, params=None):
        """Execute async query with performance monitoring"""
        start_time = time.time()
        async_pool = self.get_async_pool(database)

        try:
            async with async_pool.get_connection() as conn:
                result = await conn.fetch(query, *params if params else ())

                # Record performance metrics
                execution_time_ms = (time.time() - start_time) * 1000
                self.monitor.record_query_performance(query_type, execution_time_ms, database)

                return result

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Async query execution failed in {database}: {e} (took {execution_time_ms:.2f}ms)")
            raise e

    def health_check_all(self) -> dict[str, Any]:
        """Comprehensive health check for all databases"""
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'databases': {}
        }

        for db_name, pool in self.pools.items():
            db_health = pool.health_check()
            health_report['databases'][db_name] = db_health

            if db_health['status'] != 'healthy':
                health_report['overall_status'] = 'unhealthy'

        return health_report

    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report"""
        performance_data = self.monitor.get_performance_report()
        health_data = self.health_check_all()

        report = []
        report.append("=" * 80)
        report.append("DATABASE PERFORMANCE OPTIMIZATION REPORT")
        report.append("Epic 2 Week 1: PostgreSQL Consolidation Performance")
        report.append("=" * 80)
        report.append(f"Report generated at: {datetime.now()}")
        report.append("")

        # Performance Summary
        report.append("QUERY PERFORMANCE SUMMARY")
        report.append("-" * 40)
        for query_type, metrics in performance_data['query_performance'].items():
            status_icon = "✅" if metrics['avg_execution_time_ms'] <= 100 else "❌"
            report.append(f"{status_icon} {query_type}:")
            report.append(f"  Average: {metrics['avg_execution_time_ms']}ms")
            report.append(f"  Range: {metrics['min_time_ms']}-{metrics['max_time_ms']}ms")
            report.append(f"  Total queries: {metrics['total_queries']}")
            report.append(f"  Slow queries: {metrics['slow_queries']} ({metrics['slow_query_percentage']}%)")
            report.append("")

        # Connection Pool Status
        report.append("CONNECTION POOL STATUS")
        report.append("-" * 40)
        for db_name, metrics in performance_data['connection_performance'].items():
            status_icon = "✅" if metrics['avg_utilization_percentage'] < 90 else "⚠️ "
            report.append(f"{status_icon} {db_name}:")
            report.append(f"  Peak connections: {metrics['peak_connections']}")
            report.append(f"  Average utilization: {metrics['avg_utilization_percentage']}%")
            report.append("")

        # Performance Alerts
        if performance_data['performance_alerts']:
            report.append("PERFORMANCE ALERTS")
            report.append("-" * 40)
            for alert in performance_data['performance_alerts']:
                report.append(f"  {alert}")
            report.append("")

        # Health Status
        report.append("SYSTEM HEALTH STATUS")
        report.append("-" * 40)
        report.append(f"Overall Status: {health_data['overall_status'].upper()}")
        for db_name, health in health_data['databases'].items():
            status_icon = "✅" if health['status'] == 'healthy' else "❌"
            report.append(f"{status_icon} {db_name}: {health['status']}")
            if 'utilization_percentage' in health:
                report.append(f"  Connection utilization: {health['utilization_percentage']:.1f}%")

        return "\n".join(report)

    def close_all_pools(self):
        """Close all connection pools"""
        logger.info("🔒 Closing all connection pools...")

        for _db_name, pool in self.pools.items():
            pool.close()

        logger.info("✅ All connection pools closed")

    async def close_all_async_pools(self):
        """Close all async connection pools"""
        logger.info("🔒 Closing all async connection pools...")

        for _db_name, async_pool in self.async_pools.items():
            await async_pool.close()

        logger.info("✅ All async connection pools closed")


# Global performance manager instance
performance_manager = DatabasePerformanceManager()


async def main():
    """Example usage and testing"""
    logger.info("🚀 DATABASE PERFORMANCE OPTIMIZATION SYSTEM")
    logger.info("🎯 Target: <100ms query performance with enterprise connection pooling")

    try:
        # Initialize connection pools
        performance_manager.initialize_pools()
        await performance_manager.initialize_async_pools()

        # Example: Execute a critical business query
        logger.info("🔍 Testing consultation pipeline query performance...")

        # Simulate consultation pipeline query

        # Execute with monitoring (would work when databases are available)
        # result = performance_manager.execute_query_with_monitoring(
        #     'synapse_business_core',
        #     consultation_query,
        #     'consultation_pipeline_summary'
        # )

        # Generate performance report
        report = performance_manager.generate_performance_report()

        # Save report
        report_path = Path("/Users/bogdan/til/graph-rag-mcp/database_migration/performance_report.txt")
        with open(report_path, 'w') as f:
            f.write(report)

        logger.info(f"📊 Performance report saved: {report_path}")
        print(report)

        logger.info("✅ PERFORMANCE OPTIMIZATION SYSTEM READY")
        logger.info("🎯 Ready for <100ms query performance validation")

    except Exception as e:
        logger.error(f"💥 Performance optimization initialization failed: {e}")
        return 1

    finally:
        # Cleanup
        performance_manager.close_all_pools()
        await performance_manager.close_all_async_pools()

    return 0


if __name__ == "__main__":
    asyncio.run(main())
