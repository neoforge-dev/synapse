"""SOC 2 Type II compliance controls and monitoring system."""

import logging
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class SOC2TrustPrinciple(str, Enum):
    """SOC 2 Trust Service Criteria principles."""
    SECURITY = "security"
    AVAILABILITY = "availability"
    PROCESSING_INTEGRITY = "processing_integrity"
    CONFIDENTIALITY = "confidentiality"
    PRIVACY = "privacy"


class ControlStatus(str, Enum):
    """Control implementation and testing status."""
    DESIGNED = "designed"
    IMPLEMENTED = "implemented"
    OPERATING_EFFECTIVELY = "operating_effectively"
    DEFICIENT = "deficient"
    NOT_APPLICABLE = "not_applicable"


class SOC2Control:
    """Individual SOC 2 control definition and monitoring."""

    def __init__(
        self,
        control_id: str,
        principle: SOC2TrustPrinciple,
        title: str,
        description: str,
        control_activities: list[str],
        testing_procedures: list[str]
    ):
        self.id = control_id
        self.principle = principle
        self.title = title
        self.description = description
        self.control_activities = control_activities
        self.testing_procedures = testing_procedures
        self.status = ControlStatus.DESIGNED
        self.last_tested: datetime | None = None
        self.test_results: list[dict[str, Any]] = []
        self.exceptions: list[dict[str, Any]] = []
        self.evidence: list[dict[str, Any]] = []


class SOC2ComplianceFramework:
    """SOC 2 Type II compliance framework and control monitoring."""

    def __init__(self):
        self.controls: dict[str, SOC2Control] = {}
        self.control_tests: list[dict[str, Any]] = []
        self.compliance_period_start = datetime(2024, 1, 1)
        self.compliance_period_end = datetime(2024, 12, 31)
        self._initialize_controls()

    def _initialize_controls(self):
        """Initialize SOC 2 controls framework."""

        # Security Controls (CC)
        self._add_security_controls()

        # Availability Controls (A)
        self._add_availability_controls()

        # Processing Integrity Controls (PI)
        self._add_processing_integrity_controls()

        # Confidentiality Controls (C)
        self._add_confidentiality_controls()

        # Privacy Controls (P)
        self._add_privacy_controls()

    def _add_security_controls(self):
        """Add security principle controls."""

        # CC1.0 - Control Environment
        self.controls["CC1.0"] = SOC2Control(
            "CC1.0",
            SOC2TrustPrinciple.SECURITY,
            "Control Environment",
            "The entity demonstrates a commitment to integrity and ethical values",
            [
                "Code of conduct established and communicated",
                "Management philosophy and operating style promotes security",
                "Organizational structure supports security objectives",
                "Authority and responsibility for security assigned",
                "Human resource policies support security objectives"
            ],
            [
                "Review code of conduct documentation",
                "Interview management about security philosophy",
                "Review organizational charts and job descriptions",
                "Test security training completion",
                "Review background check procedures"
            ]
        )

        # CC2.0 - Communication and Information
        self.controls["CC2.0"] = SOC2Control(
            "CC2.0",
            SOC2TrustPrinciple.SECURITY,
            "Communication and Information Systems",
            "The entity obtains or generates and uses relevant, quality information",
            [
                "Security policies documented and communicated",
                "Information systems support security objectives",
                "Security incidents reported and escalated",
                "Security metrics collected and analyzed",
                "External communications about security managed"
            ],
            [
                "Review security policy documentation",
                "Test incident reporting procedures",
                "Review security metrics and dashboards",
                "Test external communication procedures",
                "Review information systems documentation"
            ]
        )

        # CC3.0 - Risk Assessment
        self.controls["CC3.0"] = SOC2Control(
            "CC3.0",
            SOC2TrustPrinciple.SECURITY,
            "Risk Assessment",
            "The entity identifies risks and analyzes them as basis for determining risk management",
            [
                "Risk identification processes implemented",
                "Risk assessment methodology documented",
                "Risk tolerance levels defined",
                "Risk mitigation strategies implemented",
                "Risk assessments performed regularly"
            ],
            [
                "Review risk assessment documentation",
                "Test risk identification procedures",
                "Review risk register and mitigation plans",
                "Test risk assessment frequency",
                "Interview risk management personnel"
            ]
        )

        # CC4.0 - Monitoring Activities
        self.controls["CC4.0"] = SOC2Control(
            "CC4.0",
            SOC2TrustPrinciple.SECURITY,
            "Monitoring Activities",
            "The entity selects, develops, and performs ongoing and separate evaluations",
            [
                "Security monitoring tools implemented",
                "Log analysis procedures established",
                "Security metrics monitored continuously",
                "Control deficiencies identified and remediated",
                "Independent security assessments performed"
            ],
            [
                "Review security monitoring system logs",
                "Test log analysis procedures",
                "Review security dashboards and metrics",
                "Test deficiency remediation process",
                "Review independent assessment reports"
            ]
        )

        # CC5.0 - Control Activities
        self.controls["CC5.0"] = SOC2Control(
            "CC5.0",
            SOC2TrustPrinciple.SECURITY,
            "Control Activities - Access Controls",
            "The entity implements control activities through policies and procedures",
            [
                "Logical access controls implemented",
                "Multi-factor authentication enforced",
                "User access provisioning and deprovisioning",
                "Privileged access management",
                "Access reviews performed regularly"
            ],
            [
                "Test user access provisioning process",
                "Review MFA implementation",
                "Test access review procedures",
                "Review privileged access controls",
                "Test user deprovisioning process"
            ]
        )

        # CC6.0 - Logical and Physical Access
        self.controls["CC6.0"] = SOC2Control(
            "CC6.0",
            SOC2TrustPrinciple.SECURITY,
            "Logical and Physical Access Controls",
            "The entity restricts logical and physical access to authorized personnel",
            [
                "Network access controls implemented",
                "Application access controls enforced",
                "Database access controls configured",
                "Physical security controls implemented",
                "Environmental protection controls operational"
            ],
            [
                "Test network segmentation controls",
                "Review application authentication",
                "Test database access controls",
                "Review physical security measures",
                "Test environmental monitoring systems"
            ]
        )

        # CC7.0 - System Operations
        self.controls["CC7.0"] = SOC2Control(
            "CC7.0",
            SOC2TrustPrinciple.SECURITY,
            "System Operations",
            "The entity uses detection and monitoring procedures to identify security events",
            [
                "System capacity monitoring implemented",
                "System performance monitoring active",
                "Security event detection configured",
                "Incident response procedures established",
                "System backup and recovery procedures"
            ],
            [
                "Test capacity monitoring alerts",
                "Review performance monitoring data",
                "Test security event detection",
                "Review incident response procedures",
                "Test backup and recovery processes"
            ]
        )

        # CC8.0 - Change Management
        self.controls["CC8.0"] = SOC2Control(
            "CC8.0",
            SOC2TrustPrinciple.SECURITY,
            "Change Management",
            "The entity authorizes, designs, develops and configures changes",
            [
                "Change management process documented",
                "Change approval procedures implemented",
                "Testing procedures for changes established",
                "Change deployment procedures controlled",
                "Emergency change procedures defined"
            ],
            [
                "Review change management documentation",
                "Test change approval process",
                "Review testing procedures",
                "Test change deployment controls",
                "Review emergency change procedures"
            ]
        )

    def _add_availability_controls(self):
        """Add availability principle controls."""

        # A1.0 - Availability
        self.controls["A1.0"] = SOC2Control(
            "A1.0",
            SOC2TrustPrinciple.AVAILABILITY,
            "System Availability",
            "The entity maintains system availability as committed or agreed",
            [
                "Service level agreements defined",
                "System availability monitoring implemented",
                "High availability architecture deployed",
                "Disaster recovery procedures established",
                "Capacity planning processes implemented"
            ],
            [
                "Review SLA documentation",
                "Test availability monitoring systems",
                "Review high availability configuration",
                "Test disaster recovery procedures",
                "Review capacity planning documentation"
            ]
        )

    def _add_processing_integrity_controls(self):
        """Add processing integrity principle controls."""

        # PI1.0 - Processing Integrity
        self.controls["PI1.0"] = SOC2Control(
            "PI1.0",
            SOC2TrustPrinciple.PROCESSING_INTEGRITY,
            "Data Processing Integrity",
            "The entity processes data with integrity as committed or agreed",
            [
                "Data validation controls implemented",
                "Error detection and correction procedures",
                "Data transmission integrity controls",
                "Processing completeness controls",
                "Data integrity monitoring systems"
            ],
            [
                "Test data validation procedures",
                "Review error handling processes",
                "Test data transmission controls",
                "Review processing completeness checks",
                "Test data integrity monitoring"
            ]
        )

    def _add_confidentiality_controls(self):
        """Add confidentiality principle controls."""

        # C1.0 - Confidentiality
        self.controls["C1.0"] = SOC2Control(
            "C1.0",
            SOC2TrustPrinciple.CONFIDENTIALITY,
            "Data Confidentiality",
            "The entity protects confidential information as committed or agreed",
            [
                "Data classification procedures implemented",
                "Encryption at rest and in transit",
                "Access controls for confidential data",
                "Data loss prevention controls",
                "Confidentiality agreements in place"
            ],
            [
                "Review data classification procedures",
                "Test encryption implementation",
                "Test confidential data access controls",
                "Review DLP system configuration",
                "Review confidentiality agreements"
            ]
        )

    def _add_privacy_controls(self):
        """Add privacy principle controls."""

        # P1.0 - Privacy Notice
        self.controls["P1.0"] = SOC2Control(
            "P1.0",
            SOC2TrustPrinciple.PRIVACY,
            "Privacy Notice and Consent",
            "The entity provides notice about its privacy practices",
            [
                "Privacy notice published and accessible",
                "Consent mechanisms implemented",
                "Privacy choices provided to users",
                "Privacy notice updates communicated",
                "Data collection purposes disclosed"
            ],
            [
                "Review privacy notice content",
                "Test consent mechanisms",
                "Review privacy choice options",
                "Test privacy notice update process",
                "Review data collection disclosures"
            ]
        )

        # P2.0 - Collection and Retention
        self.controls["P2.0"] = SOC2Control(
            "P2.0",
            SOC2TrustPrinciple.PRIVACY,
            "Personal Information Collection",
            "The entity collects personal information only for purposes identified in notice",
            [
                "Data collection procedures documented",
                "Purpose limitation controls implemented",
                "Data minimization practices enforced",
                "Retention schedules defined and followed",
                "Data disposal procedures implemented"
            ],
            [
                "Review data collection procedures",
                "Test purpose limitation controls",
                "Review data minimization practices",
                "Test retention schedule compliance",
                "Test data disposal procedures"
            ]
        )

    def perform_control_test(
        self,
        control_id: str,
        tester: str,
        test_description: str,
        test_results: dict[str, Any]
    ) -> UUID:
        """Perform and record a control test."""

        if control_id not in self.controls:
            raise ValueError(f"Control {control_id} not found")

        test_id = uuid4()
        control = self.controls[control_id]

        test_record = {
            "test_id": test_id,
            "control_id": control_id,
            "tester": tester,
            "test_date": datetime.utcnow(),
            "test_description": test_description,
            "test_results": test_results,
            "conclusion": test_results.get("conclusion", "inconclusive"),
            "exceptions": test_results.get("exceptions", []),
            "evidence_collected": test_results.get("evidence", [])
        }

        # Update control status based on test results
        if test_results.get("conclusion") == "satisfactory":
            control.status = ControlStatus.OPERATING_EFFECTIVELY
        elif test_results.get("conclusion") == "unsatisfactory":
            control.status = ControlStatus.DEFICIENT

        control.last_tested = datetime.utcnow()
        control.test_results.append(test_record)

        if test_results.get("exceptions"):
            control.exceptions.extend(test_results["exceptions"])

        self.control_tests.append(test_record)

        logger.info(f"Control test performed for {control_id}: {test_results.get('conclusion')}")
        return test_id

    def add_control_evidence(
        self,
        control_id: str,
        evidence_type: str,
        description: str,
        file_path: str = None,
        metadata: dict[str, Any] = None
    ):
        """Add evidence supporting a control."""

        if control_id not in self.controls:
            raise ValueError(f"Control {control_id} not found")

        evidence = {
            "evidence_id": str(uuid4()),
            "control_id": control_id,
            "evidence_type": evidence_type,
            "description": description,
            "file_path": file_path,
            "collected_date": datetime.utcnow(),
            "metadata": metadata or {}
        }

        self.controls[control_id].evidence.append(evidence)
        logger.info(f"Evidence added for control {control_id}: {evidence_type}")

    def generate_control_testing_report(self) -> dict[str, Any]:
        """Generate comprehensive control testing report for SOC 2."""

        total_controls = len(self.controls)
        tested_controls = sum(1 for c in self.controls.values() if c.last_tested)
        effective_controls = sum(
            1 for c in self.controls.values()
            if c.status == ControlStatus.OPERATING_EFFECTIVELY
        )
        deficient_controls = sum(
            1 for c in self.controls.values()
            if c.status == ControlStatus.DEFICIENT
        )

        # Group controls by principle
        controls_by_principle = {}
        for control in self.controls.values():
            principle = control.principle.value
            if principle not in controls_by_principle:
                controls_by_principle[principle] = []
            controls_by_principle[principle].append({
                "control_id": control.id,
                "title": control.title,
                "status": control.status.value,
                "last_tested": control.last_tested.isoformat() if control.last_tested else None,
                "exceptions_count": len(control.exceptions),
                "evidence_count": len(control.evidence)
            })

        return {
            "report_date": datetime.utcnow().isoformat(),
            "compliance_period": {
                "start_date": self.compliance_period_start.isoformat(),
                "end_date": self.compliance_period_end.isoformat()
            },
            "summary": {
                "total_controls": total_controls,
                "tested_controls": tested_controls,
                "effective_controls": effective_controls,
                "deficient_controls": deficient_controls,
                "testing_coverage": (tested_controls / total_controls) * 100,
                "effectiveness_rate": (effective_controls / tested_controls) * 100 if tested_controls > 0 else 0
            },
            "controls_by_principle": controls_by_principle,
            "exceptions": self._get_all_exceptions(),
            "testing_statistics": {
                "total_tests_performed": len(self.control_tests),
                "tests_by_month": self._get_tests_by_month(),
                "avg_tests_per_control": len(self.control_tests) / total_controls
            },
            "remediation_status": self._get_remediation_status()
        }

    def _get_all_exceptions(self) -> list[dict[str, Any]]:
        """Get all control exceptions for reporting."""

        exceptions = []
        for control in self.controls.values():
            for exception in control.exceptions:
                exceptions.append({
                    "control_id": control.id,
                    "control_title": control.title,
                    "exception": exception,
                    "status": exception.get("status", "open")
                })

        return exceptions

    def _get_tests_by_month(self) -> dict[str, int]:
        """Get number of tests performed by month."""

        tests_by_month = {}
        for test in self.control_tests:
            month_key = test["test_date"].strftime("%Y-%m")
            tests_by_month[month_key] = tests_by_month.get(month_key, 0) + 1

        return tests_by_month

    def _get_remediation_status(self) -> dict[str, Any]:
        """Get remediation status for deficient controls."""

        deficient_controls = [
            c for c in self.controls.values()
            if c.status == ControlStatus.DEFICIENT
        ]

        return {
            "deficient_controls_count": len(deficient_controls),
            "deficient_controls": [
                {
                    "control_id": c.id,
                    "title": c.title,
                    "principle": c.principle.value,
                    "exceptions_count": len(c.exceptions),
                    "last_tested": c.last_tested.isoformat() if c.last_tested else None
                }
                for c in deficient_controls
            ]
        }

    def generate_management_assertion(self) -> dict[str, Any]:
        """Generate management assertion for SOC 2 report."""

        effective_controls = sum(
            1 for c in self.controls.values()
            if c.status == ControlStatus.OPERATING_EFFECTIVELY
        )
        total_applicable_controls = sum(
            1 for c in self.controls.values()
            if c.status != ControlStatus.NOT_APPLICABLE
        )

        control_effectiveness = (effective_controls / total_applicable_controls) * 100

        return {
            "assertion_date": datetime.utcnow().isoformat(),
            "management_assertion": {
                "security": "Management maintains effective controls over security",
                "availability": "Management maintains effective controls over availability",
                "processing_integrity": "Management maintains effective controls over processing integrity",
                "confidentiality": "Management maintains effective controls over confidentiality",
                "privacy": "Management maintains effective controls over privacy"
            },
            "control_effectiveness_percentage": control_effectiveness,
            "assertion_basis": {
                "design_effectiveness": "Controls are suitably designed",
                "operating_effectiveness": f"Controls operated effectively during the period from {self.compliance_period_start.date()} to {self.compliance_period_end.date()}",
                "testing_coverage": "All applicable controls were tested",
                "exception_management": "All exceptions were properly managed and remediated"
            },
            "limitations": [
                "Controls are designed to provide reasonable assurance",
                "Inherent limitations exist in any system of internal controls",
                "Controls may become inadequate due to changes in conditions",
                "Degree of compliance may vary"
            ]
        }


# Global SOC 2 compliance framework instance
soc2_framework = SOC2ComplianceFramework()
