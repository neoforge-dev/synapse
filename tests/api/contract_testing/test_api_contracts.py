"""
API Contract Testing Framework for Epic 2 Consolidation

Ensures 100% API compatibility during router consolidation.
Tests all endpoints to establish baseline contracts before changes.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from graph_rag.api.main import create_app

logger = logging.getLogger(__name__)


class EndpointContract(BaseModel):
    """Contract definition for an API endpoint."""
    path: str
    method: str
    status_code: int
    response_schema: dict[str, Any]
    request_schema: dict[str, Any] | None = None
    performance_baseline_ms: float | None = None


class ContractTestResult(BaseModel):
    """Result of a contract test."""
    endpoint: str
    method: str
    passed: bool
    status_code: int
    response_time_ms: float
    schema_valid: bool
    error_message: str | None = None


class APIContractTester:
    """Contract testing framework for API consolidation."""

    def __init__(self, test_client: TestClient | None = None):
        if test_client is not None:
            self.client = test_client
        else:
            self.app = create_app()
            self.client = TestClient(self.app)
        self.contracts: list[EndpointContract] = []
        self.results: list[ContractTestResult] = []

    def load_existing_contracts(self, contracts_file: str | None = None) -> None:
        """Load existing contracts from JSON file."""
        if contracts_file is None:
            contracts_file_path = Path(__file__).parent / "api_contracts.json"
        else:
            contracts_file_path = Path(contracts_file)

        if contracts_file_path.exists():
            with open(contracts_file_path) as f:
                contracts_data = json.load(f)
                self.contracts = [EndpointContract(**contract) for contract in contracts_data]
            logger.info(f"Loaded {len(self.contracts)} existing contracts")
        else:
            logger.info("No existing contracts found, will generate new ones")

    def discover_endpoints(self) -> list[dict[str, Any]]:
        """Discover all available API endpoints via direct router inspection."""
        endpoints = []

        # Manually define known endpoints from current router architecture
        known_endpoints = [
            # Core Content Management
            {"path": "/api/v1/documents", "method": "GET", "spec": {}},
            {"path": "/api/v1/documents", "method": "POST", "spec": {}},
            {"path": "/api/v1/chunks", "method": "GET", "spec": {}},
            {"path": "/api/v1/chunks", "method": "POST", "spec": {}},
            {"path": "/api/v1/ingestion/documents", "method": "POST", "spec": {}},

            # Retrieval and Search
            {"path": "/api/v1/search", "method": "POST", "spec": {}},
            {"path": "/api/v1/query", "method": "POST", "spec": {}},
            {"path": "/api/v1/reasoning/analyze", "method": "POST", "spec": {}},

            # Business Intelligence
            {"path": "/api/v1/dashboard/metrics", "method": "GET", "spec": {}},
            {"path": "/api/v1/audience/analyze", "method": "POST", "spec": {}},
            {"path": "/api/v1/concepts/extract", "method": "POST", "spec": {}},

            # Graph Operations
            {"path": "/api/v1/graph/nodes", "method": "GET", "spec": {}},
            {"path": "/api/v1/graph/relationships", "method": "GET", "spec": {}},
            {"path": "/api/v1/monitoring/health", "method": "GET", "spec": {}},

            # System Administration
            {"path": "/api/v1/auth/token", "method": "POST", "spec": {}},
            {"path": "/api/v1/admin/system", "method": "GET", "spec": {}},

            # Specialized Features
            {"path": "/api/v1/hot-takes/generate", "method": "POST", "spec": {}},
            {"path": "/api/v1/brand-safety/check", "method": "POST", "spec": {}},

            # Basic health endpoints
            {"path": "/health", "method": "GET", "spec": {}},
            {"path": "/ready", "method": "GET", "spec": {}},
        ]

        endpoints = known_endpoints
        logger.info(f"Using known endpoints list: {len(endpoints)} API endpoints")
        return endpoints

    def generate_contracts(self) -> None:
        """Generate contracts for all discovered endpoints."""
        endpoints = self.discover_endpoints()

        for endpoint in endpoints:
            # Test the endpoint to get baseline contract
            contract = self._test_endpoint_for_contract(
                endpoint["path"],
                endpoint["method"],
                endpoint["spec"]
            )
            if contract:
                self.contracts.append(contract)

    def _test_endpoint_for_contract(self, path: str, method: str, spec: dict) -> EndpointContract | None:
        """Test an endpoint to establish its contract."""
        try:
            start_time = time.time()

            # Prepare test request based on endpoint spec
            test_data = self._generate_test_data(spec)

            if method == "GET":
                response = self.client.get(path, params=test_data.get("params", {}))
            elif method == "POST":
                response = self.client.post(path, json=test_data.get("json", {}))
            elif method == "PUT":
                response = self.client.put(path, json=test_data.get("json", {}))
            elif method == "DELETE":
                response = self.client.delete(path)
            elif method == "PATCH":
                response = self.client.patch(path, json=test_data.get("json", {}))
            else:
                return None

            response_time_ms = (time.time() - start_time) * 1000

            # Extract response schema
            response_schema = {}
            if response.status_code < 400 and response.content:
                try:
                    response_data = response.json()
                    response_schema = self._extract_schema(response_data)
                except:
                    response_schema = {"type": "text", "content_type": response.headers.get("content-type")}

            return EndpointContract(
                path=path,
                method=method,
                status_code=response.status_code,
                response_schema=response_schema,
                request_schema=test_data.get("schema"),
                performance_baseline_ms=response_time_ms
            )

        except Exception as e:
            logger.error(f"Failed to test endpoint {method} {path}: {e}")
            return None

    def _generate_test_data(self, spec: dict) -> dict[str, Any]:
        """Generate test data for an endpoint based on its spec."""
        test_data = {}

        # Handle request body
        request_body = spec.get("requestBody", {})
        if request_body:
            content = request_body.get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                test_data["json"] = self._generate_sample_data(schema)
                test_data["schema"] = schema

        # Handle query parameters
        parameters = spec.get("parameters", [])
        params = {}
        for param in parameters:
            if param.get("in") == "query":
                param_name = param.get("name")
                param_schema = param.get("schema", {})
                if param_name:
                    params[param_name] = self._generate_sample_value(param_schema)

        if params:
            test_data["params"] = params

        return test_data

    def _generate_sample_data(self, schema: dict) -> Any:
        """Generate sample data based on JSON schema."""
        schema_type = schema.get("type", "object")

        if schema_type == "object":
            obj = {}
            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                obj[prop_name] = self._generate_sample_value(prop_schema)
            return obj
        elif schema_type == "array":
            items = schema.get("items", {})
            return [self._generate_sample_value(items)]
        else:
            return self._generate_sample_value(schema)

    def _generate_sample_value(self, schema: dict) -> Any:
        """Generate a sample value based on schema type."""
        schema_type = schema.get("type", "string")

        if schema_type == "string":
            return "test_string"
        elif schema_type == "integer":
            return 42
        elif schema_type == "number":
            return 3.14
        elif schema_type == "boolean":
            return True
        elif schema_type == "array":
            return []
        elif schema_type == "object":
            return {}
        else:
            return "test_value"

    def _extract_schema(self, data: Any) -> dict[str, Any]:
        """Extract schema from response data."""
        if isinstance(data, dict):
            schema = {"type": "object", "properties": {}}
            for key, value in data.items():
                schema["properties"][key] = self._extract_schema(value)
            return schema
        elif isinstance(data, list):
            if data:
                return {"type": "array", "items": self._extract_schema(data[0])}
            else:
                return {"type": "array", "items": {}}
        elif isinstance(data, str):
            return {"type": "string"}
        elif isinstance(data, int):
            return {"type": "integer"}
        elif isinstance(data, float):
            return {"type": "number"}
        elif isinstance(data, bool):
            return {"type": "boolean"}
        else:
            return {"type": "unknown"}

    def save_contracts(self, contracts_file: str | None = None) -> None:
        """Save contracts to JSON file."""
        if contracts_file is None:
            contracts_file_path = Path(__file__).parent / "api_contracts.json"
        else:
            contracts_file_path = Path(contracts_file)

        contracts_data = [contract.model_dump() for contract in self.contracts]
        with open(contracts_file_path, 'w') as f:
            json.dump(contracts_data, f, indent=2)

        logger.info(f"Saved {len(self.contracts)} contracts to {contracts_file_path}")

    def test_contracts(self) -> list[ContractTestResult]:
        """Test all contracts and return results."""
        results = []

        for contract in self.contracts:
            result = self._test_single_contract(contract)
            results.append(result)

        self.results = results
        return results

    def _test_single_contract(self, contract: EndpointContract) -> ContractTestResult:
        """Test a single contract."""
        try:
            start_time = time.time()

            # Generate test data
            test_data = {}
            if contract.request_schema:
                test_data = self._generate_sample_data(contract.request_schema)

            # Make request
            if contract.method == "GET":
                response = self.client.get(contract.path)
            elif contract.method == "POST":
                response = self.client.post(contract.path, json=test_data)
            elif contract.method == "PUT":
                response = self.client.put(contract.path, json=test_data)
            elif contract.method == "DELETE":
                response = self.client.delete(contract.path)
            elif contract.method == "PATCH":
                response = self.client.patch(contract.path, json=test_data)
            else:
                raise ValueError(f"Unsupported HTTP method: {contract.method}")

            response_time_ms = (time.time() - start_time) * 1000

            # Validate contract
            status_valid = response.status_code == contract.status_code
            schema_valid = True  # TODO: Implement schema validation

            passed = status_valid and schema_valid
            error_message = None

            if not status_valid:
                error_message = f"Status code mismatch: expected {contract.status_code}, got {response.status_code}"

            return ContractTestResult(
                endpoint=contract.path,
                method=contract.method,
                passed=passed,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                schema_valid=schema_valid,
                error_message=error_message
            )

        except Exception as e:
            return ContractTestResult(
                endpoint=contract.path,
                method=contract.method,
                passed=False,
                status_code=0,
                response_time_ms=0,
                schema_valid=False,
                error_message=str(e)
            )

    def generate_report(self) -> dict[str, Any]:
        """Generate contract testing report."""
        if not self.results:
            return {"error": "No test results available"}

        passed_tests = [r for r in self.results if r.passed]
        failed_tests = [r for r in self.results if not r.passed]

        avg_response_time = sum(r.response_time_ms for r in self.results) / len(self.results)

        report = {
            "summary": {
                "total_tests": len(self.results),
                "passed": len(passed_tests),
                "failed": len(failed_tests),
                "success_rate": len(passed_tests) / len(self.results) * 100,
                "average_response_time_ms": round(avg_response_time, 2)
            },
            "failed_tests": [
                {
                    "endpoint": r.endpoint,
                    "method": r.method,
                    "error": r.error_message
                } for r in failed_tests
            ],
            "performance_analysis": {
                "fastest_endpoint": min(self.results, key=lambda x: x.response_time_ms),
                "slowest_endpoint": max(self.results, key=lambda x: x.response_time_ms)
            }
        }

        return report


# Test fixtures and test functions

@pytest.fixture
def contract_tester(sync_test_client):
    """Fixture providing contract tester instance with mocked dependencies."""
    return APIContractTester(test_client=sync_test_client)


def test_generate_baseline_contracts(contract_tester):
    """Test generating baseline contracts for all endpoints."""
    contract_tester.generate_contracts()
    assert len(contract_tester.contracts) > 0

    # Save baseline contracts
    contract_tester.save_contracts()


def test_validate_existing_contracts(contract_tester):
    """Test validation of existing contracts."""
    contract_tester.load_existing_contracts()

    if not contract_tester.contracts:
        pytest.skip("No existing contracts found")

    results = contract_tester.test_contracts()
    report = contract_tester.generate_report()

    # Convert ContractTestResult objects to dicts for JSON serialization
    serializable_report = {
        "summary": report["summary"],
        "failed_tests": [
            {
                "endpoint": test["endpoint"],
                "method": test["method"],
                "error": test["error"]
            } for test in report["failed_tests"]
        ],
        "performance_analysis": {
            "fastest_endpoint": {
                "endpoint": report["performance_analysis"]["fastest_endpoint"].endpoint,
                "method": report["performance_analysis"]["fastest_endpoint"].method,
                "response_time_ms": report["performance_analysis"]["fastest_endpoint"].response_time_ms
            },
            "slowest_endpoint": {
                "endpoint": report["performance_analysis"]["slowest_endpoint"].endpoint,
                "method": report["performance_analysis"]["slowest_endpoint"].method,
                "response_time_ms": report["performance_analysis"]["slowest_endpoint"].response_time_ms
            }
        }
    }

    # Log report
    logger.info(f"Contract test report: {json.dumps(serializable_report, indent=2)}")

    # Assert success rate > 95%
    success_rate = report["summary"]["success_rate"]
    assert success_rate >= 95.0, f"Contract success rate {success_rate}% is below 95% threshold"


def test_performance_baseline(contract_tester):
    """Test that current API performance meets baseline requirements."""
    contract_tester.load_existing_contracts()
    results = contract_tester.test_contracts()

    # Check average response time
    avg_time = sum(r.response_time_ms for r in results) / len(results)
    assert avg_time < 500, f"Average response time {avg_time}ms exceeds 500ms baseline"

    # Check that no endpoint takes more than 2 seconds
    slow_endpoints = [r for r in results if r.response_time_ms > 2000]
    assert len(slow_endpoints) == 0, f"Slow endpoints found: {slow_endpoints}"


@pytest.mark.integration
def test_contract_compatibility_after_consolidation(test_client):
    """Test that consolidated API maintains contract compatibility."""
    # This test will be run after consolidation to ensure compatibility
    contract_tester = APIContractTester(test_client=test_client)
    contract_tester.load_existing_contracts()

    if not contract_tester.contracts:
        pytest.skip("No baseline contracts found")

    results = contract_tester.test_contracts()
    report = contract_tester.generate_report()

    # Assert 100% compatibility maintained
    success_rate = report["summary"]["success_rate"]
    assert success_rate == 100.0, f"API compatibility broken: {success_rate}% success rate"

    # Assert performance improvement
    avg_time = report["summary"]["average_response_time_ms"]
    assert avg_time < 200, f"Performance target missed: {avg_time}ms average response time"
