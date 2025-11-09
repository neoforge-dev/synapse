"""HIPAA compliance framework for healthcare data protection."""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class HIPAASafeguardType(str, Enum):
    """HIPAA safeguard categories."""
    ADMINISTRATIVE = "administrative"
    PHYSICAL = "physical"
    TECHNICAL = "technical"


class PHIType(str, Enum):
    """Protected Health Information types."""
    IDENTIFIABLE_PHI = "identifiable_phi"
    LIMITED_DATA_SET = "limited_data_set"
    DE_IDENTIFIED = "de_identified"
    SAFE_HARBOR = "safe_harbor"


class HIPAAComplianceStatus(str, Enum):
    """HIPAA compliance status levels."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    REQUIRES_ATTENTION = "requires_attention"
    NOT_APPLICABLE = "not_applicable"


class HIPAASafeguard:
    """Individual HIPAA safeguard implementation."""

    def __init__(
        self,
        safeguard_id: str,
        safeguard_type: HIPAASafeguardType,
        title: str,
        description: str,
        required: bool,
        addressable: bool = False
    ):
        self.id = safeguard_id
        self.safeguard_type = safeguard_type
        self.title = title
        self.description = description
        self.required = required
        self.addressable = addressable
        self.status = HIPAAComplianceStatus.NOT_APPLICABLE
        self.implementation_date: datetime | None = None
        self.last_reviewed: datetime | None = None
        self.policies: list[str] = []
        self.procedures: list[str] = []
        self.evidence: list[dict[str, Any]] = []
        self.risk_assessment: dict[str, Any] | None = None


class PHIHandler:
    """Protected Health Information handling and monitoring."""

    def __init__(self):
        self.phi_inventory: list[dict[str, Any]] = []
        self.access_logs: list[dict[str, Any]] = []
        self.phi_breaches: list[dict[str, Any]] = []

        # HIPAA identifiers that must be removed for de-identification
        self.phi_identifiers = {
            "names": ["first_name", "last_name", "full_name"],
            "geographic": ["address", "city", "county", "precinct", "zip_code"],
            "dates": ["birth_date", "admission_date", "discharge_date", "death_date"],
            "communication": ["phone", "fax", "email", "url", "ip_address"],
            "identifiers": [
                "ssn", "mrn", "account_number", "certificate_number",
                "vehicle_id", "device_id", "biometric_id", "photo"
            ],
            "other": ["age_over_89", "relative_identifiers"]
        }

    def classify_phi(self, data: dict[str, Any]) -> PHIType:
        """Classify data based on PHI content."""

        # Check for direct identifiers
        for _category, identifiers in self.phi_identifiers.items():
            for identifier in identifiers:
                if identifier in data or any(
                    identifier in str(key).lower() for key in data.keys()
                ):
                    return PHIType.IDENTIFIABLE_PHI

        # Check for dates (limited data set allows certain dates)
        has_dates = any("date" in str(key).lower() for key in data.keys())
        if has_dates and not self._has_direct_identifiers(data):
            return PHIType.LIMITED_DATA_SET

        # If no identifiers found, consider de-identified
        return PHIType.DE_IDENTIFIED

    def _has_direct_identifiers(self, data: dict[str, Any]) -> bool:
        """Check if data contains direct identifiers."""
        direct_identifiers = [
            "name", "address", "phone", "email", "ssn", "mrn"
        ]
        return any(
            identifier in str(key).lower()
            for identifier in direct_identifiers
            for key in data.keys()
        )

    def log_phi_access(
        self,
        user_id: UUID,
        phi_record_id: str,
        action: str,
        purpose: str,
        ip_address: str = None
    ):
        """Log PHI access for audit trail."""

        access_log = {
            "log_id": str(uuid4()),
            "timestamp": datetime.utcnow(),
            "user_id": str(user_id),
            "phi_record_id": phi_record_id,
            "action": action,
            "purpose": purpose,
            "ip_address": ip_address,
            "authorized": True  # Should be validated
        }

        self.access_logs.append(access_log)
        logger.info(f"PHI access logged: {action} by user {user_id}")

    def detect_phi_breach(
        self,
        incident_description: str,
        affected_individuals: int,
        phi_types: list[str],
        discovery_date: datetime = None
    ) -> str:
        """Report and track PHI breach incident."""

        breach_id = str(uuid4())
        discovery_date = discovery_date or datetime.utcnow()

        # Determine if breach requires notification (>500 individuals)
        requires_hhs_notification = affected_individuals > 500

        breach_record = {
            "breach_id": breach_id,
            "discovery_date": discovery_date,
            "incident_description": incident_description,
            "affected_individuals": affected_individuals,
            "phi_types": phi_types,
            "requires_hhs_notification": requires_hhs_notification,
            "notification_deadline": discovery_date + timedelta(days=60),
            "status": "reported",
            "mitigation_actions": [],
            "lessons_learned": []
        }

        self.phi_breaches.append(breach_record)

        # Log critical security event
        logger.critical(f"PHI breach detected: {breach_id}, {affected_individuals} individuals affected")

        return breach_id


class HIPAAComplianceFramework:
    """HIPAA compliance framework and safeguard management."""

    def __init__(self):
        self.safeguards: dict[str, HIPAASafeguard] = {}
        self.phi_handler = PHIHandler()
        self.business_associates: list[dict[str, Any]] = []
        self.risk_assessments: list[dict[str, Any]] = []
        self._initialize_safeguards()

    def _initialize_safeguards(self):
        """Initialize HIPAA safeguards based on Security Rule requirements."""

        # Administrative Safeguards (§164.308)
        self._add_administrative_safeguards()

        # Physical Safeguards (§164.310)
        self._add_physical_safeguards()

        # Technical Safeguards (§164.312)
        self._add_technical_safeguards()

    def _add_administrative_safeguards(self):
        """Add administrative safeguards (§164.308)."""

        # §164.308(a)(1) - Security Officer
        self.safeguards["164.308(a)(1)"] = HIPAASafeguard(
            "164.308(a)(1)",
            HIPAASafeguardType.ADMINISTRATIVE,
            "Security Officer",
            "Assign security responsibilities to a security officer",
            required=True
        )

        # §164.308(a)(2) - Assigned Security Responsibilities
        self.safeguards["164.308(a)(2)"] = HIPAASafeguard(
            "164.308(a)(2)",
            HIPAASafeguardType.ADMINISTRATIVE,
            "Assigned Security Responsibilities",
            "Identify the security officer responsible for developing and implementing policies",
            required=True
        )

        # §164.308(a)(3) - Workforce Training and Access Management
        self.safeguards["164.308(a)(3)"] = HIPAASafeguard(
            "164.308(a)(3)",
            HIPAASafeguardType.ADMINISTRATIVE,
            "Workforce Training and Access Management",
            "Authorize appropriate access to EPHI and provide workforce training",
            required=True
        )

        # §164.308(a)(4) - Information Access Management
        self.safeguards["164.308(a)(4)"] = HIPAASafeguard(
            "164.308(a)(4)",
            HIPAASafeguardType.ADMINISTRATIVE,
            "Information Access Management",
            "Implement policies for authorizing access to EPHI",
            required=True
        )

        # §164.308(a)(5) - Security Awareness and Training
        self.safeguards["164.308(a)(5)"] = HIPAASafeguard(
            "164.308(a)(5)",
            HIPAASafeguardType.ADMINISTRATIVE,
            "Security Awareness and Training",
            "Implement security awareness and training program for all workforce members",
            required=True
        )

        # §164.308(a)(6) - Security Incident Procedures
        self.safeguards["164.308(a)(6)"] = HIPAASafeguard(
            "164.308(a)(6)",
            HIPAASafeguardType.ADMINISTRATIVE,
            "Security Incident Procedures",
            "Implement procedures to address security incidents",
            required=True
        )

        # §164.308(a)(7) - Contingency Plan
        self.safeguards["164.308(a)(7)"] = HIPAASafeguard(
            "164.308(a)(7)",
            HIPAASafeguardType.ADMINISTRATIVE,
            "Contingency Plan",
            "Establish procedures for responding to emergencies or other occurrences",
            required=True
        )

        # §164.308(a)(8) - Evaluation
        self.safeguards["164.308(a)(8)"] = HIPAASafeguard(
            "164.308(a)(8)",
            HIPAASafeguardType.ADMINISTRATIVE,
            "Evaluation",
            "Perform periodic technical and non-technical evaluation",
            required=True
        )

    def _add_physical_safeguards(self):
        """Add physical safeguards (§164.310)."""

        # §164.310(a)(1) - Facility Access Controls
        self.safeguards["164.310(a)(1)"] = HIPAASafeguard(
            "164.310(a)(1)",
            HIPAASafeguardType.PHYSICAL,
            "Facility Access Controls",
            "Limit physical access to facilities while ensuring authorized access",
            required=True
        )

        # §164.310(a)(2) - Workstation Use
        self.safeguards["164.310(a)(2)"] = HIPAASafeguard(
            "164.310(a)(2)",
            HIPAASafeguardType.PHYSICAL,
            "Workstation Use",
            "Implement policies for workstations that access EPHI",
            required=True
        )

        # §164.310(d)(1) - Device and Media Controls
        self.safeguards["164.310(d)(1)"] = HIPAASafeguard(
            "164.310(d)(1)",
            HIPAASafeguardType.PHYSICAL,
            "Device and Media Controls",
            "Implement policies for receiving, removing, and disposing of hardware and media",
            required=True
        )

    def _add_technical_safeguards(self):
        """Add technical safeguards (§164.312)."""

        # §164.312(a)(1) - Access Control
        self.safeguards["164.312(a)(1)"] = HIPAASafeguard(
            "164.312(a)(1)",
            HIPAASafeguardType.TECHNICAL,
            "Access Control",
            "Implement technical policies to allow only authorized persons to access EPHI",
            required=True
        )

        # §164.312(b) - Audit Controls
        self.safeguards["164.312(b)"] = HIPAASafeguard(
            "164.312(b)",
            HIPAASafeguardType.TECHNICAL,
            "Audit Controls",
            "Implement hardware, software, and/or procedural mechanisms for recording access",
            required=True
        )

        # §164.312(c)(1) - Integrity
        self.safeguards["164.312(c)(1)"] = HIPAASafeguard(
            "164.312(c)(1)",
            HIPAASafeguardType.TECHNICAL,
            "Integrity",
            "Protect EPHI from improper alteration or destruction",
            required=True
        )

        # §164.312(d) - Person or Entity Authentication
        self.safeguards["164.312(d)"] = HIPAASafeguard(
            "164.312(d)",
            HIPAASafeguardType.TECHNICAL,
            "Person or Entity Authentication",
            "Verify that person or entity seeking access is who they claim to be",
            required=True
        )

        # §164.312(e)(1) - Transmission Security
        self.safeguards["164.312(e)(1)"] = HIPAASafeguard(
            "164.312(e)(1)",
            HIPAASafeguardType.TECHNICAL,
            "Transmission Security",
            "Implement technical security measures to guard against unauthorized access to EPHI transmitted over networks",
            required=True
        )

    def conduct_risk_assessment(self, assessment_scope: str, assessor: str) -> str:
        """Conduct HIPAA risk assessment."""

        assessment_id = str(uuid4())

        # Sample risk assessment framework
        risk_categories = {
            "administrative": {
                "policies_procedures": "medium",
                "workforce_training": "low",
                "access_management": "high",
                "incident_response": "medium"
            },
            "physical": {
                "facility_security": "low",
                "workstation_controls": "medium",
                "media_handling": "low"
            },
            "technical": {
                "access_controls": "medium",
                "audit_logging": "low",
                "data_integrity": "medium",
                "transmission_security": "high"
            }
        }

        # Calculate overall risk score
        risk_scores = {"low": 1, "medium": 2, "high": 3}
        total_score = sum(
            risk_scores[risk_level]
            for category in risk_categories.values()
            for risk_level in category.values()
        )
        max_score = len([
            risk for category in risk_categories.values()
            for risk in category.values()
        ]) * 3

        overall_risk = "low" if total_score / max_score < 0.33 else "medium" if total_score / max_score < 0.67 else "high"

        assessment = {
            "assessment_id": assessment_id,
            "assessment_date": datetime.utcnow(),
            "scope": assessment_scope,
            "assessor": assessor,
            "risk_categories": risk_categories,
            "overall_risk_level": overall_risk,
            "risk_score": total_score / max_score,
            "recommendations": self._generate_risk_recommendations(risk_categories),
            "next_assessment_due": datetime.utcnow() + timedelta(days=365)  # Annual
        }

        self.risk_assessments.append(assessment)

        logger.info(f"HIPAA risk assessment completed: {assessment_id}, overall risk: {overall_risk}")
        return assessment_id

    def _generate_risk_recommendations(self, risk_categories: dict[str, dict[str, str]]) -> list[str]:
        """Generate recommendations based on risk assessment."""

        recommendations = []

        for category, risks in risk_categories.items():
            high_risks = [risk for risk, level in risks.items() if level == "high"]
            for risk in high_risks:
                if category == "administrative" and risk == "access_management":
                    recommendations.append("Implement role-based access controls for PHI")
                elif category == "technical" and risk == "transmission_security":
                    recommendations.append("Implement end-to-end encryption for PHI transmission")

        return recommendations

    def add_business_associate(
        self,
        name: str,
        contact_info: dict[str, str],
        services_provided: list[str],
        baa_signed_date: datetime,
        baa_expiry_date: datetime
    ) -> str:
        """Add business associate with BAA tracking."""

        ba_id = str(uuid4())

        business_associate = {
            "ba_id": ba_id,
            "name": name,
            "contact_info": contact_info,
            "services_provided": services_provided,
            "baa_signed_date": baa_signed_date,
            "baa_expiry_date": baa_expiry_date,
            "status": "active",
            "last_reviewed": datetime.utcnow(),
            "compliance_status": "compliant"
        }

        self.business_associates.append(business_associate)

        logger.info(f"Business associate added: {name} ({ba_id})")
        return ba_id

    def generate_hipaa_compliance_report(self) -> dict[str, Any]:
        """Generate comprehensive HIPAA compliance report."""

        total_safeguards = len(self.safeguards)
        implemented_safeguards = sum(
            1 for s in self.safeguards.values()
            if s.status == HIPAAComplianceStatus.COMPLIANT
        )

        # Group safeguards by type
        safeguards_by_type = {
            "administrative": [],
            "physical": [],
            "technical": []
        }

        for safeguard in self.safeguards.values():
            safeguards_by_type[safeguard.safeguard_type.value].append({
                "id": safeguard.id,
                "title": safeguard.title,
                "status": safeguard.status.value,
                "required": safeguard.required,
                "addressable": safeguard.addressable,
                "last_reviewed": safeguard.last_reviewed.isoformat() if safeguard.last_reviewed else None
            })

        # Recent risk assessments
        recent_assessments = [
            {
                "assessment_id": ra["assessment_id"],
                "assessment_date": ra["assessment_date"].isoformat(),
                "overall_risk_level": ra["overall_risk_level"],
                "assessor": ra["assessor"]
            }
            for ra in sorted(
                self.risk_assessments,
                key=lambda x: x["assessment_date"],
                reverse=True
            )[:5]
        ]

        # Business associate compliance
        active_bas = [ba for ba in self.business_associates if ba["status"] == "active"]
        expiring_baas = [
            ba for ba in active_bas
            if ba["baa_expiry_date"] <= datetime.utcnow() + timedelta(days=90)
        ]

        return {
            "report_date": datetime.utcnow().isoformat(),
            "compliance_summary": {
                "total_safeguards": total_safeguards,
                "implemented_safeguards": implemented_safeguards,
                "compliance_percentage": (implemented_safeguards / total_safeguards) * 100,
                "overall_status": "compliant" if implemented_safeguards / total_safeguards >= 0.9 else "non_compliant"
            },
            "safeguards_by_type": safeguards_by_type,
            "risk_management": {
                "total_assessments": len(self.risk_assessments),
                "recent_assessments": recent_assessments,
                "next_assessment_due": max(
                    [ra["next_assessment_due"] for ra in self.risk_assessments]
                ).isoformat() if self.risk_assessments else None
            },
            "business_associates": {
                "total_active": len(active_bas),
                "expiring_baas": len(expiring_baas),
                "baa_renewal_alerts": [
                    {
                        "name": ba["name"],
                        "expiry_date": ba["baa_expiry_date"].isoformat(),
                        "days_until_expiry": (ba["baa_expiry_date"] - datetime.utcnow()).days
                    }
                    for ba in expiring_baas
                ]
            },
            "phi_management": {
                "phi_records_tracked": len(self.phi_handler.phi_inventory),
                "access_logs_count": len(self.phi_handler.access_logs),
                "breach_incidents": len(self.phi_handler.phi_breaches),
                "recent_breaches": [
                    {
                        "breach_id": breach["breach_id"],
                        "discovery_date": breach["discovery_date"].isoformat(),
                        "affected_individuals": breach["affected_individuals"],
                        "status": breach["status"]
                    }
                    for breach in sorted(
                        self.phi_handler.phi_breaches,
                        key=lambda x: x["discovery_date"],
                        reverse=True
                    )[:5]
                ]
            }
        }

    def update_safeguard_status(
        self,
        safeguard_id: str,
        status: HIPAAComplianceStatus,
        evidence: str = None,
        reviewer: str = None
    ):
        """Update safeguard implementation status."""

        if safeguard_id not in self.safeguards:
            raise ValueError(f"Safeguard {safeguard_id} not found")

        safeguard = self.safeguards[safeguard_id]
        old_status = safeguard.status
        safeguard.status = status
        safeguard.last_reviewed = datetime.utcnow()

        if evidence:
            safeguard.evidence.append({
                "evidence_id": str(uuid4()),
                "date": datetime.utcnow(),
                "description": evidence,
                "reviewer": reviewer
            })

        logger.info(f"Safeguard {safeguard_id} status updated: {old_status.value} → {status.value}")


# Global HIPAA compliance framework instance
hipaa_framework = HIPAAComplianceFramework()
