#!/usr/bin/env python3
"""
Epic 15 Comprehensive Testing Framework Runner
Orchestrates all testing phases for system consolidation readiness
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class Epic15TestRunner:
    """Orchestrate Epic 15 testing phases with business continuity protection"""

    def __init__(self):
        self.test_results = {}
        self.start_time = datetime.now()
        self.project_root = project_root

        # Define test phases in priority order
        self.test_phases = {
            'phase1_business_critical': {
                'name': 'Phase 1: Business Logic Tests (REVENUE CRITICAL)',
                'description': 'Epic 7 CRM and business logic tests protecting $1.158M pipeline',
                'tests': [
                    'tests/business/test_epic7_crm.py',
                    'tests/business/test_lead_scoring.py',
                    'tests/business/test_proposal_gen.py',
                    'tests/business/test_consultation.py'
                ],
                'priority': 1,
                'critical': True
            },
            'phase2_core_system': {
                'name': 'Phase 2: Core GraphRAG System Tests',
                'description': 'Core platform functionality validation',
                'tests': [
                    'tests/core/test_graph_rag_system.py',
                    'tests/core/test_graph_rag_engine_orchestrator.py',
                    'tests/core/test_knowledge_graph_builder.py'
                ],
                'priority': 2,
                'critical': True
            },
            'phase3_integration': {
                'name': 'Phase 3: API Integration & Contract Tests',
                'description': 'System integration and API contract validation',
                'tests': [
                    'tests/integration/test_api_contracts.py',
                    'tests/integration/test_e2e.py',
                    'tests/integration/test_ingestion_integration.py'
                ],
                'priority': 3,
                'critical': False
            },
            'phase4_performance': {
                'name': 'Phase 4: Performance & Quality Monitoring',
                'description': 'Performance benchmarks and quality metrics',
                'tests': [
                    'tests/performance/test_system_monitoring.py',
                    'tests/performance/test_system_performance.py'
                ],
                'priority': 4,
                'critical': False
            },
            'phase5_continuity': {
                'name': 'Phase 5: Business Continuity Validation',
                'description': 'Pipeline protection and business continuity assurance',
                'tests': [
                    'tests/business_continuity/test_pipeline_protection.py'
                ],
                'priority': 5,
                'critical': True
            }
        }

    def run_test_suite(self, test_file: str, verbose: bool = True) -> tuple[bool, dict]:
        """Run a specific test suite and return results"""
        print(f"🧪 Running test suite: {test_file}")

        # Check if test file exists
        test_path = self.project_root / test_file
        if not test_path.exists():
            print(f"⚠️  Test file not found: {test_path}")
            return False, {
                'status': 'error',
                'message': f'Test file not found: {test_file}',
                'duration': 0,
                'tests_run': 0,
                'failures': 0,
                'errors': 0
            }

        # Run pytest with appropriate flags
        cmd = [
            'python', '-m', 'pytest',
            str(test_path),
            '-v' if verbose else '-q',
            '--tb=short',
            '--json-report',
            '--json-report-file=/tmp/pytest_report.json'
        ]

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per test suite
            )

            duration = time.time() - start_time

            # Parse results
            try:
                with open('/tmp/pytest_report.json') as f:
                    report_data = json.load(f)

                summary = report_data.get('summary', {})

                test_results = {
                    'status': 'success' if result.returncode == 0 else 'failed',
                    'duration': duration,
                    'tests_run': summary.get('total', 0),
                    'passed': summary.get('passed', 0),
                    'failed': summary.get('failed', 0),
                    'errors': summary.get('error', 0),
                    'skipped': summary.get('skipped', 0),
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }

            except (FileNotFoundError, json.JSONDecodeError):
                # Fallback to basic parsing
                test_results = {
                    'status': 'success' if result.returncode == 0 else 'failed',
                    'duration': duration,
                    'tests_run': 'unknown',
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }

            # Print summary
            if test_results['status'] == 'success':
                print(f"✅ {test_file}: {test_results.get('passed', '?')} tests passed in {duration:.1f}s")
            else:
                print(f"❌ {test_file}: {test_results.get('failed', '?')} failures, {test_results.get('errors', '?')} errors")
                if verbose and test_results.get('stderr'):
                    print(f"   Error output: {test_results['stderr'][:200]}...")

            return result.returncode == 0, test_results

        except subprocess.TimeoutExpired:
            print(f"⏰ Test suite {test_file} timed out after 5 minutes")
            return False, {
                'status': 'timeout',
                'duration': 300,
                'message': 'Test suite timed out'
            }

        except Exception as e:
            print(f"💥 Error running test suite {test_file}: {e}")
            return False, {
                'status': 'error',
                'duration': time.time() - start_time,
                'message': str(e)
            }

    def run_phase(self, phase_id: str, verbose: bool = True, stop_on_failure: bool = False) -> bool:
        """Run a complete testing phase"""
        phase = self.test_phases[phase_id]
        print(f"\n{'='*60}")
        print(f"🚀 {phase['name']}")
        print(f"📋 {phase['description']}")
        print(f"{'='*60}")

        phase_results = {
            'phase_id': phase_id,
            'name': phase['name'],
            'start_time': datetime.now().isoformat(),
            'tests': {},
            'summary': {
                'total_tests': len(phase['tests']),
                'passed_tests': 0,
                'failed_tests': 0,
                'total_duration': 0
            }
        }

        phase_success = True

        for test_file in phase['tests']:
            success, results = self.run_test_suite(test_file, verbose)

            phase_results['tests'][test_file] = results
            phase_results['summary']['total_duration'] += results.get('duration', 0)

            if success:
                phase_results['summary']['passed_tests'] += 1
            else:
                phase_results['summary']['failed_tests'] += 1
                phase_success = False

                if stop_on_failure:
                    print(f"⛔ Stopping phase {phase_id} due to test failure: {test_file}")
                    break

        phase_results['end_time'] = datetime.now().isoformat()
        phase_results['success'] = phase_success

        # Store results
        self.test_results[phase_id] = phase_results

        # Print phase summary
        summary = phase_results['summary']
        print(f"\n📊 Phase {phase_id} Summary:")
        print(f"   ✅ Passed: {summary['passed_tests']}/{summary['total_tests']}")
        print(f"   ❌ Failed: {summary['failed_tests']}/{summary['total_tests']}")
        print(f"   ⏱️  Duration: {summary['total_duration']:.1f}s")
        print(f"   🎯 Success: {'YES' if phase_success else 'NO'}")

        # Critical phase failure check
        if not phase_success and phase.get('critical', False):
            print(f"🚨 CRITICAL PHASE FAILURE: {phase['name']}")
            print("   This phase is marked as critical for business continuity!")

        return phase_success

    def generate_comprehensive_report(self) -> dict:
        """Generate comprehensive testing report"""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()

        # Calculate overall statistics
        total_phases = len(self.test_results)
        passed_phases = sum(1 for r in self.test_results.values() if r.get('success', False))

        total_test_suites = sum(r['summary']['total_tests'] for r in self.test_results.values())
        passed_test_suites = sum(r['summary']['passed_tests'] for r in self.test_results.values())
        failed_test_suites = sum(r['summary']['failed_tests'] for r in self.test_results.values())

        # Calculate critical phase status
        critical_phases = [pid for pid, phase in self.test_phases.items() if phase.get('critical', False)]
        critical_phase_success = all(
            self.test_results.get(pid, {}).get('success', False) for pid in critical_phases
        )

        report = {
            'epic15_testing_report': {
                'timestamp': end_time.isoformat(),
                'total_duration_seconds': total_duration,
                'overall_success': passed_phases == total_phases and critical_phase_success,
                'critical_systems_protected': critical_phase_success
            },
            'summary': {
                'phases': {
                    'total': total_phases,
                    'passed': passed_phases,
                    'failed': total_phases - passed_phases
                },
                'test_suites': {
                    'total': total_test_suites,
                    'passed': passed_test_suites,
                    'failed': failed_test_suites
                },
                'critical_phase_status': 'PROTECTED' if critical_phase_success else 'AT_RISK'
            },
            'phase_results': self.test_results,
            'business_impact_assessment': self._assess_business_impact(),
            'recommendations': self._generate_recommendations()
        }

        return report

    def _assess_business_impact(self) -> dict:
        """Assess business impact based on test results"""
        # Check critical business systems
        business_systems_status = {
            'epic7_crm_system': 'unknown',
            'pipeline_protection': 'unknown',
            'revenue_forecasting': 'unknown',
            'api_stability': 'unknown'
        }

        # Analyze Phase 1 (Business Critical) results
        if 'phase1_business_critical' in self.test_results:
            phase1 = self.test_results['phase1_business_critical']
            if phase1.get('success', False):
                business_systems_status['epic7_crm_system'] = 'operational'
                business_systems_status['pipeline_protection'] = 'protected'
                business_systems_status['revenue_forecasting'] = 'functional'
            else:
                business_systems_status['epic7_crm_system'] = 'at_risk'
                business_systems_status['pipeline_protection'] = 'compromised'

        # Analyze Phase 3 (Integration) results
        if 'phase3_integration' in self.test_results:
            phase3 = self.test_results['phase3_integration']
            business_systems_status['api_stability'] = 'stable' if phase3.get('success', False) else 'unstable'

        # Calculate business continuity score
        operational_systems = sum(1 for status in business_systems_status.values() if status in ['operational', 'protected', 'functional', 'stable'])
        continuity_score = (operational_systems / len(business_systems_status)) * 100

        return {
            'business_systems_status': business_systems_status,
            'business_continuity_score': continuity_score,
            'pipeline_value_protected': continuity_score >= 75,
            'ready_for_consolidation': continuity_score >= 90
        }

    def _generate_recommendations(self) -> list[str]:
        """Generate recommendations based on test results"""
        recommendations = []

        # Check critical phases
        critical_failures = []
        for phase_id, phase_info in self.test_phases.items():
            if phase_info.get('critical', False):
                if not self.test_results.get(phase_id, {}).get('success', False):
                    critical_failures.append(phase_info['name'])

        if critical_failures:
            recommendations.append(
                f"🚨 CRITICAL: Address failures in critical phases: {', '.join(critical_failures)}"
            )
            recommendations.append(
                "🛡️ BUSINESS PROTECTION: Do not proceed with system consolidation until critical issues are resolved"
            )
        else:
            recommendations.append(
                "✅ BUSINESS CONTINUITY: All critical systems tested and operational"
            )

        # Performance recommendations
        if 'phase4_performance' in self.test_results:
            if self.test_results['phase4_performance'].get('success', False):
                recommendations.append("⚡ PERFORMANCE: System meets performance benchmarks for enterprise scaling")
            else:
                recommendations.append("🔧 OPTIMIZATION: Address performance issues before scaling to Fortune 500 requirements")

        # Integration recommendations
        if 'phase3_integration' in self.test_results:
            if self.test_results['phase3_integration'].get('success', False):
                recommendations.append("🔗 INTEGRATION: API contracts validated - safe for consolidation")
            else:
                recommendations.append("🔧 API FIXES: Resolve API contract issues before router consolidation")

        # Overall readiness
        business_impact = self._assess_business_impact()
        if business_impact['ready_for_consolidation']:
            recommendations.append("🎯 CONSOLIDATION READY: System validated for Epic 15 consolidation (33 → 8-10 routers)")
        else:
            recommendations.append("⚠️ CONSOLIDATION BLOCKED: Address test failures before proceeding with architectural changes")

        return recommendations

    def print_final_report(self, report: dict):
        """Print comprehensive final report"""
        print(f"\n{'='*80}")
        print("🏆 EPIC 15 TESTING FRAMEWORK - COMPREHENSIVE REPORT")
        print(f"{'='*80}")

        # Overall status
        overall_success = report['epic15_testing_report']['overall_success']
        critical_protected = report['epic15_testing_report']['critical_systems_protected']

        print(f"🎯 Overall Status: {'✅ SUCCESS' if overall_success else '❌ NEEDS ATTENTION'}")
        print(f"🛡️ Critical Systems: {'✅ PROTECTED' if critical_protected else '🚨 AT RISK'}")
        print(f"⏱️ Total Duration: {report['epic15_testing_report']['total_duration_seconds']:.1f}s")

        # Summary statistics
        summary = report['summary']
        print("\n📊 Test Execution Summary:")
        print(f"   Phases: {summary['phases']['passed']}/{summary['phases']['total']} passed")
        print(f"   Test Suites: {summary['test_suites']['passed']}/{summary['test_suites']['total']} passed")
        print(f"   Critical Status: {summary['critical_phase_status']}")

        # Business impact
        business_impact = report['business_impact_assessment']
        print("\n💼 Business Impact Assessment:")
        print(f"   Business Continuity Score: {business_impact['business_continuity_score']:.1f}%")
        print(f"   Pipeline Value Protected: {'✅ YES' if business_impact['pipeline_value_protected'] else '❌ NO'}")
        print(f"   Ready for Consolidation: {'✅ YES' if business_impact['ready_for_consolidation'] else '❌ NO'}")

        # System status
        print("\n🔧 System Status:")
        for system, status in business_impact['business_systems_status'].items():
            status_icon = {
                'operational': '✅', 'protected': '🛡️', 'functional': '⚡', 'stable': '🔗',
                'at_risk': '⚠️', 'compromised': '🚨', 'unstable': '💥', 'unknown': '❓'
            }.get(status, '❓')
            print(f"   {system.replace('_', ' ').title()}: {status_icon} {status.upper()}")

        # Recommendations
        print("\n📋 Recommendations:")
        for i, recommendation in enumerate(report['recommendations'], 1):
            print(f"   {i}. {recommendation}")

        # Final verdict
        print(f"\n{'='*80}")
        if overall_success and critical_protected:
            print("🎉 EPIC 15 TESTING FRAMEWORK: ✅ ALL SYSTEMS GO")
            print("   System consolidation can proceed safely with business continuity assured")
        elif critical_protected:
            print("⚠️ EPIC 15 TESTING FRAMEWORK: 🟡 CONDITIONAL PROCEED")
            print("   Critical systems protected, but address non-critical issues before consolidation")
        else:
            print("🚨 EPIC 15 TESTING FRAMEWORK: ❌ DO NOT PROCEED")
            print("   Critical business systems at risk - resolve issues before any architectural changes")
        print(f"{'='*80}")


def main():
    """Main entry point for Epic 15 testing framework"""
    parser = argparse.ArgumentParser(description='Epic 15 Comprehensive Testing Framework')
    parser.add_argument('--phase', choices=['1', '2', '3', '4', '5', 'all'], default='all',
                       help='Run specific phase or all phases')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--stop-on-failure', action='store_true',
                       help='Stop testing on first failure')
    parser.add_argument('--report-only', action='store_true',
                       help='Generate report from existing results (skip testing)')

    args = parser.parse_args()

    runner = Epic15TestRunner()

    print("🚀 Epic 15 System Consolidation Testing Framework")
    print(f"📅 Started: {runner.start_time.isoformat()}")
    print("🎯 Mission: Enable safe consolidation of 33 → 8-10 API routers")
    print("🛡️ Priority: Protect $1.158M business pipeline")

    if not args.report_only:
        # Determine which phases to run
        if args.phase == 'all':
            phases_to_run = list(runner.test_phases.keys())
        else:
            phase_id = f'phase{args.phase}_' + {
                '1': 'business_critical',
                '2': 'core_system',
                '3': 'integration',
                '4': 'performance',
                '5': 'continuity'
            }[args.phase]
            phases_to_run = [phase_id]

        # Run selected phases
        for phase_id in phases_to_run:
            if phase_id in runner.test_phases:
                success = runner.run_phase(
                    phase_id,
                    verbose=args.verbose,
                    stop_on_failure=args.stop_on_failure
                )
                if not success:
                    if args.stop_on_failure and runner.test_phases[phase_id].get('critical', False):
                        print(f"🛑 Stopping execution due to critical phase failure: {phase_id}")
                        break

    # Generate and display comprehensive report
    report = runner.generate_comprehensive_report()
    runner.print_final_report(report)

    # Save report to file
    report_file = runner.project_root / f"epic15_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n💾 Full report saved to: {report_file}")

    # Exit with appropriate code
    overall_success = report['epic15_testing_report']['overall_success']
    critical_protected = report['epic15_testing_report']['critical_systems_protected']

    if overall_success:
        sys.exit(0)  # Complete success
    elif critical_protected:
        sys.exit(1)  # Partial success - critical systems protected
    else:
        sys.exit(2)  # Critical failure - business systems at risk


if __name__ == "__main__":
    main()
