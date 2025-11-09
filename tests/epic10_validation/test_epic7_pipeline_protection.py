"""
Epic 7 Pipeline Protection Validation Tests

This module validates that Epic 7's $1,158,000 consultation pipeline
is protected during Epic 10 consolidation activities.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import requests


class Epic7PipelineValidator:
    """Validates Epic 7 pipeline protection during Epic 10 consolidation."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.api_base_url = "http://localhost:8000/api/v1"

        # Epic 7 pipeline requirements
        self.pipeline_requirements = {
            "minimum_contacts": 16,
            "minimum_pipeline_value": 1158000,
            "minimum_proposals": 3,
            "minimum_campaigns": 2
        }

        # Expected Epic 7 endpoints
        self.epic7_endpoints = [
            "/epic7/sales-automation/pipeline",
            "/epic7/sales-automation/contacts",
            "/epic7/sales-automation/proposals",
            "/epic7/sales-automation/campaigns",
            "/epic7/sales-automation/roi-calculator",
            "/epic7/sales-automation/consultation-detector"
        ]

    def validate_crm_database_integrity(self) -> dict[str, Any]:
        """Validate CRM database contains Epic 7 pipeline data."""
        crm_db_path = self.project_root / "synapse_business_crm.db"

        if not crm_db_path.exists():
            return {
                "database_exists": False,
                "status": "CRITICAL_FAILURE",
                "error": "CRM database missing - Epic 7 pipeline at risk"
            }

        try:
            conn = sqlite3.connect(crm_db_path)
            cursor = conn.cursor()

            # Check contacts table
            contacts_data = self._validate_contacts_table(cursor)

            # Check opportunities/pipeline table
            pipeline_data = self._validate_pipeline_table(cursor)

            # Check proposals table
            proposals_data = self._validate_proposals_table(cursor)

            # Check campaigns table
            campaigns_data = self._validate_campaigns_table(cursor)

            # Check for Epic 7 specific data integrity
            epic7_integrity = self._validate_epic7_data_integrity(cursor)

            conn.close()

            # Calculate overall pipeline health
            pipeline_healthy = (
                contacts_data["count"] >= self.pipeline_requirements["minimum_contacts"] and
                pipeline_data["total_value"] >= self.pipeline_requirements["minimum_pipeline_value"] and
                proposals_data["count"] >= self.pipeline_requirements["minimum_proposals"] and
                campaigns_data["count"] >= self.pipeline_requirements["minimum_campaigns"]
            )

            return {
                "database_exists": True,
                "pipeline_healthy": pipeline_healthy,
                "contacts": contacts_data,
                "pipeline": pipeline_data,
                "proposals": proposals_data,
                "campaigns": campaigns_data,
                "epic7_integrity": epic7_integrity,
                "status": "HEALTHY" if pipeline_healthy else "AT_RISK"
            }

        except Exception as e:
            return {
                "database_exists": True,
                "database_accessible": False,
                "error": str(e),
                "status": "CRITICAL_FAILURE"
            }

    def _validate_contacts_table(self, cursor) -> dict[str, Any]:
        """Validate contacts table data."""
        try:
            # Check if contacts table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contacts'")
            if not cursor.fetchone():
                return {"exists": False, "count": 0}

            # Get contact count
            cursor.execute("SELECT COUNT(*) FROM contacts")
            total_count = cursor.fetchone()[0]

            # Get qualified contacts (Epic 7 specific)
            cursor.execute("""
                SELECT COUNT(*) FROM contacts
                WHERE status IN ('qualified', 'consultation_requested', 'proposal_sent')
            """)
            qualified_count = cursor.fetchone()[0] if cursor.fetchone() else 0

            # Get recent contacts (last 30 days)
            cursor.execute("""
                SELECT COUNT(*) FROM contacts
                WHERE created_date >= datetime('now', '-30 days')
            """)
            recent_count = cursor.fetchone()[0] if cursor.fetchone() else 0

            return {
                "exists": True,
                "count": total_count,
                "qualified_count": qualified_count,
                "recent_count": recent_count,
                "meets_requirement": total_count >= self.pipeline_requirements["minimum_contacts"]
            }

        except Exception as e:
            return {"exists": False, "count": 0, "error": str(e)}

    def _validate_pipeline_table(self, cursor) -> dict[str, Any]:
        """Validate pipeline/opportunities table data."""
        try:
            # Check for opportunities table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='opportunities'")
            if not cursor.fetchone():
                return {"exists": False, "total_value": 0}

            # Get total pipeline value
            cursor.execute("""
                SELECT SUM(value) FROM opportunities
                WHERE status IN ('active', 'qualified', 'proposal', 'negotiation')
            """)
            result = cursor.fetchone()
            total_value = result[0] if result and result[0] else 0

            # Get opportunity count by stage
            cursor.execute("""
                SELECT status, COUNT(*), SUM(value)
                FROM opportunities
                GROUP BY status
            """)
            stages = {}
            for row in cursor.fetchall():
                stages[row[0]] = {"count": row[1], "value": row[2] if row[2] else 0}

            # Get high-value opportunities (>$50k)
            cursor.execute("""
                SELECT COUNT(*) FROM opportunities
                WHERE value >= 50000 AND status IN ('active', 'qualified', 'proposal')
            """)
            high_value_count = cursor.fetchone()[0] if cursor.fetchone() else 0

            return {
                "exists": True,
                "total_value": total_value,
                "stages": stages,
                "high_value_count": high_value_count,
                "meets_requirement": total_value >= self.pipeline_requirements["minimum_pipeline_value"]
            }

        except Exception as e:
            return {"exists": False, "total_value": 0, "error": str(e)}

    def _validate_proposals_table(self, cursor) -> dict[str, Any]:
        """Validate proposals table data."""
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='proposals'")
            if not cursor.fetchone():
                return {"exists": False, "count": 0}

            cursor.execute("SELECT COUNT(*) FROM proposals")
            total_count = cursor.fetchone()[0]

            # Get active proposals
            cursor.execute("""
                SELECT COUNT(*) FROM proposals
                WHERE status IN ('sent', 'under_review', 'negotiation')
            """)
            active_count = cursor.fetchone()[0] if cursor.fetchone() else 0

            # Get proposal values
            cursor.execute("SELECT SUM(value) FROM proposals WHERE status != 'rejected'")
            result = cursor.fetchone()
            total_proposal_value = result[0] if result and result[0] else 0

            return {
                "exists": True,
                "count": total_count,
                "active_count": active_count,
                "total_value": total_proposal_value,
                "meets_requirement": total_count >= self.pipeline_requirements["minimum_proposals"]
            }

        except Exception as e:
            return {"exists": False, "count": 0, "error": str(e)}

    def _validate_campaigns_table(self, cursor) -> dict[str, Any]:
        """Validate campaigns table data."""
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='campaigns'")
            if not cursor.fetchone():
                return {"exists": False, "count": 0}

            cursor.execute("SELECT COUNT(*) FROM campaigns")
            total_count = cursor.fetchone()[0]

            # Get active campaigns
            cursor.execute("""
                SELECT COUNT(*) FROM campaigns
                WHERE status = 'active' AND end_date >= date('now')
            """)
            active_count = cursor.fetchone()[0] if cursor.fetchone() else 0

            return {
                "exists": True,
                "count": total_count,
                "active_count": active_count,
                "meets_requirement": total_count >= self.pipeline_requirements["minimum_campaigns"]
            }

        except Exception as e:
            return {"exists": False, "count": 0, "error": str(e)}

    def _validate_epic7_data_integrity(self, cursor) -> dict[str, Any]:
        """Validate Epic 7 specific data integrity markers."""
        try:
            integrity_checks = {}

            # Check for Epic 7 metadata markers
            cursor.execute("""
                SELECT COUNT(*) FROM contacts
                WHERE source LIKE '%epic7%' OR tags LIKE '%epic7%'
            """)
            result = cursor.fetchone()
            integrity_checks["epic7_tagged_contacts"] = result[0] if result else 0

            # Check for LinkedIn integration data
            cursor.execute("""
                SELECT COUNT(*) FROM contacts
                WHERE linkedin_profile IS NOT NULL AND linkedin_profile != ''
            """)
            result = cursor.fetchone()
            integrity_checks["linkedin_contacts"] = result[0] if result else 0

            # Check for consultation inquiry tracking
            cursor.execute("""
                SELECT COUNT(*) FROM opportunities
                WHERE opportunity_type = 'consultation' OR description LIKE '%consultation%'
            """)
            result = cursor.fetchone()
            integrity_checks["consultation_opportunities"] = result[0] if result else 0

            return {
                "checks_passed": len([v for v in integrity_checks.values() if v > 0]),
                "total_checks": len(integrity_checks),
                "details": integrity_checks,
                "integrity_score": len([v for v in integrity_checks.values() if v > 0]) / len(integrity_checks) * 100
            }

        except Exception as e:
            return {"error": str(e), "integrity_score": 0}

    def validate_epic7_api_endpoints(self) -> dict[str, Any]:
        """Validate Epic 7 sales automation API endpoints are functional."""
        endpoint_results = {}

        for endpoint in self.epic7_endpoints:
            try:
                response = requests.get(f"{self.api_base_url}{endpoint}", timeout=10)
                endpoint_results[endpoint] = {
                    "accessible": True,
                    "status_code": response.status_code,
                    "functional": response.status_code in [200, 401, 422],  # Auth errors acceptable
                    "response_size": len(response.content)
                }
            except Exception as e:
                endpoint_results[endpoint] = {
                    "accessible": False,
                    "error": str(e),
                    "functional": False
                }

        functional_endpoints = sum(1 for result in endpoint_results.values() if result.get("functional", False))
        total_endpoints = len(self.epic7_endpoints)

        return {
            "endpoints_tested": total_endpoints,
            "functional_endpoints": functional_endpoints,
            "functionality_rate": functional_endpoints / total_endpoints * 100,
            "endpoint_details": endpoint_results,
            "status": "FUNCTIONAL" if functional_endpoints >= total_endpoints * 0.8 else "DEGRADED"
        }

    def validate_epic7_router_exists(self) -> dict[str, Any]:
        """Validate Epic 7 sales automation router exists and is properly configured."""
        epic7_router_path = self.project_root / "graph_rag" / "api" / "routers" / "epic7_sales_automation.py"

        if not epic7_router_path.exists():
            return {
                "router_exists": False,
                "status": "CRITICAL_FAILURE",
                "error": "Epic 7 sales automation router missing"
            }

        try:
            # Read router file and validate structure
            with open(epic7_router_path) as f:
                router_content = f.read()

            # Check for key Epic 7 functionality
            required_functions = [
                "get_pipeline",
                "get_contacts",
                "create_proposal",
                "calculate_roi",
                "detect_consultation_inquiry"
            ]

            function_checks = {}
            for func in required_functions:
                function_checks[func] = func in router_content

            functions_present = sum(function_checks.values())

            return {
                "router_exists": True,
                "functions_implemented": functions_present,
                "total_functions_expected": len(required_functions),
                "function_checks": function_checks,
                "implementation_complete": functions_present >= len(required_functions) * 0.8,
                "status": "FUNCTIONAL" if functions_present >= len(required_functions) * 0.8 else "INCOMPLETE"
            }

        except Exception as e:
            return {
                "router_exists": True,
                "readable": False,
                "error": str(e),
                "status": "ERROR"
            }

    def calculate_pipeline_value_at_risk(self) -> dict[str, Any]:
        """Calculate the actual pipeline value at risk during consolidation."""
        crm_validation = self.validate_crm_database_integrity()

        if not crm_validation.get("database_exists", False):
            return {
                "total_at_risk": self.pipeline_requirements["minimum_pipeline_value"],
                "risk_level": "CRITICAL",
                "reason": "CRM database completely missing"
            }

        if not crm_validation.get("pipeline_healthy", False):
            pipeline_data = crm_validation.get("pipeline", {})
            current_value = pipeline_data.get("total_value", 0)
            value_shortfall = max(0, self.pipeline_requirements["minimum_pipeline_value"] - current_value)

            return {
                "current_pipeline_value": current_value,
                "target_pipeline_value": self.pipeline_requirements["minimum_pipeline_value"],
                "value_at_risk": value_shortfall,
                "risk_level": "HIGH" if value_shortfall > 500000 else "MEDIUM",
                "risk_percentage": (value_shortfall / self.pipeline_requirements["minimum_pipeline_value"]) * 100
            }

        return {
            "current_pipeline_value": crm_validation["pipeline"]["total_value"],
            "target_pipeline_value": self.pipeline_requirements["minimum_pipeline_value"],
            "value_at_risk": 0,
            "risk_level": "LOW",
            "status": "PROTECTED"
        }

    def generate_pipeline_protection_report(self) -> dict[str, Any]:
        """Generate comprehensive Epic 7 pipeline protection report."""
        crm_validation = self.validate_crm_database_integrity()
        api_validation = self.validate_epic7_api_endpoints()
        router_validation = self.validate_epic7_router_exists()
        value_at_risk = self.calculate_pipeline_value_at_risk()

        # Calculate overall protection status
        protection_factors = [
            crm_validation.get("status") in ["HEALTHY"],
            api_validation.get("status") in ["FUNCTIONAL"],
            router_validation.get("status") in ["FUNCTIONAL"],
            value_at_risk.get("risk_level") in ["LOW"]
        ]

        protection_score = sum(protection_factors) / len(protection_factors) * 100

        overall_status = (
            "FULLY_PROTECTED" if protection_score >= 90 else
            "PARTIALLY_PROTECTED" if protection_score >= 70 else
            "AT_RISK" if protection_score >= 50 else
            "CRITICAL_RISK"
        )

        return {
            "pipeline_protection_status": overall_status,
            "protection_score": protection_score,
            "crm_database": crm_validation,
            "api_endpoints": api_validation,
            "router_status": router_validation,
            "value_at_risk_analysis": value_at_risk,
            "recommendations": self._generate_protection_recommendations(
                crm_validation, api_validation, router_validation, value_at_risk
            ),
            "timestamp": datetime.now().isoformat()
        }

    def _generate_protection_recommendations(self, crm_val, api_val, router_val, risk_val) -> list[str]:
        """Generate recommendations for pipeline protection."""
        recommendations = []

        if crm_val.get("status") != "HEALTHY":
            recommendations.append(
                "URGENT: Restore CRM database integrity. Epic 7 pipeline data may be compromised."
            )

        if api_val.get("functionality_rate", 0) < 80:
            recommendations.append(
                "Restore Epic 7 API endpoints. Sales automation functionality is degraded."
            )

        if router_val.get("status") != "FUNCTIONAL":
            recommendations.append(
                "Epic 7 sales automation router needs attention. Core functionality missing."
            )

        if risk_val.get("risk_level") != "LOW":
            value_at_risk = risk_val.get("value_at_risk", 0)
            recommendations.append(
                f"Pipeline value at risk: ${value_at_risk:,.2f}. "
                f"Implement data recovery procedures immediately."
            )

        if not recommendations:
            recommendations.append("Epic 7 pipeline is fully protected. Continue monitoring during consolidation.")

        return recommendations


@pytest.fixture
def pipeline_validator():
    """Provide Epic 7 pipeline validator."""
    return Epic7PipelineValidator()


class TestEpic7PipelineProtection:
    """Epic 7 pipeline protection validation tests."""

    def test_crm_database_integrity(self, pipeline_validator):
        """Test CRM database contains Epic 7 pipeline data."""
        validation = pipeline_validator.validate_crm_database_integrity()

        assert validation["database_exists"], "CRM database missing - Epic 7 pipeline at risk"
        assert validation["status"] != "CRITICAL_FAILURE", (
            f"CRM database critical failure: {validation.get('error', 'Unknown error')}"
        )

        # Validate minimum contact requirements
        contacts = validation.get("contacts", {})
        assert contacts.get("count", 0) >= pipeline_validator.pipeline_requirements["minimum_contacts"], (
            f"Insufficient contacts: {contacts.get('count', 0)} found, "
            f"minimum {pipeline_validator.pipeline_requirements['minimum_contacts']} required"
        )

    def test_pipeline_value_protection(self, pipeline_validator):
        """Test pipeline value meets Epic 7 requirements."""
        validation = pipeline_validator.validate_crm_database_integrity()

        assert validation["database_exists"], "CRM database missing - pipeline value at risk"

        pipeline = validation.get("pipeline", {})
        pipeline_value = pipeline.get("total_value", 0)
        minimum_value = pipeline_validator.pipeline_requirements["minimum_pipeline_value"]

        assert pipeline_value >= minimum_value, (
            f"Pipeline value below Epic 7 requirement: ${pipeline_value:,.2f} found, "
            f"minimum ${minimum_value:,.2f} required"
        )

    def test_epic7_api_endpoints_functional(self, pipeline_validator):
        """Test Epic 7 sales automation API endpoints are functional."""
        validation = pipeline_validator.validate_epic7_api_endpoints()

        functionality_rate = validation.get("functionality_rate", 0)
        assert functionality_rate >= 80, (
            f"Epic 7 API functionality degraded: {functionality_rate:.1f}% functional, "
            f"minimum 80% required"
        )

        assert validation["status"] == "FUNCTIONAL", (
            f"Epic 7 API endpoints not functional: {validation.get('status')}"
        )

    def test_epic7_router_exists(self, pipeline_validator):
        """Test Epic 7 sales automation router exists and is functional."""
        validation = pipeline_validator.validate_epic7_router_exists()

        assert validation["router_exists"], "Epic 7 sales automation router missing"
        assert validation["status"] == "FUNCTIONAL", (
            f"Epic 7 router not functional: {validation.get('status')}. "
            f"Functions implemented: {validation.get('functions_implemented', 0)}/"
            f"{validation.get('total_functions_expected', 0)}"
        )

    def test_pipeline_value_at_risk_analysis(self, pipeline_validator):
        """Test pipeline value at risk analysis."""
        risk_analysis = pipeline_validator.calculate_pipeline_value_at_risk()

        risk_level = risk_analysis.get("risk_level", "UNKNOWN")
        value_at_risk = risk_analysis.get("value_at_risk", 0)

        # Critical failure if high value at risk
        assert risk_level != "CRITICAL", (
            f"Critical pipeline risk detected. Value at risk: ${value_at_risk:,.2f}"
        )

        # Warning for medium/high risk
        if risk_level in ["HIGH", "MEDIUM"]:
            pytest.warn(UserWarning(
                f"Pipeline value at risk: ${value_at_risk:,.2f} ({risk_level} risk level)"
            ))

    def test_overall_pipeline_protection(self, pipeline_validator):
        """Test overall Epic 7 pipeline protection status."""
        report = pipeline_validator.generate_pipeline_protection_report()

        protection_status = report["pipeline_protection_status"]
        protection_score = report["protection_score"]

        print("\nEpic 7 Pipeline Protection Report:")
        print(f"Status: {protection_status}")
        print(f"Protection Score: {protection_score:.1f}%")

        if report["recommendations"]:
            print("Recommendations:")
            for i, rec in enumerate(report["recommendations"], 1):
                print(f"  {i}. {rec}")

        assert protection_status != "CRITICAL_RISK", (
            f"Epic 7 pipeline at critical risk. Protection score: {protection_score:.1f}%"
        )

        # For Epic 10 completion, pipeline must be at least partially protected
        assert protection_score >= 70, (
            f"Insufficient pipeline protection: {protection_score:.1f}%, minimum 70% required"
        )


if __name__ == "__main__":
    """Run Epic 7 pipeline protection validation."""
    validator = Epic7PipelineValidator()
    report = validator.generate_pipeline_protection_report()

    print(json.dumps(report, indent=2, default=str))
