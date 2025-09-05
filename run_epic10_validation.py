#!/usr/bin/env python3
"""
Epic 10 System Consolidation Validation Runner

This script runs comprehensive validation testing for Epic 10 system
consolidation completion and enterprise readiness.

Usage:
    python run_epic10_validation.py [--full] [--report-only] [--save-report]
    
Options:
    --full          Run full validation suite including long-running tests
    --report-only   Generate report without running new tests
    --save-report   Save detailed report to JSON file
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.epic10_validation import (
    Epic10ValidationFramework,
    DatabaseConsolidationValidator,
    Epic7PipelineValidator,
    EnterpriseReadinessValidator,
    ComprehensiveRegressionValidator
)


class Epic10ValidationRunner:
    """Main runner for Epic 10 validation tests."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.validators = {
            "main": Epic10ValidationFramework(),
            "database": DatabaseConsolidationValidator(),
            "epic7": Epic7PipelineValidator(),
            "enterprise": EnterpriseReadinessValidator(),
            "regression": ComprehensiveRegressionValidator()
        }
        
    def run_quick_validation(self) -> Dict[str, Any]:
        """Run quick validation tests (essential checks only)."""
        print("🚀 Starting Epic 10 Quick Validation...")
        print("="*70)
        
        results = {}
        
        # 1. Database consolidation check
        print("1️⃣ Database Consolidation Status...")
        results["database_consolidation"] = self.validators["database"].generate_consolidation_report()
        self._print_status("Database Consolidation", results["database_consolidation"]["status"])
        
        # 2. Epic 7 pipeline protection check
        print("\n2️⃣ Epic 7 Pipeline Protection...")
        results["epic7_protection"] = self.validators["epic7"].generate_pipeline_protection_report()
        self._print_status("Epic 7 Protection", results["epic7_protection"]["pipeline_protection_status"])
        
        # 3. Basic API functionality check
        print("\n3️⃣ API Functionality Check...")
        api_validation = self.validators["main"].validate_api_functionality()
        results["api_functionality"] = api_validation
        self._print_status("API Functionality", api_validation["status"])
        
        # 4. Enterprise readiness quick check
        print("\n4️⃣ Enterprise Readiness Overview...")
        enterprise_auth = self.validators["enterprise"].validate_authentication_enterprise_readiness()
        results["enterprise_auth"] = enterprise_auth
        self._print_status("Enterprise Auth", enterprise_auth["status"])
        
        return results
    
    def run_full_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation tests."""
        print("🔍 Starting Epic 10 Comprehensive Validation...")
        print("="*70)
        
        results = {}
        
        # 1. Main Epic 10 validation framework
        print("1️⃣ Main Epic 10 Validation Framework...")
        results["main_validation"] = self.validators["main"].generate_validation_report()
        self._print_detailed_status("Main Validation", results["main_validation"])
        
        # 2. Database consolidation validation
        print("\n2️⃣ Database Consolidation Validation...")
        results["database_validation"] = self.validators["database"].generate_consolidation_report()
        self._print_detailed_status("Database Consolidation", results["database_validation"])
        
        # 3. Epic 7 pipeline protection validation
        print("\n3️⃣ Epic 7 Pipeline Protection Validation...")
        results["epic7_validation"] = self.validators["epic7"].generate_pipeline_protection_report()
        self._print_detailed_status("Epic 7 Protection", results["epic7_validation"])
        
        # 4. Enterprise readiness validation
        print("\n4️⃣ Enterprise Readiness Validation...")
        results["enterprise_validation"] = self.validators["enterprise"].generate_enterprise_readiness_report()
        self._print_detailed_status("Enterprise Readiness", results["enterprise_validation"])
        
        # 5. Comprehensive regression testing
        print("\n5️⃣ Comprehensive Regression Testing...")
        results["regression_validation"] = self.validators["regression"].generate_comprehensive_regression_report()
        self._print_detailed_status("Regression Testing", results["regression_validation"])
        
        return results
    
    def generate_consolidation_report(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final Epic 10 consolidation report."""
        
        # Extract key metrics from validation results
        database_status = validation_results.get("database_validation", {}).get("status", "UNKNOWN")
        epic7_status = validation_results.get("epic7_validation", {}).get("pipeline_protection_status", "UNKNOWN")
        enterprise_status = validation_results.get("enterprise_validation", {}).get("enterprise_readiness_status", "UNKNOWN")
        regression_status = validation_results.get("regression_validation", {}).get("overall_regression_status", "UNKNOWN")
        
        # Calculate overall completion metrics
        completion_factors = {
            "database_consolidation": database_status == "COMPLETE",
            "epic7_protection": epic7_status in ["FULLY_PROTECTED", "PARTIALLY_PROTECTED"],
            "enterprise_readiness": enterprise_status in ["ENTERPRISE_READY", "MOSTLY_READY"],
            "regression_tests": regression_status in ["NO_REGRESSIONS", "MINOR_REGRESSIONS"]
        }
        
        completed_factors = sum(completion_factors.values())
        total_factors = len(completion_factors)
        completion_percentage = (completed_factors / total_factors) * 100
        
        # Determine overall Epic 10 status
        if completion_percentage >= 90:
            overall_status = "EPIC_10_COMPLETE"
            readiness_level = "PRODUCTION_READY"
        elif completion_percentage >= 75:
            overall_status = "EPIC_10_MOSTLY_COMPLETE"
            readiness_level = "PRE_PRODUCTION"
        elif completion_percentage >= 60:
            overall_status = "EPIC_10_IN_PROGRESS"
            readiness_level = "DEVELOPMENT"
        else:
            overall_status = "EPIC_10_INCOMPLETE"
            readiness_level = "REQUIRES_ATTENTION"
        
        # Extract key metrics
        database_count = validation_results.get("database_validation", {}).get("total_databases", 0)
        pipeline_value = validation_results.get("epic7_validation", {}).get("value_at_risk_analysis", {}).get("current_pipeline_value", 0)
        
        consolidation_report = {
            "epic_10_completion_status": overall_status,
            "readiness_level": readiness_level,
            "completion_percentage": completion_percentage,
            "completion_factors": completion_factors,
            "key_metrics": {
                "database_count": database_count,
                "database_consolidation_target": 3,
                "pipeline_value_current": pipeline_value,
                "pipeline_value_target": 1158000,
                "enterprise_readiness_score": validation_results.get("enterprise_validation", {}).get("overall_score", 0)
            },
            "category_status": {
                "database_consolidation": database_status,
                "epic7_pipeline_protection": epic7_status,
                "enterprise_readiness": enterprise_status,
                "regression_testing": regression_status
            },
            "validation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "detailed_results": validation_results,
            "next_steps": self._generate_next_steps(overall_status, completion_factors, validation_results)
        }
        
        return consolidation_report
    
    def _print_status(self, category: str, status: str):
        """Print category status with appropriate color coding."""
        status_colors = {
            "PASS": "✅",
            "COMPLETE": "✅",
            "HEALTHY": "✅",
            "FUNCTIONAL": "✅",
            "READY": "✅",
            "FULLY_PROTECTED": "✅",
            "ENTERPRISE_READY": "✅",
            "NO_REGRESSIONS": "✅",
            
            "PARTIAL": "⚠️",
            "IN_PROGRESS": "⚠️",
            "MOSTLY_READY": "⚠️",
            "PARTIALLY_PROTECTED": "⚠️",
            "MINOR_REGRESSIONS": "⚠️",
            
            "FAIL": "❌",
            "INCOMPLETE": "❌",
            "AT_RISK": "❌",
            "CRITICAL_RISK": "❌",
            "NOT_READY": "❌",
            "CRITICAL_REGRESSIONS": "❌"
        }
        
        icon = status_colors.get(status, "❓")
        print(f"   {icon} {category}: {status}")
    
    def _print_detailed_status(self, category: str, results: Dict[str, Any]):
        """Print detailed status information."""
        # Extract status from various possible keys
        status_keys = [
            "epic10_consolidation_complete", "consolidation_complete", 
            "pipeline_protection_status", "enterprise_readiness_status",
            "overall_regression_status", "status"
        ]
        
        status = "UNKNOWN"
        for key in status_keys:
            if key in results:
                status = results[key]
                break
        
        self._print_status(category, str(status))
        
        # Print additional metrics if available
        if "completion_percentage" in results:
            print(f"      Completion: {results['completion_percentage']:.1f}%")
        if "success_rate" in results:
            print(f"      Success Rate: {results['success_rate']:.1f}%")
        if "overall_score" in results:
            print(f"      Score: {results['overall_score']:.1f}%")
    
    def _generate_next_steps(self, overall_status: str, completion_factors: Dict[str, bool], results: Dict[str, Any]) -> list[str]:
        """Generate next steps recommendations."""
        next_steps = []
        
        if overall_status == "EPIC_10_COMPLETE":
            next_steps.extend([
                "🎉 Epic 10 consolidation complete! Ready for Epic 8 implementation.",
                "📋 Document consolidation achievements and lessons learned.",
                "🚀 Begin Epic 8 planning and requirements gathering.",
                "🔄 Establish ongoing monitoring for consolidated systems."
            ])
        elif overall_status == "EPIC_10_MOSTLY_COMPLETE":
            next_steps.extend([
                "🔧 Address remaining consolidation items to achieve full completion.",
                "📊 Focus on areas with completion gaps identified in validation.",
                "🧪 Run targeted tests for incomplete areas.",
                "📈 Prepare for Epic 8 while completing Epic 10 tasks."
            ])
        else:
            # Identify specific areas needing attention
            if not completion_factors.get("database_consolidation", True):
                next_steps.append("🗄️ Complete database consolidation: migrate remaining databases to 3 target databases.")
            
            if not completion_factors.get("epic7_protection", True):
                next_steps.append("💼 Strengthen Epic 7 pipeline protection: ensure $1,158,000 value integrity.")
            
            if not completion_factors.get("enterprise_readiness", True):
                next_steps.append("🏢 Improve enterprise readiness: address authentication, scalability, and compliance gaps.")
            
            if not completion_factors.get("regression_tests", True):
                next_steps.append("🧪 Fix regression test failures: resolve breaking changes and performance issues.")
        
        return next_steps
    
    def save_report_to_file(self, report: Dict[str, Any], filename: str = None) -> str:
        """Save validation report to JSON file."""
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"epic10_validation_report_{timestamp}.json"
        
        report_path = self.project_root / filename
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return str(report_path)
    
    def print_final_summary(self, report: Dict[str, Any]):
        """Print final validation summary."""
        print("\n" + "="*70)
        print("🏁 EPIC 10 SYSTEM CONSOLIDATION VALIDATION SUMMARY")
        print("="*70)
        
        print(f"Overall Status: {report['epic_10_completion_status']}")
        print(f"Readiness Level: {report['readiness_level']}")
        print(f"Completion: {report['completion_percentage']:.1f}%")
        
        print("\nCategory Status:")
        for category, status in report['category_status'].items():
            self._print_status(category.replace('_', ' ').title(), status)
        
        print(f"\nKey Metrics:")
        metrics = report['key_metrics']
        print(f"  📊 Databases: {metrics['database_count']} (target: {metrics['database_consolidation_target']})")
        print(f"  💰 Pipeline Value: ${metrics['pipeline_value_current']:,.2f} (target: ${metrics['pipeline_value_target']:,.2f})")
        print(f"  🏢 Enterprise Score: {metrics['enterprise_readiness_score']:.1f}%")
        
        if report['next_steps']:
            print(f"\nNext Steps:")
            for step in report['next_steps']:
                print(f"  {step}")
        
        print("="*70)


def main():
    """Main entry point for Epic 10 validation."""
    parser = argparse.ArgumentParser(description='Epic 10 System Consolidation Validation')
    parser.add_argument('--full', action='store_true', help='Run full validation suite')
    parser.add_argument('--report-only', action='store_true', help='Generate report without running tests')
    parser.add_argument('--save-report', action='store_true', help='Save detailed report to JSON file')
    parser.add_argument('--output', type=str, help='Output filename for saved report')
    
    args = parser.parse_args()
    
    runner = Epic10ValidationRunner()
    
    try:
        if args.report_only:
            print("📋 Generating report from existing data...")
            # This would load existing results if available
            validation_results = {}
        elif args.full:
            validation_results = runner.run_full_validation()
        else:
            validation_results = runner.run_quick_validation()
        
        # Generate consolidation report
        consolidation_report = runner.generate_consolidation_report(validation_results)
        
        # Print final summary
        runner.print_final_summary(consolidation_report)
        
        # Save report if requested
        if args.save_report:
            report_path = runner.save_report_to_file(consolidation_report, args.output)
            print(f"\n📄 Detailed report saved to: {report_path}")
        
        # Exit with appropriate code
        if consolidation_report['epic_10_completion_status'] in ['EPIC_10_COMPLETE', 'EPIC_10_MOSTLY_COMPLETE']:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()