"""
Epic 10 System Consolidation Validation Test Suite

This comprehensive test suite validates the completion of Epic 10 system consolidation
and ensures enterprise readiness for Fortune 500 scalability.

Test Coverage:
1. Epic 7 Pipeline Protection Validation ($1,158,000 value integrity)
2. Database Consolidation Validation (Target: 3 databases)
3. API Router Consolidation Validation (Target: 10 routers)
4. Enterprise Readiness Validation
5. Regression Testing
"""

import pytest
import sqlite3
import os
import subprocess
import requests
import time
from pathlib import Path
from typing import Dict, List, Any
import json
import asyncio
import aiohttp


class Epic10ValidationFramework:
    """Comprehensive validation framework for Epic 10 system consolidation."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.api_base_url = "http://localhost:8000/api/v1"
        self.validation_results = {}
        
    def get_database_count(self) -> int:
        """Count actual databases in root directory."""
        db_files = list(self.project_root.glob("*.db"))
        return len(db_files)
    
    def get_database_list(self) -> List[str]:
        """Get list of all databases."""
        db_files = list(self.project_root.glob("*.db"))
        return [db.name for db in db_files]
    
    def get_router_count(self) -> int:
        """Count API routers."""
        router_files = list((self.project_root / "graph_rag" / "api" / "routers").glob("*.py"))
        # Exclude __init__.py
        router_files = [f for f in router_files if f.name != "__init__.py"]
        return len(router_files)
    
    def get_router_list(self) -> List[str]:
        """Get list of all API routers."""
        router_files = list((self.project_root / "graph_rag" / "api" / "routers").glob("*.py"))
        router_files = [f for f in router_files if f.name != "__init__.py"]
        return [f.stem for f in router_files]
    
    def validate_database_consolidation(self) -> Dict[str, Any]:
        """Validate database consolidation status."""
        target_databases = 3
        current_count = self.get_database_count()
        database_list = self.get_database_list()
        
        # Expected consolidated databases
        expected_dbs = [
            "synapse_business_crm.db",
            "synapse_analytics_intelligence.db", 
            "synapse_system_infrastructure.db"
        ]
        
        consolidation_complete = current_count <= target_databases
        expected_dbs_present = all(db in database_list for db in expected_dbs)
        
        return {
            "consolidation_complete": consolidation_complete,
            "target_count": target_databases,
            "current_count": current_count,
            "database_list": database_list,
            "expected_dbs_present": expected_dbs_present,
            "expected_databases": expected_dbs,
            "status": "PASS" if consolidation_complete and expected_dbs_present else "FAIL"
        }
    
    def validate_router_consolidation(self) -> Dict[str, Any]:
        """Validate API router consolidation status."""
        target_routers = 10
        current_count = self.get_router_count()
        router_list = self.get_router_list()
        
        # Expected consolidated routers
        expected_routers = [
            "core_business",
            "administration", 
            "analytics",
            "advanced_features",
            "epic7_sales_automation",
            "unified_platform",
            "enterprise_auth",
            "compliance",
            "monitoring",
            "unified_business_intelligence"
        ]
        
        consolidation_complete = current_count <= target_routers
        expected_routers_present = all(router in router_list for router in expected_routers)
        
        return {
            "consolidation_complete": consolidation_complete,
            "target_count": target_routers,
            "current_count": current_count,
            "router_list": router_list,
            "expected_routers_present": expected_routers_present,
            "expected_routers": expected_routers,
            "status": "PASS" if consolidation_complete and expected_routers_present else "FAIL"
        }
    
    def validate_epic7_pipeline_protection(self) -> Dict[str, Any]:
        """Validate Epic 7 pipeline protection and $1,158,000 value integrity."""
        try:
            # Check for Epic 7 sales automation router
            epic7_router_exists = (self.project_root / "graph_rag" / "api" / "routers" / "epic7_sales_automation.py").exists()
            
            # Check business CRM database
            crm_db_path = self.project_root / "synapse_business_crm.db"
            crm_db_exists = crm_db_path.exists()
            
            pipeline_data = {}
            contacts_count = 0
            total_value = 0.0
            
            if crm_db_exists:
                try:
                    conn = sqlite3.connect(crm_db_path)
                    cursor = conn.cursor()
                    
                    # Check for contacts table and count
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contacts'")
                    if cursor.fetchone():
                        cursor.execute("SELECT COUNT(*) FROM contacts")
                        contacts_count = cursor.fetchone()[0]
                    
                    # Check for opportunities/pipeline value
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='opportunities'")
                    if cursor.fetchone():
                        cursor.execute("SELECT SUM(value) FROM opportunities WHERE status IN ('active', 'qualified', 'proposal')")
                        result = cursor.fetchone()
                        total_value = result[0] if result[0] else 0.0
                    
                    conn.close()
                except Exception as e:
                    pipeline_data["db_error"] = str(e)
            
            pipeline_protected = (
                epic7_router_exists and
                crm_db_exists and
                contacts_count >= 16 and  # Epic 7 requirement
                total_value >= 1000000    # $1M+ pipeline value
            )
            
            return {
                "pipeline_protected": pipeline_protected,
                "epic7_router_exists": epic7_router_exists,
                "crm_db_exists": crm_db_exists,
                "contacts_count": contacts_count,
                "total_pipeline_value": total_value,
                "target_contacts": 16,
                "target_value": 1158000,
                "status": "PASS" if pipeline_protected else "FAIL"
            }
            
        except Exception as e:
            return {
                "pipeline_protected": False,
                "error": str(e),
                "status": "FAIL"
            }
    
    def validate_api_functionality(self) -> Dict[str, Any]:
        """Validate API functionality and endpoint availability."""
        try:
            # Test API health endpoint
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            api_healthy = response.status_code == 200
            
            # Test key endpoints
            endpoints_to_test = [
                "/documents",
                "/search", 
                "/query",
                "/admin/status",
                "/auth/login",
                "/analytics/metrics"
            ]
            
            endpoint_results = {}
            for endpoint in endpoints_to_test:
                try:
                    resp = requests.get(f"{self.api_base_url}{endpoint}", timeout=5)
                    endpoint_results[endpoint] = {
                        "status_code": resp.status_code,
                        "accessible": resp.status_code in [200, 401, 422]  # 401/422 acceptable for auth endpoints
                    }
                except Exception as e:
                    endpoint_results[endpoint] = {
                        "status_code": None,
                        "accessible": False,
                        "error": str(e)
                    }
            
            accessible_endpoints = sum(1 for result in endpoint_results.values() if result["accessible"])
            
            return {
                "api_healthy": api_healthy,
                "endpoint_results": endpoint_results,
                "accessible_endpoints": accessible_endpoints,
                "total_endpoints_tested": len(endpoints_to_test),
                "accessibility_rate": accessible_endpoints / len(endpoints_to_test) * 100,
                "status": "PASS" if api_healthy and accessible_endpoints >= len(endpoints_to_test) * 0.8 else "FAIL"
            }
            
        except Exception as e:
            return {
                "api_healthy": False,
                "error": str(e),
                "status": "FAIL"
            }
    
    def validate_enterprise_readiness(self) -> Dict[str, Any]:
        """Validate enterprise readiness metrics."""
        try:
            # Check for enterprise features
            enterprise_features = {
                "authentication": (self.project_root / "graph_rag" / "api" / "routers" / "enterprise_auth.py").exists(),
                "compliance": (self.project_root / "graph_rag" / "api" / "routers" / "compliance.py").exists(),
                "monitoring": (self.project_root / "graph_rag" / "api" / "routers" / "monitoring.py").exists(),
                "unified_platform": (self.project_root / "graph_rag" / "api" / "routers" / "unified_platform.py").exists()
            }
            
            # Check configuration files
            config_files = {
                "docker_compose": (self.project_root / "docker-compose.yml").exists(),
                "makefile": (self.project_root / "Makefile").exists(),
                "pyproject": (self.project_root / "pyproject.toml").exists(),
                "requirements": (self.project_root / "requirements.txt").exists() or (self.project_root / "pyproject.toml").exists()
            }
            
            # Test basic scalability metrics
            scalability_metrics = {
                "database_optimization": len([db for db in self.get_database_list() if "optimized" in db.lower()]) > 0,
                "caching_enabled": any("cache" in router.lower() for router in self.get_router_list()),
                "monitoring_available": "monitoring" in self.get_router_list()
            }
            
            enterprise_ready = (
                sum(enterprise_features.values()) >= 3 and
                sum(config_files.values()) >= 3 and
                sum(scalability_metrics.values()) >= 2
            )
            
            return {
                "enterprise_ready": enterprise_ready,
                "enterprise_features": enterprise_features,
                "config_files": config_files,
                "scalability_metrics": scalability_metrics,
                "status": "PASS" if enterprise_ready else "FAIL"
            }
            
        except Exception as e:
            return {
                "enterprise_ready": False,
                "error": str(e),
                "status": "FAIL"
            }
    
    def run_regression_tests(self) -> Dict[str, Any]:
        """Run regression testing to ensure no breaking changes."""
        try:
            # Run pytest with coverage
            result = subprocess.run(
                ["uv", "run", "pytest", "tests/", "--tb=short", "-q"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            test_passed = result.returncode == 0
            
            # Parse test results
            output_lines = result.stdout.split('\n')
            test_summary = ""
            for line in output_lines:
                if "passed" in line or "failed" in line or "error" in line:
                    test_summary = line
                    break
            
            return {
                "regression_tests_passed": test_passed,
                "test_output": result.stdout,
                "test_errors": result.stderr,
                "test_summary": test_summary,
                "return_code": result.returncode,
                "status": "PASS" if test_passed else "FAIL"
            }
            
        except Exception as e:
            return {
                "regression_tests_passed": False,
                "error": str(e),
                "status": "FAIL"
            }
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive Epic 10 validation report."""
        print("🔍 Starting Epic 10 System Consolidation Validation...")
        
        # Run all validations
        validations = {
            "database_consolidation": self.validate_database_consolidation(),
            "router_consolidation": self.validate_router_consolidation(), 
            "epic7_pipeline_protection": self.validate_epic7_pipeline_protection(),
            "api_functionality": self.validate_api_functionality(),
            "enterprise_readiness": self.validate_enterprise_readiness(),
            "regression_tests": self.run_regression_tests()
        }
        
        # Calculate overall success rate
        passed_validations = sum(1 for v in validations.values() if v.get("status") == "PASS")
        total_validations = len(validations)
        success_rate = (passed_validations / total_validations) * 100
        
        # Determine overall Epic 10 status
        epic10_complete = success_rate >= 95  # 95% success rate required
        
        report = {
            "epic10_consolidation_complete": epic10_complete,
            "validation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "success_rate": success_rate,
            "passed_validations": passed_validations,
            "total_validations": total_validations,
            "validations": validations,
            "overall_status": "EPIC 10 COMPLETE" if epic10_complete else "CONSOLIDATION IN PROGRESS",
            "recommendations": self._generate_recommendations(validations)
        }
        
        return report
    
    def _generate_recommendations(self, validations: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on validation results."""
        recommendations = []
        
        # Database consolidation recommendations
        db_validation = validations.get("database_consolidation", {})
        if db_validation.get("status") == "FAIL":
            current_count = db_validation.get("current_count", 0)
            target_count = db_validation.get("target_count", 3)
            recommendations.append(
                f"Database consolidation incomplete: {current_count} databases found, target is {target_count}. "
                f"Run database migration scripts to consolidate remaining databases."
            )
        
        # Router consolidation recommendations  
        router_validation = validations.get("router_consolidation", {})
        if router_validation.get("status") == "FAIL":
            current_count = router_validation.get("current_count", 0)
            target_count = router_validation.get("target_count", 10)
            recommendations.append(
                f"API router consolidation incomplete: {current_count} routers found, target is {target_count}. "
                f"Consolidate related functionality into unified routers."
            )
        
        # Epic 7 pipeline recommendations
        pipeline_validation = validations.get("epic7_pipeline_protection", {})
        if pipeline_validation.get("status") == "FAIL":
            recommendations.append(
                "Epic 7 pipeline protection validation failed. Verify CRM database integrity, "
                "contact count (target: 16+), and pipeline value (target: $1,158,000+)."
            )
        
        # Enterprise readiness recommendations
        enterprise_validation = validations.get("enterprise_readiness", {})
        if enterprise_validation.get("status") == "FAIL":
            recommendations.append(
                "Enterprise readiness validation failed. Ensure all enterprise features "
                "(auth, compliance, monitoring, unified platform) are properly configured."
            )
        
        # Regression test recommendations
        regression_validation = validations.get("regression_tests", {})
        if regression_validation.get("status") == "FAIL":
            recommendations.append(
                "Regression tests failing. Review test output and fix any breaking changes "
                "introduced during consolidation process."
            )
        
        return recommendations


@pytest.fixture
def validation_framework():
    """Provide Epic 10 validation framework for tests."""
    return Epic10ValidationFramework()


class TestEpic10SystemValidation:
    """Epic 10 System Consolidation Validation Test Suite."""
    
    def test_database_consolidation_validation(self, validation_framework):
        """Test database consolidation completion."""
        result = validation_framework.validate_database_consolidation()
        
        assert result["status"] == "PASS", f"Database consolidation failed: {result}"
        assert result["current_count"] <= result["target_count"], (
            f"Too many databases: {result['current_count']} found, "
            f"target is {result['target_count']}"
        )
        assert result["expected_dbs_present"], (
            f"Missing expected consolidated databases: {result['expected_databases']}"
        )
    
    def test_router_consolidation_validation(self, validation_framework):
        """Test API router consolidation completion."""
        result = validation_framework.validate_router_consolidation()
        
        assert result["status"] == "PASS", f"Router consolidation failed: {result}"
        assert result["current_count"] <= result["target_count"], (
            f"Too many routers: {result['current_count']} found, "
            f"target is {result['target_count']}"
        )
        assert result["expected_routers_present"], (
            f"Missing expected consolidated routers: {result['expected_routers']}"
        )
    
    def test_epic7_pipeline_protection(self, validation_framework):
        """Test Epic 7 pipeline protection and value integrity."""
        result = validation_framework.validate_epic7_pipeline_protection()
        
        assert result["status"] == "PASS", f"Epic 7 pipeline protection failed: {result}"
        assert result["pipeline_protected"], "Epic 7 pipeline not properly protected"
        assert result["contacts_count"] >= result["target_contacts"], (
            f"Insufficient contacts: {result['contacts_count']} found, "
            f"minimum {result['target_contacts']} required"
        )
        assert result["total_pipeline_value"] >= result["target_value"], (
            f"Pipeline value below target: ${result['total_pipeline_value']:,.2f} found, "
            f"minimum ${result['target_value']:,.2f} required"
        )
    
    def test_api_functionality_validation(self, validation_framework):
        """Test API functionality and endpoint accessibility."""
        result = validation_framework.validate_api_functionality()
        
        assert result["status"] == "PASS", f"API functionality validation failed: {result}"
        assert result["api_healthy"], "API health check failed"
        assert result["accessibility_rate"] >= 80, (
            f"API accessibility too low: {result['accessibility_rate']:.1f}%, minimum 80% required"
        )
    
    def test_enterprise_readiness_validation(self, validation_framework):
        """Test enterprise readiness for Fortune 500 scalability."""
        result = validation_framework.validate_enterprise_readiness()
        
        assert result["status"] == "PASS", f"Enterprise readiness validation failed: {result}"
        assert result["enterprise_ready"], "System not enterprise ready"
        
        # Verify specific enterprise features
        features = result["enterprise_features"]
        assert features["authentication"], "Enterprise authentication missing"
        assert features["compliance"], "Compliance features missing"
        assert features["monitoring"], "Monitoring capabilities missing"
    
    def test_regression_testing_validation(self, validation_framework):
        """Test regression testing to ensure no breaking changes."""
        result = validation_framework.validate_regression_tests()
        
        assert result["status"] == "PASS", f"Regression testing failed: {result}"
        assert result["regression_tests_passed"], (
            f"Regression tests failing: {result.get('test_summary', 'Unknown error')}"
        )
    
    def test_overall_epic10_completion(self, validation_framework):
        """Test overall Epic 10 consolidation completion."""
        report = validation_framework.generate_validation_report()
        
        print("\n" + "="*80)
        print("EPIC 10 SYSTEM CONSOLIDATION VALIDATION REPORT")
        print("="*80)
        print(f"Overall Status: {report['overall_status']}")
        print(f"Success Rate: {report['success_rate']:.1f}%")
        print(f"Passed Validations: {report['passed_validations']}/{report['total_validations']}")
        print("\nValidation Results:")
        for name, validation in report['validations'].items():
            status = validation.get('status', 'UNKNOWN')
            print(f"  {name}: {status}")
        
        if report['recommendations']:
            print("\nRecommendations:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"  {i}. {rec}")
        
        print("="*80)
        
        assert report["epic10_consolidation_complete"], (
            f"Epic 10 consolidation not complete. Success rate: {report['success_rate']:.1f}%, "
            f"minimum 95% required. Recommendations: {report['recommendations']}"
        )


if __name__ == "__main__":
    """Run Epic 10 validation as standalone script."""
    framework = Epic10ValidationFramework()
    report = framework.generate_validation_report()
    
    # Save report to file
    report_file = framework.project_root / "epic10_validation_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\nValidation report saved to: {report_file}")
    
    # Exit with appropriate code
    exit(0 if report["epic10_consolidation_complete"] else 1)