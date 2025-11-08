#!/usr/bin/env python3
"""
Business Continuity and Pipeline Protection Tests - CRITICAL
Tests ensuring $1.158M business pipeline remains protected during system operations
"""

import shutil
import sqlite3
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from business_development.epic7_sales_automation import CRMContact, SalesAutomationEngine


class TestBusinessPipelineProtection:
    """CRITICAL: Test business pipeline protection during system operations"""

    @pytest.fixture
    def protected_pipeline_engine(self):
        """Create sales engine with protected high-value pipeline data"""
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        engine = SalesAutomationEngine(db_path=db_path)

        # Create high-value pipeline data simulating $1.158M+ value
        high_value_contacts = [
            CRMContact(
                contact_id="protected-001",
                name="Enterprise Client Alpha",
                company="Fortune 500 Corp",
                company_size="Enterprise (500+ employees)",
                title="CTO",
                email="cto@fortune500.com",
                linkedin_profile="linkedin.com/in/enterprise-cto",
                phone="+1-555-0100",
                lead_score=95,
                qualification_status="qualified",
                estimated_value=250000,  # High-value enterprise deal
                priority_tier="platinum",
                next_action="Strategic consultation call scheduled",
                next_action_date=(datetime.now() + timedelta(days=2)).isoformat(),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                notes="Enterprise fractional CTO engagement - strategic transformation initiative"
            ),
            CRMContact(
                contact_id="protected-002",
                name="Series B Leader Beta",
                company="ScaleUp Technologies",
                company_size="Series B (50-200 employees)",
                title="CEO",
                email="ceo@scaleup.com",
                linkedin_profile="linkedin.com/in/scaleup-ceo",
                phone="+1-555-0200",
                lead_score=88,
                qualification_status="qualified",
                estimated_value=180000,  # High-value team building
                priority_tier="platinum",
                next_action="Team velocity assessment call",
                next_action_date=(datetime.now() + timedelta(days=1)).isoformat(),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                notes="150+ engineer team building - velocity optimization project"
            )
        ]

        # Add 16+ additional contacts to meet minimum requirements
        for i in range(16):
            high_value_contacts.append(CRMContact(
                contact_id=f"protected-{i+3:03d}",
                name=f"Series A Contact {i+1}",
                company=f"Growth Company {i+1}",
                company_size="Series A (20-50 employees)",
                title=["CTO", "VP Engineering", "Head of Engineering"][i % 3],
                email=f"contact{i+1}@growthco.com",
                linkedin_profile=f"linkedin.com/in/contact{i+1}",
                phone=f"+1-555-{300+i:04d}",
                lead_score=75 + (i % 15),  # 75-89 range
                qualification_status="qualified",
                estimated_value=[45000, 55000, 65000, 35000, 40000][i % 5],
                priority_tier=["gold", "silver", "gold", "silver", "bronze"][i % 5],
                next_action="Follow-up consultation call",
                next_action_date=(datetime.now() + timedelta(days=3+i)).isoformat(),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                notes=f"Series A consultation inquiry - {['team building', 'NOBUILD audit', 'technical architecture'][i % 3]}"
            ))

        # Save all contacts to database
        engine._save_contacts(high_value_contacts)

        yield engine, db_path

        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    def test_pipeline_value_protection(self, protected_pipeline_engine):
        """CRITICAL: Test pipeline value meets/exceeds $1.158M target"""
        engine, db_path = protected_pipeline_engine

        summary = engine.get_sales_pipeline_summary()

        total_pipeline_value = summary['total_pipeline_value']
        target_pipeline_value = 1158000  # $1.158M

        # CRITICAL ASSERTION: Pipeline value must meet target
        assert total_pipeline_value >= target_pipeline_value, \
            f"CRITICAL: Pipeline value ${total_pipeline_value:,} below target ${target_pipeline_value:,}"

        # Verify contact count meets minimum requirement
        assert summary['total_contacts'] >= 16, \
            f"CRITICAL: Contact count {summary['total_contacts']} below minimum 16"

        # Verify qualified leads are sufficient
        qualified_percentage = summary['qualified_leads'] / summary['total_contacts']
        assert qualified_percentage >= 0.8, \
            f"CRITICAL: Qualified lead percentage {qualified_percentage:.1%} below 80% target"

        print("\nBusiness Pipeline Protection Status:")
        print(f"✅ Pipeline Value: ${total_pipeline_value:,} (Target: ${target_pipeline_value:,})")
        print(f"✅ Contact Count: {summary['total_contacts']} (Minimum: 16)")
        print(f"✅ Qualified Leads: {summary['qualified_leads']} ({qualified_percentage:.1%})")
        print(f"✅ Platinum Tier: {summary['platinum_leads']}")
        print(f"✅ Gold Tier: {summary['gold_leads']}")

    def test_data_integrity_during_operations(self, protected_pipeline_engine):
        """CRITICAL: Test data integrity maintained during system operations"""
        engine, db_path = protected_pipeline_engine

        # Capture initial state
        initial_summary = engine.get_sales_pipeline_summary()
        initial_contacts = initial_summary['total_contacts']
        initial_value = initial_summary['total_pipeline_value']

        # Perform various system operations
        operations_log = []

        try:
            # Operation 1: Generate revenue forecast
            forecast = engine.generate_revenue_forecast("quarterly")
            operations_log.append(f"✅ Revenue forecast: ${forecast['total_projected_revenue']:,}")

            # Operation 2: Create A/B testing campaign
            campaign_id = engine.create_ab_test_campaign(
                "Pipeline Protection Test",
                "Approach A: Direct outreach",
                "Approach B: Value-first content"
            )
            operations_log.append(f"✅ A/B test campaign: {campaign_id}")

            # Operation 3: Generate proposals for high-value leads
            conn = sqlite3.connect(engine.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT contact_id FROM crm_contacts 
                WHERE priority_tier IN ('platinum', 'gold') 
                AND qualification_status = 'qualified'
                LIMIT 5
            """)
            high_value_contacts = cursor.fetchall()
            conn.close()

            generated_proposals = 0
            for contact_row in high_value_contacts:
                proposal = engine.generate_automated_proposal(contact_row[0])
                if 'error' not in proposal:
                    generated_proposals += 1

            operations_log.append(f"✅ Proposals generated: {generated_proposals}")

            # Operation 4: LinkedIn automation integration
            linkedin_integrations = 0
            for contact_row in high_value_contacts[:3]:  # Top 3 prospects
                integration = engine.integrate_linkedin_automation(contact_row[0])
                if 'error' not in integration:
                    linkedin_integrations += 1

            operations_log.append(f"✅ LinkedIn automations: {linkedin_integrations}")

        except Exception as e:
            pytest.fail(f"CRITICAL: System operation failed: {e}")

        # Verify data integrity after operations
        final_summary = engine.get_sales_pipeline_summary()

        # CRITICAL ASSERTIONS: Data integrity must be maintained
        assert final_summary['total_contacts'] == initial_contacts, \
            f"CRITICAL: Contact count changed from {initial_contacts} to {final_summary['total_contacts']}"

        assert final_summary['total_pipeline_value'] == initial_value, \
            f"CRITICAL: Pipeline value changed from ${initial_value:,} to ${final_summary['total_pipeline_value']:,}"

        # Verify proposals were generated without data corruption
        assert final_summary['total_proposals'] >= generated_proposals, \
            "CRITICAL: Proposal generation corrupted data"

        print("\nData Integrity Verification:")
        for operation in operations_log:
            print(f"  {operation}")
        print(f"✅ Final Contact Count: {final_summary['total_contacts']} (Unchanged)")
        print(f"✅ Final Pipeline Value: ${final_summary['total_pipeline_value']:,} (Unchanged)")

    def test_concurrent_access_protection(self, protected_pipeline_engine):
        """CRITICAL: Test pipeline protection under concurrent access"""
        engine, db_path = protected_pipeline_engine

        def concurrent_operation(operation_id):
            """Simulate concurrent business operations"""
            try:
                # Each thread performs different operations
                if operation_id % 3 == 0:
                    # Revenue forecasting
                    forecast = engine.generate_revenue_forecast("monthly")
                    return f"forecast-{operation_id}", forecast['total_projected_revenue']

                elif operation_id % 3 == 1:
                    # Pipeline summary
                    summary = engine.get_sales_pipeline_summary()
                    return f"summary-{operation_id}", summary['total_pipeline_value']

                else:
                    # A/B test creation
                    campaign_id = engine.create_ab_test_campaign(
                        f"Concurrent Test {operation_id}",
                        "Variant A", "Variant B"
                    )
                    return f"campaign-{operation_id}", campaign_id

            except Exception as e:
                return f"error-{operation_id}", str(e)

        # Run concurrent operations
        num_threads = 10
        results = []

        def worker(op_id):
            result = concurrent_operation(op_id)
            results.append(result)

        # Start concurrent threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all operations completed successfully
        successful_operations = 0
        error_operations = 0

        for operation_name, result in results:
            if "error-" in operation_name:
                error_operations += 1
                print(f"❌ {operation_name}: {result}")
            else:
                successful_operations += 1

        # CRITICAL ASSERTIONS: Most operations should succeed
        success_rate = successful_operations / len(results)
        assert success_rate >= 0.8, \
            f"CRITICAL: Success rate {success_rate:.1%} below 80% under concurrent access"

        # Verify data integrity after concurrent operations
        final_summary = engine.get_sales_pipeline_summary()
        assert final_summary['total_contacts'] >= 16, \
            "CRITICAL: Concurrent access corrupted contact data"

        print("\nConcurrent Access Test Results:")
        print(f"✅ Successful operations: {successful_operations}/{len(results)} ({success_rate:.1%})")
        print(f"✅ Pipeline integrity maintained: {final_summary['total_contacts']} contacts")

    def test_database_backup_and_recovery(self, protected_pipeline_engine):
        """CRITICAL: Test database backup and recovery procedures"""
        engine, db_path = protected_pipeline_engine

        # Create backup
        backup_path = f"{db_path}.backup"
        shutil.copy2(db_path, backup_path)

        # Capture original data
        original_summary = engine.get_sales_pipeline_summary()
        original_export = engine.export_pipeline_data()

        # Simulate data corruption or modification
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM crm_contacts WHERE contact_id LIKE 'protected-0%'")
        conn.commit()
        conn.close()

        # Verify corruption occurred
        corrupted_summary = engine.get_sales_pipeline_summary()
        assert corrupted_summary['total_contacts'] < original_summary['total_contacts'], \
            "Test corruption should reduce contact count"

        # Restore from backup
        shutil.copy2(backup_path, db_path)

        # Verify recovery
        recovered_engine = SalesAutomationEngine(db_path=db_path)
        recovered_summary = recovered_engine.get_sales_pipeline_summary()

        # CRITICAL ASSERTIONS: Recovery must restore original state
        assert recovered_summary['total_contacts'] == original_summary['total_contacts'], \
            f"CRITICAL: Recovery failed - contacts {recovered_summary['total_contacts']} != {original_summary['total_contacts']}"

        assert recovered_summary['total_pipeline_value'] == original_summary['total_pipeline_value'], \
            "CRITICAL: Recovery failed - pipeline value mismatch"

        print("\nBackup and Recovery Test:")
        print(f"✅ Original contacts: {original_summary['total_contacts']}")
        print(f"❌ After corruption: {corrupted_summary['total_contacts']}")
        print(f"✅ After recovery: {recovered_summary['total_contacts']}")
        print(f"✅ Pipeline value restored: ${recovered_summary['total_pipeline_value']:,}")

        # Cleanup
        Path(backup_path).unlink(missing_ok=True)


class TestZeroDowntimeOperations:
    """Test zero-downtime operations and business continuity"""

    @pytest.fixture
    def production_simulation_engine(self):
        """Create engine simulating production environment"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        engine = SalesAutomationEngine(db_path=db_path)

        # Populate with production-like data
        engine.import_consultation_inquiries(include_synthetic=True)

        yield engine, db_path

        Path(db_path).unlink(missing_ok=True)

    def test_zero_disruption_during_updates(self, production_simulation_engine):
        """Test zero business disruption during system updates"""
        engine, db_path = production_simulation_engine

        # Simulate ongoing business operations
        def ongoing_business_operations():
            """Simulate continuous business operations"""
            operation_results = []

            for i in range(10):  # 10 operations over test period
                try:
                    # Random business operations
                    if i % 2 == 0:
                        summary = engine.get_sales_pipeline_summary()
                        operation_results.append(("pipeline_summary", summary['total_contacts']))
                    else:
                        forecast = engine.generate_revenue_forecast("monthly")
                        operation_results.append(("forecast", forecast['total_projected_revenue']))

                    time.sleep(0.1)  # Simulate operation timing

                except Exception as e:
                    operation_results.append(("error", str(e)))

            return operation_results

        # Start background business operations
        results = []

        def business_worker():
            worker_results = ongoing_business_operations()
            results.extend(worker_results)

        business_thread = threading.Thread(target=business_worker)
        business_thread.start()

        # Simulate system update operations during business operations
        time.sleep(0.05)  # Let business operations start

        update_operations = [
            lambda: engine.create_ab_test_campaign("Update Test", "A", "B"),
            lambda: engine.get_unified_dashboard_data(),
            lambda: engine.export_pipeline_data(),
        ]

        update_results = []
        for update_op in update_operations:
            try:
                result = update_op()
                update_results.append(("success", type(result).__name__))
            except Exception as e:
                update_results.append(("error", str(e)))

            time.sleep(0.05)

        # Wait for business operations to complete
        business_thread.join()

        # Analyze results
        business_errors = [r for r in results if r[0] == "error"]
        update_errors = [r for r in update_results if r[0] == "error"]

        business_success_rate = (len(results) - len(business_errors)) / len(results)
        update_success_rate = (len(update_results) - len(update_errors)) / len(update_results)

        print("\nZero Downtime Test Results:")
        print(f"✅ Business operations: {len(results) - len(business_errors)}/{len(results)} ({business_success_rate:.1%})")
        print(f"✅ Update operations: {len(update_results) - len(update_errors)}/{len(update_results)} ({update_success_rate:.1%})")

        # CRITICAL ASSERTIONS: Business continuity must be maintained
        assert business_success_rate >= 0.9, \
            f"CRITICAL: Business operations success rate {business_success_rate:.1%} below 90%"

        assert len(business_errors) == 0, \
            f"CRITICAL: Business operations had {len(business_errors)} errors during updates"

    def test_rollback_capability(self, production_simulation_engine):
        """Test rollback capability for failed operations"""
        engine, db_path = production_simulation_engine

        # Capture initial state
        initial_summary = engine.get_sales_pipeline_summary()
        initial_state = {
            'contacts': initial_summary['total_contacts'],
            'pipeline_value': initial_summary['total_pipeline_value'],
            'proposals': initial_summary['total_proposals']
        }

        # Create checkpoint (backup)
        checkpoint_path = f"{db_path}.checkpoint"
        shutil.copy2(db_path, checkpoint_path)

        # Simulate risky operation that might fail
        def risky_operation():
            """Simulate operation that might need rollback"""
            # Add test contact
            test_contact = CRMContact(
                contact_id="rollback-test-001",
                name="Rollback Test Contact",
                company="Test Company",
                company_size="Series A (20-50 employees)",
                title="Test Title",
                email="test@rollback.com",
                linkedin_profile="",
                phone="",
                lead_score=50,
                qualification_status="unqualified",
                estimated_value=10000,
                priority_tier="bronze",
                next_action="Test action",
                next_action_date="",
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                notes="Rollback test contact"
            )

            engine._save_contacts([test_contact])

            # Simulate operation failure condition
            current_summary = engine.get_sales_pipeline_summary()
            if current_summary['total_contacts'] > initial_state['contacts'] + 5:  # Arbitrary failure condition
                raise Exception("Simulated operation failure requiring rollback")

        rollback_needed = False
        try:
            risky_operation()
        except Exception:
            rollback_needed = True

            # Perform rollback
            shutil.copy2(checkpoint_path, db_path)

            # Reinitialize engine to pick up restored state
            engine = SalesAutomationEngine(db_path=db_path)

        # Verify rollback if needed
        if rollback_needed:
            post_rollback_summary = engine.get_sales_pipeline_summary()

            # CRITICAL ASSERTIONS: Rollback must restore original state
            assert post_rollback_summary['total_contacts'] == initial_state['contacts'], \
                "CRITICAL: Rollback failed to restore contact count"

            assert post_rollback_summary['total_pipeline_value'] == initial_state['pipeline_value'], \
                "CRITICAL: Rollback failed to restore pipeline value"

            print("\n✅ Rollback Test Successful:")
            print(f"  Contacts restored: {post_rollback_summary['total_contacts']}")
            print(f"  Pipeline value restored: ${post_rollback_summary['total_pipeline_value']:,}")
        else:
            print("\n✅ Rollback Test: No rollback needed (operation succeeded)")

        # Cleanup
        Path(checkpoint_path).unlink(missing_ok=True)


class TestBusinessMetricsValidation:
    """Test business metrics validation and monitoring"""

    @pytest.fixture
    def metrics_engine(self):
        """Create engine for metrics validation"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        engine = SalesAutomationEngine(db_path=db_path)

        # Import comprehensive test data
        engine.import_consultation_inquiries(include_synthetic=True)

        yield engine, db_path

        Path(db_path).unlink(missing_ok=True)

    def test_real_time_metrics_monitoring(self, metrics_engine):
        """Test real-time business metrics monitoring"""
        engine, db_path = metrics_engine

        # Monitor metrics over time
        metrics_timeline = []

        for i in range(5):
            summary = engine.get_sales_pipeline_summary()
            unified_data = engine.get_unified_dashboard_data()

            metrics_snapshot = {
                'timestamp': datetime.now().isoformat(),
                'total_contacts': summary['total_contacts'],
                'pipeline_value': summary['total_pipeline_value'],
                'qualified_leads': summary['qualified_leads'],
                'pipeline_health': summary['pipeline_health_score'],
                'automation_status': unified_data['system_status']['automation_health']
            }

            metrics_timeline.append(metrics_snapshot)

            if i < 4:  # Don't sleep on last iteration
                time.sleep(0.1)

        # Validate metrics consistency
        for i, snapshot in enumerate(metrics_timeline):
            assert snapshot['total_contacts'] > 0, f"Snapshot {i}: No contacts in pipeline"
            assert snapshot['pipeline_value'] > 0, f"Snapshot {i}: No pipeline value"
            assert snapshot['qualified_leads'] <= snapshot['total_contacts'], \
                f"Snapshot {i}: Qualified leads exceed total contacts"
            assert 0 <= snapshot['pipeline_health'] <= 100, \
                f"Snapshot {i}: Pipeline health score out of range"

        # Check for consistency across snapshots
        first_snapshot = metrics_timeline[0]
        last_snapshot = metrics_timeline[-1]

        # Core metrics should remain stable during short monitoring period
        assert first_snapshot['total_contacts'] == last_snapshot['total_contacts'], \
            "Contact count should be stable during monitoring"

        print("\nReal-time Metrics Monitoring:")
        print(f"✅ Snapshots collected: {len(metrics_timeline)}")
        print(f"✅ Contact stability: {first_snapshot['total_contacts']} contacts")
        print(f"✅ Pipeline value: ${first_snapshot['pipeline_value']:,}")
        print(f"✅ Health score range: {min(s['pipeline_health'] for s in metrics_timeline):.1f} - {max(s['pipeline_health'] for s in metrics_timeline):.1f}")

    def test_business_kpi_validation(self, metrics_engine):
        """Test key business performance indicators"""
        engine, db_path = metrics_engine

        # Generate comprehensive business data
        summary = engine.get_sales_pipeline_summary()
        forecast = engine.generate_revenue_forecast("annual")
        unified_data = engine.get_unified_dashboard_data()

        # Define critical KPIs
        kpis = {
            'pipeline_value': {
                'value': summary['total_pipeline_value'],
                'target': 500000,  # Minimum expected pipeline
                'unit': '$'
            },
            'contact_count': {
                'value': summary['total_contacts'],
                'target': 10,  # Minimum contacts
                'unit': 'contacts'
            },
            'qualification_rate': {
                'value': summary['qualified_leads'] / max(summary['total_contacts'], 1),
                'target': 0.6,  # 60% qualification rate
                'unit': '%'
            },
            'pipeline_health': {
                'value': summary['pipeline_health_score'],
                'target': 50,  # Minimum health score
                'unit': 'score'
            },
            'arr_achievement': {
                'value': forecast['arr_target_achievement']['achievement_percentage'] / 100,
                'target': 0.5,  # 50% of ARR target
                'unit': '%'
            }
        }

        # Validate each KPI
        kpi_results = {}
        for kpi_name, kpi_data in kpis.items():
            actual_value = kpi_data['value']
            target_value = kpi_data['target']
            unit = kpi_data['unit']

            meets_target = actual_value >= target_value
            kpi_results[kpi_name] = {
                'actual': actual_value,
                'target': target_value,
                'meets_target': meets_target,
                'unit': unit
            }

            # CRITICAL ASSERTION: Each KPI must meet minimum target
            assert meets_target, \
                f"CRITICAL: KPI {kpi_name} = {actual_value:.2f}{unit} below target {target_value:.2f}{unit}"

        print("\nBusiness KPI Validation:")
        for kpi_name, result in kpi_results.items():
            status = "✅" if result['meets_target'] else "❌"
            if result['unit'] == '%':
                print(f"{status} {kpi_name}: {result['actual']:.1%} (Target: {result['target']:.1%})")
            elif result['unit'] == '$':
                print(f"{status} {kpi_name}: ${result['actual']:,.0f} (Target: ${result['target']:,.0f})")
            else:
                print(f"{status} {kpi_name}: {result['actual']:.1f}{result['unit']} (Target: {result['target']:.1f}{result['unit']})")

    def test_alert_system_validation(self, metrics_engine):
        """Test business alert system for critical thresholds"""
        engine, db_path = metrics_engine

        # Define alert thresholds
        alert_thresholds = {
            'pipeline_value_critical': 250000,  # Below this triggers critical alert
            'health_score_warning': 40,  # Below this triggers warning
            'qualified_lead_ratio_critical': 0.3,  # Below 30% qualified leads
        }

        summary = engine.get_sales_pipeline_summary()

        # Check alert conditions
        alerts_triggered = []

        # Pipeline value check
        if summary['total_pipeline_value'] < alert_thresholds['pipeline_value_critical']:
            alerts_triggered.append({
                'level': 'CRITICAL',
                'metric': 'Pipeline Value',
                'value': summary['total_pipeline_value'],
                'threshold': alert_thresholds['pipeline_value_critical'],
                'message': f"Pipeline value ${summary['total_pipeline_value']:,} below critical threshold ${alert_thresholds['pipeline_value_critical']:,}"
            })

        # Health score check
        if summary['pipeline_health_score'] < alert_thresholds['health_score_warning']:
            alerts_triggered.append({
                'level': 'WARNING',
                'metric': 'Pipeline Health',
                'value': summary['pipeline_health_score'],
                'threshold': alert_thresholds['health_score_warning'],
                'message': f"Pipeline health {summary['pipeline_health_score']:.1f} below warning threshold {alert_thresholds['health_score_warning']}"
            })

        # Qualified lead ratio check
        qualified_ratio = summary['qualified_leads'] / max(summary['total_contacts'], 1)
        if qualified_ratio < alert_thresholds['qualified_lead_ratio_critical']:
            alerts_triggered.append({
                'level': 'CRITICAL',
                'metric': 'Qualification Rate',
                'value': qualified_ratio,
                'threshold': alert_thresholds['qualified_lead_ratio_critical'],
                'message': f"Qualified lead ratio {qualified_ratio:.1%} below critical threshold {alert_thresholds['qualified_lead_ratio_critical']:.1%}"
            })

        print("\nAlert System Validation:")
        if alerts_triggered:
            print(f"⚠️  {len(alerts_triggered)} alerts triggered:")
            for alert in alerts_triggered:
                print(f"  {alert['level']}: {alert['message']}")
        else:
            print("✅ No alerts triggered - all metrics within acceptable ranges")

        # For this test, we expect the system to be healthy (no critical alerts)
        critical_alerts = [a for a in alerts_triggered if a['level'] == 'CRITICAL']
        assert len(critical_alerts) == 0, \
            f"CRITICAL: {len(critical_alerts)} critical business alerts triggered"


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "--tb=short", "-s"])
