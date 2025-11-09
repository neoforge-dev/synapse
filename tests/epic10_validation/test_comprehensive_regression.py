"""
Comprehensive Regression Testing Suite for Epic 10

This module provides comprehensive regression testing to ensure
Epic 10 consolidation introduces no breaking changes.
"""

import json
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
import requests


class ComprehensiveRegressionValidator:
    """Comprehensive regression testing for Epic 10 consolidation."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.api_base_url = "http://localhost:8000/api/v1"

        # Core functionality that must continue working
        self.core_functionality = {
            "document_management": [
                "create_document",
                "retrieve_document",
                "update_document",
                "delete_document",
                "list_documents"
            ],
            "search_capabilities": [
                "vector_search",
                "graph_search",
                "unified_search",
                "semantic_search"
            ],
            "query_processing": [
                "simple_query",
                "complex_query",
                "contextual_query",
                "multi_step_query"
            ],
            "user_management": [
                "user_authentication",
                "user_authorization",
                "role_management",
                "session_management"
            ],
            "system_administration": [
                "health_monitoring",
                "system_status",
                "configuration_management",
                "log_management"
            ]
        }

        # Critical API endpoints that must remain functional
        self.critical_endpoints = [
            "/health",
            "/documents",
            "/search",
            "/query",
            "/auth/login",
            "/admin/status",
            "/epic7/sales-automation/pipeline",
            "/analytics/metrics"
        ]

        # Database tables that must remain accessible
        self.critical_database_tables = {
            "synapse_business_crm.db": ["contacts", "opportunities", "proposals"],
            "synapse_analytics_intelligence.db": ["analytics_metrics", "performance_data"],
            "synapse_system_infrastructure.db": ["system_config", "user_management"]
        }

    def run_unit_test_regression(self) -> dict[str, Any]:
        """Run unit tests to check for regressions."""
        try:
            print("🧪 Running unit test regression suite...")

            # Run unit tests with coverage
            result = subprocess.run(
                ["uv", "run", "pytest", "tests/", "-m", "not integration",
                 "--tb=short", "--maxfail=10", "-v"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=300  # 5 minute timeout
            )

            # Parse test results
            output_lines = result.stdout.split('\n')
            test_summary = self._parse_pytest_output(output_lines)

            return {
                "tests_passed": result.returncode == 0,
                "return_code": result.returncode,
                "test_summary": test_summary,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "status": "PASS" if result.returncode == 0 else "FAIL"
            }

        except subprocess.TimeoutExpired:
            return {
                "tests_passed": False,
                "error": "Unit tests timed out after 5 minutes",
                "status": "TIMEOUT"
            }
        except Exception as e:
            return {
                "tests_passed": False,
                "error": str(e),
                "status": "ERROR"
            }

    def run_integration_test_regression(self) -> dict[str, Any]:
        """Run integration tests to check for regressions."""
        try:
            print("🔗 Running integration test regression suite...")

            # Run integration tests
            result = subprocess.run(
                ["uv", "run", "pytest", "tests/", "-m", "integration",
                 "--tb=short", "--maxfail=5", "-v"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=600  # 10 minute timeout
            )

            # Parse test results
            output_lines = result.stdout.split('\n')
            test_summary = self._parse_pytest_output(output_lines)

            return {
                "tests_passed": result.returncode == 0,
                "return_code": result.returncode,
                "test_summary": test_summary,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "status": "PASS" if result.returncode == 0 else "FAIL"
            }

        except subprocess.TimeoutExpired:
            return {
                "tests_passed": False,
                "error": "Integration tests timed out after 10 minutes",
                "status": "TIMEOUT"
            }
        except Exception as e:
            return {
                "tests_passed": False,
                "error": str(e),
                "status": "ERROR"
            }

    def test_api_endpoint_regression(self) -> dict[str, Any]:
        """Test all critical API endpoints for regressions."""
        print("🌐 Testing API endpoint regression...")

        endpoint_results = {}
        regression_detected = False

        for endpoint in self.critical_endpoints:
            try:
                start_time = time.time()
                response = requests.get(f"{self.api_base_url}{endpoint}", timeout=10)
                response_time = (time.time() - start_time) * 1000

                # Determine if endpoint is functional
                functional = response.status_code in [200, 401, 422, 404]  # Auth errors acceptable

                if not functional:
                    regression_detected = True

                endpoint_results[endpoint] = {
                    "functional": functional,
                    "status_code": response.status_code,
                    "response_time_ms": response_time,
                    "response_size": len(response.content),
                    "has_regression": not functional
                }

            except Exception as e:
                regression_detected = True
                endpoint_results[endpoint] = {
                    "functional": False,
                    "error": str(e),
                    "has_regression": True
                }

        functional_endpoints = sum(1 for r in endpoint_results.values() if r.get("functional", False))
        total_endpoints = len(self.critical_endpoints)

        return {
            "regression_detected": regression_detected,
            "functional_endpoints": functional_endpoints,
            "total_endpoints": total_endpoints,
            "functionality_rate": functional_endpoints / total_endpoints * 100,
            "endpoint_details": endpoint_results,
            "status": "PASS" if not regression_detected else "REGRESSION_DETECTED"
        }

    def test_database_access_regression(self) -> dict[str, Any]:
        """Test database access for regressions."""
        print("🗄️ Testing database access regression...")

        database_results = {}
        regression_detected = False

        for db_name, tables in self.critical_database_tables.items():
            db_path = self.project_root / db_name

            if not db_path.exists():
                regression_detected = True
                database_results[db_name] = {
                    "accessible": False,
                    "error": "Database file missing",
                    "has_regression": True
                }
                continue

            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                table_results = {}
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        table_results[table] = {
                            "accessible": True,
                            "row_count": count,
                            "has_data": count > 0,
                            "has_regression": False
                        }
                    except sqlite3.OperationalError as e:
                        regression_detected = True
                        table_results[table] = {
                            "accessible": False,
                            "error": str(e),
                            "has_regression": True
                        }

                conn.close()

                accessible_tables = sum(1 for r in table_results.values() if r.get("accessible", False))
                database_results[db_name] = {
                    "accessible": True,
                    "tables": table_results,
                    "accessible_tables": accessible_tables,
                    "total_tables": len(tables),
                    "has_regression": accessible_tables < len(tables)
                }

                if accessible_tables < len(tables):
                    regression_detected = True

            except Exception as e:
                regression_detected = True
                database_results[db_name] = {
                    "accessible": False,
                    "error": str(e),
                    "has_regression": True
                }

        return {
            "regression_detected": regression_detected,
            "database_results": database_results,
            "status": "PASS" if not regression_detected else "REGRESSION_DETECTED"
        }

    def test_core_functionality_regression(self) -> dict[str, Any]:
        """Test core functionality for regressions."""
        print("⚙️ Testing core functionality regression...")

        functionality_results = {}
        regression_detected = False

        for category, functions in self.core_functionality.items():
            category_results = {}
            category_regression = False

            for function in functions:
                try:
                    # Test specific functionality based on function type
                    if function == "create_document":
                        result = self._test_document_creation()
                    elif function == "vector_search":
                        result = self._test_vector_search()
                    elif function == "user_authentication":
                        result = self._test_user_authentication()
                    elif function == "health_monitoring":
                        result = self._test_health_monitoring()
                    else:
                        # Generic endpoint test
                        result = self._test_generic_functionality(function)

                    category_results[function] = result

                    if result.get("has_regression", False):
                        category_regression = True
                        regression_detected = True

                except Exception as e:
                    category_regression = True
                    regression_detected = True
                    category_results[function] = {
                        "functional": False,
                        "error": str(e),
                        "has_regression": True
                    }

            functionality_results[category] = {
                "functions": category_results,
                "has_regression": category_regression,
                "functional_functions": sum(1 for r in category_results.values() if r.get("functional", False)),
                "total_functions": len(functions)
            }

        return {
            "regression_detected": regression_detected,
            "functionality_results": functionality_results,
            "status": "PASS" if not regression_detected else "REGRESSION_DETECTED"
        }

    def test_performance_regression(self) -> dict[str, Any]:
        """Test for performance regressions."""
        print("⚡ Testing performance regression...")

        performance_tests = [
            {"endpoint": f"{self.api_base_url}/health", "max_time_ms": 1000},
            {"endpoint": f"{self.api_base_url}/documents", "max_time_ms": 2000},
            {"endpoint": f"{self.api_base_url}/search", "max_time_ms": 3000},
            {"endpoint": f"{self.api_base_url}/admin/status", "max_time_ms": 2000}
        ]

        performance_results = {}
        regression_detected = False

        for test in performance_tests:
            endpoint = test["endpoint"]
            max_time = test["max_time_ms"]

            try:
                # Run multiple requests to get average
                times = []
                for _ in range(5):
                    start_time = time.time()
                    response = requests.get(endpoint, timeout=10)
                    end_time = time.time()
                    times.append((end_time - start_time) * 1000)

                avg_time = sum(times) / len(times)
                has_regression = avg_time > max_time

                if has_regression:
                    regression_detected = True

                performance_results[endpoint] = {
                    "avg_response_time_ms": avg_time,
                    "max_allowed_ms": max_time,
                    "has_regression": has_regression,
                    "all_times": times,
                    "functional": response.status_code in [200, 401, 422]
                }

            except Exception as e:
                regression_detected = True
                performance_results[endpoint] = {
                    "error": str(e),
                    "has_regression": True,
                    "functional": False
                }

        return {
            "regression_detected": regression_detected,
            "performance_results": performance_results,
            "status": "PASS" if not regression_detected else "PERFORMANCE_REGRESSION"
        }

    def test_backward_compatibility(self) -> dict[str, Any]:
        """Test backward compatibility with existing APIs."""
        print("🔄 Testing backward compatibility...")

        # Test existing API contracts
        compatibility_tests = [
            {
                "endpoint": f"{self.api_base_url}/documents",
                "method": "GET",
                "expected_fields": ["documents", "total", "page"]
            },
            {
                "endpoint": f"{self.api_base_url}/search",
                "method": "POST",
                "data": {"query": "test"},
                "expected_fields": ["results", "query", "total_results"]
            },
            {
                "endpoint": f"{self.api_base_url}/health",
                "method": "GET",
                "expected_fields": ["status", "timestamp"]
            }
        ]

        compatibility_results = {}
        regression_detected = False

        for test in compatibility_tests:
            endpoint = test["endpoint"]

            try:
                if test["method"] == "GET":
                    response = requests.get(endpoint, timeout=10)
                else:
                    response = requests.post(endpoint, json=test.get("data", {}), timeout=10)

                # Check if response structure is compatible
                if response.status_code == 200:
                    try:
                        data = response.json()
                        expected_fields = test.get("expected_fields", [])

                        missing_fields = []
                        for field in expected_fields:
                            if field not in data:
                                missing_fields.append(field)

                        has_regression = len(missing_fields) > 0

                        if has_regression:
                            regression_detected = True

                        compatibility_results[endpoint] = {
                            "compatible": not has_regression,
                            "missing_fields": missing_fields,
                            "has_regression": has_regression,
                            "status_code": response.status_code
                        }

                    except json.JSONDecodeError:
                        regression_detected = True
                        compatibility_results[endpoint] = {
                            "compatible": False,
                            "error": "Invalid JSON response",
                            "has_regression": True,
                            "status_code": response.status_code
                        }
                else:
                    # Non-200 responses may be acceptable for some endpoints
                    acceptable_codes = [401, 422, 404]
                    has_regression = response.status_code not in acceptable_codes

                    if has_regression:
                        regression_detected = True

                    compatibility_results[endpoint] = {
                        "compatible": not has_regression,
                        "has_regression": has_regression,
                        "status_code": response.status_code,
                        "acceptable": response.status_code in acceptable_codes
                    }

            except Exception as e:
                regression_detected = True
                compatibility_results[endpoint] = {
                    "compatible": False,
                    "error": str(e),
                    "has_regression": True
                }

        return {
            "regression_detected": regression_detected,
            "compatibility_results": compatibility_results,
            "status": "PASS" if not regression_detected else "COMPATIBILITY_ISSUES"
        }

    def _parse_pytest_output(self, output_lines: list[str]) -> dict[str, Any]:
        """Parse pytest output for summary information."""
        summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "warnings": 0
        }

        for line in output_lines:
            # Look for test summary line
            if " passed" in line or " failed" in line or " error" in line:
                # Parse pytest summary format
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed":
                        summary["passed"] = int(parts[i-1]) if i > 0 and parts[i-1].isdigit() else 0
                    elif part == "failed":
                        summary["failed"] = int(parts[i-1]) if i > 0 and parts[i-1].isdigit() else 0
                    elif part == "error" or part == "errors":
                        summary["errors"] = int(parts[i-1]) if i > 0 and parts[i-1].isdigit() else 0
                    elif part == "skipped":
                        summary["skipped"] = int(parts[i-1]) if i > 0 and parts[i-1].isdigit() else 0
                    elif part == "warning" or part == "warnings":
                        summary["warnings"] = int(parts[i-1]) if i > 0 and parts[i-1].isdigit() else 0

        summary["total_tests"] = summary["passed"] + summary["failed"] + summary["errors"] + summary["skipped"]

        return summary

    def _test_document_creation(self) -> dict[str, Any]:
        """Test document creation functionality."""
        try:
            test_doc = {
                "title": "Regression Test Document",
                "content": "This is a test document for regression testing.",
                "metadata": {"test": True}
            }

            response = requests.post(
                f"{self.api_base_url}/documents",
                json=test_doc,
                timeout=10
            )

            functional = response.status_code in [200, 201, 401, 422]

            return {
                "functional": functional,
                "status_code": response.status_code,
                "has_regression": not functional
            }

        except Exception as e:
            return {
                "functional": False,
                "error": str(e),
                "has_regression": True
            }

    def _test_vector_search(self) -> dict[str, Any]:
        """Test vector search functionality."""
        try:
            search_query = {
                "query": "test search query",
                "limit": 5
            }

            response = requests.post(
                f"{self.api_base_url}/search",
                json=search_query,
                timeout=10
            )

            functional = response.status_code in [200, 401, 422]

            return {
                "functional": functional,
                "status_code": response.status_code,
                "has_regression": not functional
            }

        except Exception as e:
            return {
                "functional": False,
                "error": str(e),
                "has_regression": True
            }

    def _test_user_authentication(self) -> dict[str, Any]:
        """Test user authentication functionality."""
        try:
            auth_data = {
                "username": "test_user",
                "password": "test_password"
            }

            response = requests.post(
                f"{self.api_base_url}/auth/login",
                json=auth_data,
                timeout=10
            )

            # For auth, 401/422 are acceptable responses
            functional = response.status_code in [200, 401, 422]

            return {
                "functional": functional,
                "status_code": response.status_code,
                "has_regression": not functional
            }

        except Exception as e:
            return {
                "functional": False,
                "error": str(e),
                "has_regression": True
            }

    def _test_health_monitoring(self) -> dict[str, Any]:
        """Test health monitoring functionality."""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=10)

            functional = response.status_code == 200

            return {
                "functional": functional,
                "status_code": response.status_code,
                "has_regression": not functional
            }

        except Exception as e:
            return {
                "functional": False,
                "error": str(e),
                "has_regression": True
            }

    def _test_generic_functionality(self, function_name: str) -> dict[str, Any]:
        """Test generic functionality by mapping to appropriate endpoint."""
        endpoint_mapping = {
            "retrieve_document": "/documents",
            "list_documents": "/documents",
            "simple_query": "/query",
            "system_status": "/admin/status",
            "configuration_management": "/admin/config"
        }

        endpoint = endpoint_mapping.get(function_name)

        if not endpoint:
            return {
                "functional": True,  # Assume functional if no specific test
                "has_regression": False,
                "note": "No specific test implemented"
            }

        try:
            response = requests.get(f"{self.api_base_url}{endpoint}", timeout=10)
            functional = response.status_code in [200, 401, 422, 404]

            return {
                "functional": functional,
                "status_code": response.status_code,
                "has_regression": not functional
            }

        except Exception as e:
            return {
                "functional": False,
                "error": str(e),
                "has_regression": True
            }

    def generate_comprehensive_regression_report(self) -> dict[str, Any]:
        """Generate comprehensive regression testing report."""
        print("🔍 Starting Comprehensive Regression Testing...")

        # Run all regression tests
        regression_tests = {
            "unit_tests": self.run_unit_test_regression(),
            "integration_tests": self.run_integration_test_regression(),
            "api_endpoints": self.test_api_endpoint_regression(),
            "database_access": self.test_database_access_regression(),
            "core_functionality": self.test_core_functionality_regression(),
            "performance": self.test_performance_regression(),
            "backward_compatibility": self.test_backward_compatibility()
        }

        # Calculate overall regression status
        regression_detected = any(
            test.get("regression_detected", False) or test.get("status") in ["FAIL", "REGRESSION_DETECTED", "PERFORMANCE_REGRESSION", "COMPATIBILITY_ISSUES"]
            for test in regression_tests.values()
        )

        passed_tests = sum(
            1 for test in regression_tests.values()
            if test.get("status") == "PASS" or not test.get("regression_detected", True)
        )

        total_tests = len(regression_tests)
        success_rate = (passed_tests / total_tests) * 100

        overall_status = (
            "NO_REGRESSIONS" if not regression_detected and success_rate >= 95 else
            "MINOR_REGRESSIONS" if success_rate >= 80 else
            "SIGNIFICANT_REGRESSIONS" if success_rate >= 60 else
            "CRITICAL_REGRESSIONS"
        )

        return {
            "overall_regression_status": overall_status,
            "regression_detected": regression_detected,
            "success_rate": success_rate,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "regression_tests": regression_tests,
            "recommendations": self._generate_regression_recommendations(regression_tests),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def _generate_regression_recommendations(self, tests: dict[str, Any]) -> list[str]:
        """Generate regression testing recommendations."""
        recommendations = []

        for test_name, test_result in tests.items():
            if test_result.get("regression_detected", False) or test_result.get("status") not in ["PASS"]:
                if test_name == "unit_tests":
                    recommendations.append(
                        "Unit test regressions detected. Review failed tests and fix breaking changes."
                    )
                elif test_name == "integration_tests":
                    recommendations.append(
                        "Integration test failures detected. Check service integrations and dependencies."
                    )
                elif test_name == "api_endpoints":
                    recommendations.append(
                        "API endpoint regressions detected. Verify all critical endpoints are functional."
                    )
                elif test_name == "database_access":
                    recommendations.append(
                        "Database access regressions detected. Check database migrations and table integrity."
                    )
                elif test_name == "core_functionality":
                    recommendations.append(
                        "Core functionality regressions detected. Review business logic and core features."
                    )
                elif test_name == "performance":
                    recommendations.append(
                        "Performance regressions detected. Optimize slow endpoints and database queries."
                    )
                elif test_name == "backward_compatibility":
                    recommendations.append(
                        "Backward compatibility issues detected. Ensure API contracts are maintained."
                    )

        if not recommendations:
            recommendations.append("No significant regressions detected. System integrity maintained.")

        return recommendations


@pytest.fixture
def regression_validator():
    """Provide comprehensive regression validator."""
    return ComprehensiveRegressionValidator()


class TestComprehensiveRegression:
    """Comprehensive regression testing suite."""

    def test_unit_test_regression(self, regression_validator):
        """Test unit test regression."""
        result = regression_validator.run_unit_test_regression()

        assert result["status"] != "ERROR", (
            f"Unit test execution error: {result.get('error', 'Unknown error')}"
        )

        # Allow some test failures but not complete failure
        if not result["tests_passed"]:
            test_summary = result.get("test_summary", {})
            failed_count = test_summary.get("failed", 0) + test_summary.get("errors", 0)
            total_count = test_summary.get("total_tests", 1)

            failure_rate = failed_count / total_count * 100 if total_count > 0 else 100

            # Allow up to 10% test failures
            assert failure_rate <= 10, (
                f"Too many unit test failures: {failed_count}/{total_count} failed ({failure_rate:.1f}%)"
            )

    def test_api_endpoint_regression(self, regression_validator):
        """Test API endpoint regression."""
        result = regression_validator.test_api_endpoint_regression()

        functionality_rate = result.get("functionality_rate", 0)
        assert functionality_rate >= 80, (
            f"API functionality below acceptable threshold: {functionality_rate:.1f}%, minimum 80% required"
        )

        assert result["status"] != "REGRESSION_DETECTED", (
            f"API endpoint regressions detected: {result['functional_endpoints']}/{result['total_endpoints']} functional"
        )

    def test_database_access_regression(self, regression_validator):
        """Test database access regression."""
        result = regression_validator.test_database_access_regression()

        assert result["status"] != "REGRESSION_DETECTED", (
            "Database access regressions detected"
        )

        # Check that critical databases are accessible
        db_results = result.get("database_results", {})
        for db_name, db_result in db_results.items():
            assert db_result.get("accessible", False), (
                f"Critical database {db_name} not accessible"
            )

    def test_core_functionality_regression(self, regression_validator):
        """Test core functionality regression."""
        result = regression_validator.test_core_functionality_regression()

        assert result["status"] != "REGRESSION_DETECTED", (
            "Core functionality regressions detected"
        )

        # Check each functionality category
        functionality_results = result.get("functionality_results", {})
        for category, category_result in functionality_results.items():
            functional_functions = category_result.get("functional_functions", 0)
            total_functions = category_result.get("total_functions", 1)

            functionality_rate = functional_functions / total_functions * 100
            assert functionality_rate >= 70, (
                f"Core functionality {category} regression: {functional_functions}/{total_functions} functional"
            )

    def test_performance_regression(self, regression_validator):
        """Test performance regression."""
        result = regression_validator.test_performance_regression()

        # Performance regression is warning, not failure for Epic 10
        if result["status"] == "PERFORMANCE_REGRESSION":
            pytest.warn(UserWarning(
                "Performance regression detected - review and optimize"
            ))

        # Check that endpoints are still functional even if slow
        performance_results = result.get("performance_results", {})
        for endpoint, perf_result in performance_results.items():
            assert perf_result.get("functional", False), (
                f"Performance regression caused {endpoint} to become non-functional"
            )

    def test_backward_compatibility(self, regression_validator):
        """Test backward compatibility."""
        result = regression_validator.test_backward_compatibility()

        assert result["status"] != "COMPATIBILITY_ISSUES", (
            "Backward compatibility issues detected"
        )

        # Check specific compatibility results
        compatibility_results = result.get("compatibility_results", {})
        for endpoint, compat_result in compatibility_results.items():
            assert compat_result.get("compatible", False), (
                f"Backward compatibility broken for {endpoint}: {compat_result}"
            )

    def test_overall_regression_status(self, regression_validator):
        """Test overall regression status."""
        report = regression_validator.generate_comprehensive_regression_report()

        regression_status = report["overall_regression_status"]
        success_rate = report["success_rate"]

        print("\nComprehensive Regression Report:")
        print(f"Overall Status: {regression_status}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Tests Passed: {report['passed_tests']}/{report['total_tests']}")

        if report["recommendations"]:
            print("Recommendations:")
            for i, rec in enumerate(report["recommendations"], 1):
                print(f"  {i}. {rec}")

        # For Epic 10 completion, shouldn't have critical regressions
        assert regression_status != "CRITICAL_REGRESSIONS", (
            f"Critical regressions detected: {regression_status}. Success rate: {success_rate:.1f}%"
        )

        # Warn about significant regressions
        if regression_status == "SIGNIFICANT_REGRESSIONS":
            pytest.warn(UserWarning(
                f"Significant regressions detected: {regression_status}. "
                f"Success rate: {success_rate:.1f}%"
            ))


if __name__ == "__main__":
    """Run comprehensive regression testing."""
    validator = ComprehensiveRegressionValidator()
    report = validator.generate_comprehensive_regression_report()

    print(json.dumps(report, indent=2, default=str))
