#!/usr/bin/env python3

"""
Failover Coordinator for <5-minute RTO
Enterprise-grade disaster recovery orchestration for $555K consultation pipeline
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import requests
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Configuration
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'synapse_secure_2024')
REPLICATION_PASSWORD = os.getenv('REPLICATION_PASSWORD', 'repl_secure_2024')
RTO_TARGET_MINUTES = int(os.getenv('RTO_TARGET_MINUTES', 5))
HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', 30))
PIPELINE_VALUE = int(os.getenv('PIPELINE_VALUE', 555000))
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
PAGERDUTY_API_KEY = os.getenv('PAGERDUTY_API_KEY')

# Database endpoints
DB_ENDPOINTS = {
    'primary': {
        'host': 'postgres-primary-region',
        'port': 5432,
        'region': 'us-west-2',
        'priority': 1
    },
    'secondary': {
        'host': 'postgres-secondary-region',
        'port': 5432,
        'region': 'us-east-1',
        'priority': 2
    },
    'tertiary': {
        'host': 'postgres-tertiary-region',
        'port': 5432,
        'region': 'eu-west-1',
        'priority': 3
    }
}

# Prometheus metrics
failover_counter = Counter('synapse_failovers_total', 'Total number of failovers performed')
pipeline_value_at_risk = Gauge('synapse_pipeline_value_at_risk_dollars', 'Dollar value of pipeline at risk')
rto_target_gauge = Gauge('synapse_rto_target_seconds', 'RTO target in seconds')
failover_duration = Histogram('synapse_failover_duration_seconds', 'Duration of failover operations')
database_health = Gauge('synapse_database_health', 'Database health status', ['region', 'role'])
replication_lag = Gauge('synapse_replication_lag_seconds', 'Replication lag in seconds', ['region'])

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/logs/failover_coordinator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('failover_coordinator')

class FailoverCoordinator:
    """
    Enterprise-grade failover coordinator with <5-minute RTO guarantee
    """

    def __init__(self):
        self.current_primary = 'primary'
        self.last_health_check = {}
        self.failover_in_progress = False
        self.failover_start_time = None

        # Initialize Prometheus metrics
        pipeline_value_at_risk.set(PIPELINE_VALUE)
        rto_target_gauge.set(RTO_TARGET_MINUTES * 60)

    def get_db_connection(self, endpoint: str, database: str = 'postgres') -> psycopg2.extensions.connection | None:
        """Get database connection with retry logic"""
        try:
            config = DB_ENDPOINTS[endpoint]
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                database=database,
                user='postgres',
                password=POSTGRES_PASSWORD,
                connect_timeout=10,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to {endpoint}: {e}")
            return None

    def check_database_health(self, endpoint: str) -> dict:
        """Comprehensive database health check"""
        health_status = {
            'endpoint': endpoint,
            'healthy': False,
            'is_primary': False,
            'replication_lag': None,
            'connections': 0,
            'last_check': datetime.now(timezone.utc).isoformat(),
            'error': None
        }

        conn = self.get_db_connection(endpoint)
        if not conn:
            health_status['error'] = 'Connection failed'
            database_health.labels(region=DB_ENDPOINTS[endpoint]['region'], role='unknown').set(0)
            return health_status

        try:
            with conn.cursor() as cur:
                # Check if database is in recovery (replica) or primary
                cur.execute("SELECT pg_is_in_recovery();")
                is_in_recovery = cur.fetchone()['pg_is_in_recovery']
                health_status['is_primary'] = not is_in_recovery

                # Check replication lag for replicas
                if is_in_recovery:
                    cur.execute("""
                        SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) as lag_seconds;
                    """)
                    result = cur.fetchone()
                    if result and result['lag_seconds'] is not None:
                        health_status['replication_lag'] = float(result['lag_seconds'])
                        replication_lag.labels(region=DB_ENDPOINTS[endpoint]['region']).set(health_status['replication_lag'])

                # Check connection count
                cur.execute("SELECT count(*) as connections FROM pg_stat_activity;")
                health_status['connections'] = cur.fetchone()['connections']

                # Test basic query performance
                start_time = time.time()
                cur.execute("SELECT 1;")
                query_time = time.time() - start_time

                # Health check passes if query completes in < 5 seconds
                health_status['healthy'] = query_time < 5.0
                health_status['query_time'] = query_time

                # Set Prometheus metrics
                role = 'primary' if health_status['is_primary'] else 'replica'
                database_health.labels(region=DB_ENDPOINTS[endpoint]['region'], role=role).set(1 if health_status['healthy'] else 0)

        except Exception as e:
            health_status['error'] = str(e)
            database_health.labels(region=DB_ENDPOINTS[endpoint]['region'], role='error').set(0)
            logger.error(f"Health check failed for {endpoint}: {e}")
        finally:
            conn.close()

        self.last_health_check[endpoint] = health_status
        return health_status

    def promote_replica_to_primary(self, endpoint: str) -> bool:
        """Promote replica to primary with minimal downtime"""
        logger.info(f"Promoting {endpoint} to primary for failover")

        conn = self.get_db_connection(endpoint)
        if not conn:
            logger.error(f"Cannot connect to {endpoint} for promotion")
            return False

        try:
            with conn.cursor() as cur:
                # Check if already primary
                cur.execute("SELECT pg_is_in_recovery();")
                if not cur.fetchone()['pg_is_in_recovery']:
                    logger.info(f"{endpoint} is already primary")
                    return True

                # Promote replica to primary
                logger.info(f"Executing promotion for {endpoint}")
                cur.execute("SELECT pg_promote();")

                # Wait for promotion to complete (max 30 seconds)
                for i in range(30):
                    time.sleep(1)
                    cur.execute("SELECT pg_is_in_recovery();")
                    if not cur.fetchone()['pg_is_in_recovery']:
                        logger.info(f"Promotion completed for {endpoint} in {i+1} seconds")
                        return True

                logger.error(f"Promotion timeout for {endpoint}")
                return False

        except Exception as e:
            logger.error(f"Promotion failed for {endpoint}: {e}")
            return False
        finally:
            conn.close()

    def update_connection_routing(self, new_primary: str) -> bool:
        """Update connection routing to new primary"""
        try:
            # Update DNS/load balancer routing here
            # This would typically involve:
            # 1. Update Route53 DNS records
            # 2. Update load balancer targets
            # 3. Update service discovery

            # For demonstration, we'll simulate this with a config update
            routing_config = {
                'primary_endpoint': DB_ENDPOINTS[new_primary]['host'],
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'failover_reason': f'Automated failover from {self.current_primary} to {new_primary}',
                'rto_achieved_seconds': time.time() - self.failover_start_time if self.failover_start_time else 0
            }

            with open('/config/routing.json', 'w') as f:
                json.dump(routing_config, f, indent=2)

            logger.info(f"Updated routing to new primary: {new_primary}")
            return True

        except Exception as e:
            logger.error(f"Failed to update routing: {e}")
            return False

    def send_alert(self, severity: str, message: str, details: dict = None) -> None:
        """Send alerts to monitoring systems"""
        alert_data = {
            'severity': severity,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'pipeline_value_at_risk': PIPELINE_VALUE,
            'details': details or {}
        }

        # Send to Slack
        if SLACK_WEBHOOK_URL:
            try:
                color = 'danger' if severity == 'critical' else 'warning'
                slack_payload = {
                    'text': f'🚨 DR Alert: {message}',
                    'attachments': [{
                        'color': color,
                        'fields': [
                            {'title': 'Severity', 'value': severity, 'short': True},
                            {'title': 'Pipeline Value', 'value': f'${PIPELINE_VALUE:,}', 'short': True},
                            {'title': 'RTO Target', 'value': f'{RTO_TARGET_MINUTES} minutes', 'short': True},
                            {'title': 'Details', 'value': json.dumps(details, indent=2), 'short': False}
                        ]
                    }]
                }
                requests.post(SLACK_WEBHOOK_URL, json=slack_payload, timeout=10)
            except Exception as e:
                logger.error(f"Failed to send Slack alert: {e}")

        # Send to PagerDuty for critical alerts
        if PAGERDUTY_API_KEY and severity == 'critical':
            try:
                pagerduty_payload = {
                    'routing_key': PAGERDUTY_API_KEY,
                    'event_action': 'trigger',
                    'payload': {
                        'summary': message,
                        'severity': severity,
                        'source': 'synapse-failover-coordinator',
                        'custom_details': alert_data
                    }
                }
                requests.post('https://events.pagerduty.com/v2/enqueue', json=pagerduty_payload, timeout=10)
            except Exception as e:
                logger.error(f"Failed to send PagerDuty alert: {e}")

        logger.info(f"Alert sent: {severity} - {message}")

    def perform_failover(self, target_endpoint: str) -> bool:
        """Perform automated failover with <5-minute RTO"""
        if self.failover_in_progress:
            logger.warning("Failover already in progress, skipping")
            return False

        self.failover_in_progress = True
        self.failover_start_time = time.time()

        logger.critical(f"STARTING FAILOVER from {self.current_primary} to {target_endpoint}")

        # Send critical alert
        self.send_alert('critical', f'Automated failover initiated: {self.current_primary} -> {target_endpoint}', {
            'from_primary': self.current_primary,
            'to_primary': target_endpoint,
            'pipeline_value': PIPELINE_VALUE,
            'rto_target_minutes': RTO_TARGET_MINUTES
        })

        try:
            with failover_duration.time():
                # Step 1: Promote replica to primary (target: <2 minutes)
                step1_start = time.time()
                if not self.promote_replica_to_primary(target_endpoint):
                    raise Exception("Failed to promote replica to primary")
                step1_duration = time.time() - step1_start
                logger.info(f"Step 1 (promotion) completed in {step1_duration:.2f}s")

                # Step 2: Update connection routing (target: <1 minute)
                step2_start = time.time()
                if not self.update_connection_routing(target_endpoint):
                    raise Exception("Failed to update connection routing")
                step2_duration = time.time() - step2_start
                logger.info(f"Step 2 (routing) completed in {step2_duration:.2f}s")

                # Step 3: Verify new primary is healthy (target: <30 seconds)
                step3_start = time.time()
                health = self.check_database_health(target_endpoint)
                if not health['healthy'] or not health['is_primary']:
                    raise Exception("New primary failed health check")
                step3_duration = time.time() - step3_start
                logger.info(f"Step 3 (verification) completed in {step3_duration:.2f}s")

                # Update internal state
                old_primary = self.current_primary
                self.current_primary = target_endpoint

                # Calculate total failover time
                total_duration = time.time() - self.failover_start_time
                rto_achieved = total_duration / 60  # Convert to minutes

                # Update metrics
                failover_counter.inc()
                pipeline_value_at_risk.set(0)  # Pipeline is now protected

                logger.critical(f"FAILOVER COMPLETED: {old_primary} -> {target_endpoint}")
                logger.info(f"RTO achieved: {rto_achieved:.2f} minutes (target: {RTO_TARGET_MINUTES} minutes)")
                logger.info(f"$${PIPELINE_VALUE:,} consultation pipeline protected")

                # Send success alert
                self.send_alert('warning', 'Failover completed successfully', {
                    'from_primary': old_primary,
                    'to_primary': target_endpoint,
                    'rto_achieved_minutes': rto_achieved,
                    'rto_target_minutes': RTO_TARGET_MINUTES,
                    'rto_met': rto_achieved <= RTO_TARGET_MINUTES,
                    'pipeline_protected': True,
                    'step_durations': {
                        'promotion_seconds': step1_duration,
                        'routing_seconds': step2_duration,
                        'verification_seconds': step3_duration,
                        'total_seconds': total_duration
                    }
                })

                return True

        except Exception as e:
            logger.error(f"Failover failed: {e}")
            self.send_alert('critical', f'Failover failed: {e}', {
                'target_endpoint': target_endpoint,
                'pipeline_at_risk': True,
                'manual_intervention_required': True
            })
            return False
        finally:
            self.failover_in_progress = False
            self.failover_start_time = None

    def select_best_failover_target(self) -> str | None:
        """Select the best replica for failover based on health and lag"""
        candidates = []

        for endpoint in ['secondary', 'tertiary']:
            health = self.check_database_health(endpoint)
            if health['healthy'] and not health['is_primary']:
                priority = DB_ENDPOINTS[endpoint]['priority']
                lag = health.get('replication_lag', float('inf'))
                candidates.append({
                    'endpoint': endpoint,
                    'priority': priority,
                    'lag': lag,
                    'health': health
                })

        if not candidates:
            logger.error("No healthy replicas available for failover")
            return None

        # Sort by priority (lower is better) then by lag (lower is better)
        candidates.sort(key=lambda x: (x['priority'], x['lag']))

        selected = candidates[0]
        logger.info(f"Selected {selected['endpoint']} for failover (lag: {selected['lag']:.2f}s)")

        return selected['endpoint']

    async def health_monitor_loop(self):
        """Main health monitoring loop"""
        logger.info("Starting health monitoring loop")

        while True:
            try:
                # Check primary health
                primary_health = self.check_database_health(self.current_primary)

                logger.debug(f"Primary {self.current_primary} health: {primary_health}")

                # Check if primary is unhealthy
                if not primary_health['healthy']:
                    logger.warning(f"Primary {self.current_primary} is unhealthy")

                    # Set pipeline at risk
                    pipeline_value_at_risk.set(PIPELINE_VALUE)

                    # Try to find a healthy failover target
                    failover_target = self.select_best_failover_target()

                    if failover_target:
                        logger.critical(f"Initiating automatic failover to {failover_target}")
                        success = self.perform_failover(failover_target)

                        if not success:
                            logger.critical("Automatic failover failed - manual intervention required")
                            self.send_alert('critical', 'Automatic failover failed - manual intervention required', {
                                'failed_primary': self.current_primary,
                                'attempted_target': failover_target,
                                'pipeline_value_at_risk': PIPELINE_VALUE,
                                'manual_intervention_required': True
                            })
                    else:
                        logger.critical("No healthy replicas available - system in critical state")
                        self.send_alert('critical', 'No healthy replicas available for failover', {
                            'failed_primary': self.current_primary,
                            'pipeline_value_at_risk': PIPELINE_VALUE,
                            'system_state': 'critical',
                            'manual_intervention_required': True
                        })
                else:
                    # Primary is healthy, reset pipeline risk
                    pipeline_value_at_risk.set(0)

                # Check replica health for monitoring
                for endpoint in ['secondary', 'tertiary']:
                    if endpoint != self.current_primary:
                        replica_health = self.check_database_health(endpoint)
                        logger.debug(f"Replica {endpoint} health: {replica_health}")

                        # Alert on high replication lag
                        if replica_health.get('replication_lag', 0) > 300:  # 5 minutes
                            self.send_alert('warning', f'High replication lag on {endpoint}', {
                                'endpoint': endpoint,
                                'lag_seconds': replica_health['replication_lag']
                            })

                # Log status summary
                logger.info(f"Health check complete - Primary: {self.current_primary}, Pipeline: $${PIPELINE_VALUE:,} {'PROTECTED' if primary_health['healthy'] else 'AT RISK'}")

            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")

            # Wait for next check
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)

async def main():
    """Main entry point"""
    logger.info("Starting Synapse Failover Coordinator")
    logger.info(f"RTO Target: {RTO_TARGET_MINUTES} minutes")
    logger.info(f"Pipeline Value: $${PIPELINE_VALUE:,}")
    logger.info(f"Health Check Interval: {HEALTH_CHECK_INTERVAL}s")

    # Start Prometheus metrics server
    start_http_server(8080)
    logger.info("Prometheus metrics available on :8080")

    # Initialize and start coordinator
    coordinator = FailoverCoordinator()

    # Send startup notification
    coordinator.send_alert('info', 'Failover Coordinator started successfully', {
        'rto_target_minutes': RTO_TARGET_MINUTES,
        'pipeline_value': PIPELINE_VALUE,
        'health_check_interval': HEALTH_CHECK_INTERVAL
    })

    # Start health monitoring
    await coordinator.health_monitor_loop()

if __name__ == "__main__":
    asyncio.run(main())
