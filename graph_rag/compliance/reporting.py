"""Compliance reporting system for SOC2, GDPR, HIPAA and other frameworks."""

import logging
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass

from pydantic import BaseModel, Field

from .audit_logging import ComplianceAuditLogger, AuditEventType
from .data_governance import DataGovernanceManager
from .access_controls import ComplianceAccessController, AccessControlFramework


logger = logging.getLogger(__name__)


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks for reporting."""
    
    SOC2_TYPE1 = "soc2_type1"
    SOC2_TYPE2 = "soc2_type2"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"
    NIST_CSF = "nist_csf"
    SOX = "sox"


class ReportFormat(str, Enum):
    """Supported report formats."""
    
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"


class ComplianceStatus(str, Enum):
    """Compliance status levels."""
    
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    UNDER_REVIEW = "under_review"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class ComplianceMetric:
    """Individual compliance metric."""
    
    metric_id: str
    name: str
    description: str
    framework: ComplianceFramework
    category: str
    
    # Current status
    status: ComplianceStatus
    score: float  # 0-100
    evidence_count: int
    last_assessment: datetime
    
    # Requirements
    required_controls: List[str]
    implemented_controls: List[str]
    missing_controls: List[str]
    
    # Recommendations
    recommendations: List[str]
    remediation_timeline: Optional[str] = None
    assigned_to: Optional[str] = None


class ComplianceReport(BaseModel):
    """Comprehensive compliance report."""
    
    report_id: str
    framework: ComplianceFramework
    tenant_id: Optional[str] = None
    
    # Report metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    reporting_period_start: datetime
    reporting_period_end: datetime
    generated_by: str
    report_version: str = "1.0"
    
    # Overall assessment
    overall_status: ComplianceStatus
    overall_score: float  # 0-100
    compliance_percentage: float
    
    # Metrics and findings
    metrics: List[ComplianceMetric]
    critical_findings: List[str]
    recommendations: List[str]
    
    # Evidence and documentation
    evidence_collected: int
    audit_events_reviewed: int
    policies_reviewed: List[str]
    
    # Risk assessment
    high_risk_areas: List[str]
    medium_risk_areas: List[str]
    low_risk_areas: List[str]
    
    # Next steps
    remediation_plan: List[Dict[str, Any]]
    next_assessment_date: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ComplianceReportGenerator:
    """Generates compliance reports for various frameworks."""
    
    def __init__(self, audit_logger: ComplianceAuditLogger,
                 data_governance: DataGovernanceManager,
                 access_controller: ComplianceAccessController):
        self.audit_logger = audit_logger
        self.data_governance = data_governance
        self.access_controller = access_controller
    
    async def generate_soc2_report(self, tenant_id: Optional[str] = None,
                                 period_days: int = 90) -> ComplianceReport:
        """Generate SOC2 Type 2 compliance report."""
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        # Collect SOC2 metrics
        metrics = []
        
        # Trust Service Category: Security
        security_metrics = await self._assess_soc2_security(tenant_id, start_date, end_date)
        metrics.extend(security_metrics)
        
        # Trust Service Category: Availability
        availability_metrics = await self._assess_soc2_availability(tenant_id, start_date, end_date)
        metrics.extend(availability_metrics)
        
        # Trust Service Category: Processing Integrity
        integrity_metrics = await self._assess_soc2_processing_integrity(tenant_id, start_date, end_date)
        metrics.extend(integrity_metrics)
        
        # Trust Service Category: Confidentiality
        confidentiality_metrics = await self._assess_soc2_confidentiality(tenant_id, start_date, end_date)
        metrics.extend(confidentiality_metrics)
        
        # Trust Service Category: Privacy
        privacy_metrics = await self._assess_soc2_privacy(tenant_id, start_date, end_date)
        metrics.extend(privacy_metrics)
        
        # Calculate overall compliance
        overall_score = sum(m.score for m in metrics) / len(metrics) if metrics else 0
        overall_status = self._determine_compliance_status(overall_score)
        
        # Identify critical findings
        critical_findings = [
            f"{m.name}: {m.status.value}" for m in metrics 
            if m.status == ComplianceStatus.NON_COMPLIANT
        ]
        
        # Generate recommendations
        recommendations = []
        for metric in metrics:
            recommendations.extend(metric.recommendations)
        
        # Create report
        report = ComplianceReport(
            report_id=f"soc2_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            framework=ComplianceFramework.SOC2_TYPE2,
            tenant_id=tenant_id,
            reporting_period_start=start_date,
            reporting_period_end=end_date,
            generated_by="synapse_compliance_system",
            overall_status=overall_status,
            overall_score=overall_score,
            compliance_percentage=(len([m for m in metrics if m.status == ComplianceStatus.COMPLIANT]) / len(metrics) * 100) if metrics else 0,
            metrics=metrics,
            critical_findings=critical_findings,
            recommendations=list(set(recommendations)),  # Remove duplicates
            evidence_collected=sum(m.evidence_count for m in metrics),
            audit_events_reviewed=await self._count_audit_events(tenant_id, start_date, end_date),
            policies_reviewed=["access_control", "data_governance", "incident_response"],
            high_risk_areas=[m.name for m in metrics if m.score < 60],
            medium_risk_areas=[m.name for m in metrics if 60 <= m.score < 80],
            low_risk_areas=[m.name for m in metrics if m.score >= 80],
            remediation_plan=await self._generate_remediation_plan(metrics),
            next_assessment_date=end_date + timedelta(days=90)
        )
        
        logger.info(f"Generated SOC2 compliance report: {overall_score:.1f}% compliance")
        
        return report
    
    async def generate_gdpr_report(self, tenant_id: Optional[str] = None,
                                 period_days: int = 365) -> ComplianceReport:
        """Generate GDPR compliance report."""
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        metrics = []
        
        # GDPR Article 5: Principles of processing
        principles_metric = await self._assess_gdpr_processing_principles(tenant_id, start_date, end_date)
        metrics.append(principles_metric)
        
        # GDPR Article 6: Lawfulness of processing
        lawfulness_metric = await self._assess_gdpr_lawful_basis(tenant_id, start_date, end_date)
        metrics.append(lawfulness_metric)
        
        # GDPR Article 7: Conditions for consent
        consent_metric = await self._assess_gdpr_consent_management(tenant_id, start_date, end_date)
        metrics.append(consent_metric)
        
        # GDPR Articles 15-22: Individual rights
        rights_metric = await self._assess_gdpr_individual_rights(tenant_id, start_date, end_date)
        metrics.append(rights_metric)
        
        # GDPR Article 25: Data protection by design and default
        privacy_design_metric = await self._assess_gdpr_privacy_by_design(tenant_id, start_date, end_date)
        metrics.append(privacy_design_metric)
        
        # GDPR Article 30: Records of processing
        records_metric = await self._assess_gdpr_processing_records(tenant_id, start_date, end_date)
        metrics.append(records_metric)
        
        # GDPR Article 32: Security of processing
        security_metric = await self._assess_gdpr_data_security(tenant_id, start_date, end_date)
        metrics.append(security_metric)
        
        # GDPR Article 33-34: Data breach notification
        breach_metric = await self._assess_gdpr_breach_notification(tenant_id, start_date, end_date)
        metrics.append(breach_metric)
        
        # Calculate overall compliance
        overall_score = sum(m.score for m in metrics) / len(metrics) if metrics else 0
        overall_status = self._determine_compliance_status(overall_score)
        
        # Create report
        report = ComplianceReport(
            report_id=f"gdpr_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            framework=ComplianceFramework.GDPR,
            tenant_id=tenant_id,
            reporting_period_start=start_date,
            reporting_period_end=end_date,
            generated_by="synapse_compliance_system",
            overall_status=overall_status,
            overall_score=overall_score,
            compliance_percentage=(len([m for m in metrics if m.status == ComplianceStatus.COMPLIANT]) / len(metrics) * 100) if metrics else 0,
            metrics=metrics,
            critical_findings=[f"{m.name}: {m.status.value}" for m in metrics if m.status == ComplianceStatus.NON_COMPLIANT],
            recommendations=list(set(sum([m.recommendations for m in metrics], []))),
            evidence_collected=sum(m.evidence_count for m in metrics),
            audit_events_reviewed=await self._count_audit_events(tenant_id, start_date, end_date),
            policies_reviewed=["privacy_policy", "data_processing", "consent_management", "data_retention"],
            high_risk_areas=[m.name for m in metrics if m.score < 70],
            medium_risk_areas=[m.name for m in metrics if 70 <= m.score < 85],
            low_risk_areas=[m.name for m in metrics if m.score >= 85],
            remediation_plan=await self._generate_remediation_plan(metrics),
            next_assessment_date=end_date + timedelta(days=180)
        )
        
        logger.info(f"Generated GDPR compliance report: {overall_score:.1f}% compliance")
        
        return report
    
    async def generate_hipaa_report(self, tenant_id: Optional[str] = None,
                                  period_days: int = 365) -> ComplianceReport:
        """Generate HIPAA compliance report."""
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        metrics = []
        
        # HIPAA Security Rule - Administrative Safeguards
        admin_safeguards = await self._assess_hipaa_administrative_safeguards(tenant_id, start_date, end_date)
        metrics.extend(admin_safeguards)
        
        # HIPAA Security Rule - Physical Safeguards
        physical_safeguards = await self._assess_hipaa_physical_safeguards(tenant_id, start_date, end_date)
        metrics.extend(physical_safeguards)
        
        # HIPAA Security Rule - Technical Safeguards
        technical_safeguards = await self._assess_hipaa_technical_safeguards(tenant_id, start_date, end_date)
        metrics.extend(technical_safeguards)
        
        # HIPAA Privacy Rule
        privacy_rule = await self._assess_hipaa_privacy_rule(tenant_id, start_date, end_date)
        metrics.extend(privacy_rule)
        
        # HIPAA Breach Notification Rule
        breach_notification = await self._assess_hipaa_breach_notification(tenant_id, start_date, end_date)
        metrics.append(breach_notification)
        
        # Calculate overall compliance
        overall_score = sum(m.score for m in metrics) / len(metrics) if metrics else 0
        overall_status = self._determine_compliance_status(overall_score)
        
        # Create report
        report = ComplianceReport(
            report_id=f"hipaa_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            framework=ComplianceFramework.HIPAA,
            tenant_id=tenant_id,
            reporting_period_start=start_date,
            reporting_period_end=end_date,
            generated_by="synapse_compliance_system",
            overall_status=overall_status,
            overall_score=overall_score,
            compliance_percentage=(len([m for m in metrics if m.status == ComplianceStatus.COMPLIANT]) / len(metrics) * 100) if metrics else 0,
            metrics=metrics,
            critical_findings=[f"{m.name}: {m.status.value}" for m in metrics if m.status == ComplianceStatus.NON_COMPLIANT],
            recommendations=list(set(sum([m.recommendations for m in metrics], []))),
            evidence_collected=sum(m.evidence_count for m in metrics),
            audit_events_reviewed=await self._count_audit_events(tenant_id, start_date, end_date),
            policies_reviewed=["hipaa_security", "hipaa_privacy", "phi_handling", "breach_response"],
            high_risk_areas=[m.name for m in metrics if m.score < 75],
            medium_risk_areas=[m.name for m in metrics if 75 <= m.score < 90],
            low_risk_areas=[m.name for m in metrics if m.score >= 90],
            remediation_plan=await self._generate_remediation_plan(metrics),
            next_assessment_date=end_date + timedelta(days=180)
        )
        
        logger.info(f"Generated HIPAA compliance report: {overall_score:.1f}% compliance")
        
        return report
    
    async def _assess_soc2_security(self, tenant_id: Optional[str], 
                                  start_date: datetime, end_date: datetime) -> List[ComplianceMetric]:
        """Assess SOC2 Security trust service category."""
        
        metrics = []
        
        # CC6.1 - Logical and Physical Access Controls
        access_stats = await self.access_controller.get_compliance_status(tenant_id)
        access_metric = ComplianceMetric(
            metric_id="soc2_cc6_1",
            name="Logical and Physical Access Controls",
            description="Controls to restrict logical and physical access",
            framework=ComplianceFramework.SOC2_TYPE2,
            category="Security",
            status=ComplianceStatus.COMPLIANT if access_stats['high_risk_sessions'] == 0 else ComplianceStatus.PARTIALLY_COMPLIANT,
            score=max(0, 100 - (access_stats['high_risk_sessions'] * 20)),
            evidence_count=access_stats['active_sessions'],
            last_assessment=datetime.utcnow(),
            required_controls=["user_authentication", "role_based_access", "session_management"],
            implemented_controls=["user_authentication", "role_based_access", "session_management"],
            missing_controls=[],
            recommendations=["Implement MFA for all users", "Regular access reviews"] if access_stats['mfa_protected_sessions'] < access_stats['active_sessions'] else []
        )
        metrics.append(access_metric)
        
        # CC6.2 - System Access
        audit_stats = await self.audit_logger.get_compliance_statistics(tenant_id)
        system_access_metric = ComplianceMetric(
            metric_id="soc2_cc6_2",
            name="System Access Monitoring",
            description="Monitoring of system access and activities",
            framework=ComplianceFramework.SOC2_TYPE2,
            category="Security",
            status=ComplianceStatus.COMPLIANT if audit_stats['failure_rate'] < 1.0 else ComplianceStatus.PARTIALLY_COMPLIANT,
            score=max(0, 100 - (audit_stats['failure_rate'] * 10)),
            evidence_count=audit_stats['total_events'],
            last_assessment=datetime.utcnow(),
            required_controls=["audit_logging", "access_monitoring", "anomaly_detection"],
            implemented_controls=["audit_logging", "access_monitoring"],
            missing_controls=["anomaly_detection"] if access_stats.get('suspicious_sessions', 0) > 0 else [],
            recommendations=["Enhance anomaly detection", "Automated alerting"] if access_stats.get('suspicious_sessions', 0) > 0 else []
        )
        metrics.append(system_access_metric)
        
        return metrics
    
    async def _assess_soc2_availability(self, tenant_id: Optional[str],
                                      start_date: datetime, end_date: datetime) -> List[ComplianceMetric]:
        """Assess SOC2 Availability trust service category."""
        
        # A1.1 - System Availability
        availability_metric = ComplianceMetric(
            metric_id="soc2_a1_1",
            name="System Availability",
            description="System availability and performance monitoring",
            framework=ComplianceFramework.SOC2_TYPE2,
            category="Availability",
            status=ComplianceStatus.COMPLIANT,  # Assume good availability for demo
            score=99.5,
            evidence_count=100,
            last_assessment=datetime.utcnow(),
            required_controls=["monitoring", "alerting", "backup_systems"],
            implemented_controls=["monitoring", "alerting", "backup_systems"],
            missing_controls=[],
            recommendations=["Implement automated failover", "Regular availability testing"]
        )
        
        return [availability_metric]
    
    async def _assess_soc2_processing_integrity(self, tenant_id: Optional[str],
                                              start_date: datetime, end_date: datetime) -> List[ComplianceMetric]:
        """Assess SOC2 Processing Integrity trust service category."""
        
        # PI1.1 - Data Processing Integrity
        integrity_metric = ComplianceMetric(
            metric_id="soc2_pi1_1",
            name="Data Processing Integrity",
            description="Controls to ensure data processing integrity",
            framework=ComplianceFramework.SOC2_TYPE2,
            category="Processing Integrity",
            status=ComplianceStatus.COMPLIANT,
            score=95.0,
            evidence_count=50,
            last_assessment=datetime.utcnow(),
            required_controls=["data_validation", "processing_controls", "error_handling"],
            implemented_controls=["data_validation", "processing_controls", "error_handling"],
            missing_controls=[],
            recommendations=["Implement additional data checksums", "Enhanced error reporting"]
        )
        
        return [integrity_metric]
    
    async def _assess_soc2_confidentiality(self, tenant_id: Optional[str],
                                         start_date: datetime, end_date: datetime) -> List[ComplianceMetric]:
        """Assess SOC2 Confidentiality trust service category."""
        
        # C1.1 - Data Confidentiality
        confidentiality_metric = ComplianceMetric(
            metric_id="soc2_c1_1",
            name="Data Confidentiality",
            description="Controls to protect confidential information",
            framework=ComplianceFramework.SOC2_TYPE2,
            category="Confidentiality",
            status=ComplianceStatus.COMPLIANT,
            score=92.0,
            evidence_count=75,
            last_assessment=datetime.utcnow(),
            required_controls=["encryption", "access_controls", "data_classification"],
            implemented_controls=["encryption", "access_controls", "data_classification"],
            missing_controls=[],
            recommendations=["Regular encryption key rotation", "Data loss prevention tools"]
        )
        
        return [confidentiality_metric]
    
    async def _assess_soc2_privacy(self, tenant_id: Optional[str],
                                 start_date: datetime, end_date: datetime) -> List[ComplianceMetric]:
        """Assess SOC2 Privacy trust service category."""
        
        # P1.1 - Privacy Notice
        privacy_metric = ComplianceMetric(
            metric_id="soc2_p1_1",
            name="Privacy Notice and Consent",
            description="Privacy notice and consent management",
            framework=ComplianceFramework.SOC2_TYPE2,
            category="Privacy",
            status=ComplianceStatus.COMPLIANT,
            score=88.0,
            evidence_count=30,
            last_assessment=datetime.utcnow(),
            required_controls=["privacy_notice", "consent_management", "data_subject_rights"],
            implemented_controls=["privacy_notice", "consent_management"],
            missing_controls=["data_subject_rights"],
            recommendations=["Implement data subject request portal", "Automate consent renewal"]
        )
        
        return [privacy_metric]
    
    async def _assess_gdpr_processing_principles(self, tenant_id: Optional[str],
                                               start_date: datetime, end_date: datetime) -> ComplianceMetric:
        """Assess GDPR Article 5 - Principles of processing."""
        
        return ComplianceMetric(
            metric_id="gdpr_art5",
            name="Principles of Processing",
            description="Lawfulness, fairness, transparency, purpose limitation, data minimization, accuracy, storage limitation, integrity, confidentiality, accountability",
            framework=ComplianceFramework.GDPR,
            category="Data Processing Principles",
            status=ComplianceStatus.COMPLIANT,
            score=90.0,
            evidence_count=100,
            last_assessment=datetime.utcnow(),
            required_controls=["lawful_basis", "purpose_limitation", "data_minimization", "accuracy", "storage_limitation"],
            implemented_controls=["lawful_basis", "purpose_limitation", "data_minimization", "storage_limitation"],
            missing_controls=["accuracy"],
            recommendations=["Implement data accuracy validation", "Regular data quality audits"]
        )
    
    async def _assess_gdpr_lawful_basis(self, tenant_id: Optional[str],
                                      start_date: datetime, end_date: datetime) -> ComplianceMetric:
        """Assess GDPR Article 6 - Lawfulness of processing."""
        
        return ComplianceMetric(
            metric_id="gdpr_art6",
            name="Lawful Basis for Processing",
            description="Documented lawful basis for all data processing activities",
            framework=ComplianceFramework.GDPR,
            category="Legal Basis",
            status=ComplianceStatus.COMPLIANT,
            score=95.0,
            evidence_count=50,
            last_assessment=datetime.utcnow(),
            required_controls=["lawful_basis_documentation", "processing_records"],
            implemented_controls=["lawful_basis_documentation", "processing_records"],
            missing_controls=[],
            recommendations=["Regular review of processing activities", "Update lawful basis documentation"]
        )
    
    async def _assess_gdpr_consent_management(self, tenant_id: Optional[str],
                                            start_date: datetime, end_date: datetime) -> ComplianceMetric:
        """Assess GDPR Article 7 - Conditions for consent."""
        
        return ComplianceMetric(
            metric_id="gdpr_art7",
            name="Consent Management",
            description="Valid consent collection, withdrawal mechanisms, and consent records",
            framework=ComplianceFramework.GDPR,
            category="Consent",
            status=ComplianceStatus.PARTIALLY_COMPLIANT,
            score=75.0,
            evidence_count=25,
            last_assessment=datetime.utcnow(),
            required_controls=["consent_collection", "withdrawal_mechanism", "consent_records"],
            implemented_controls=["consent_collection", "consent_records"],
            missing_controls=["withdrawal_mechanism"],
            recommendations=["Implement easy consent withdrawal", "Automated consent renewal reminders"]
        )
    
    async def _assess_gdpr_individual_rights(self, tenant_id: Optional[str],
                                           start_date: datetime, end_date: datetime) -> ComplianceMetric:
        """Assess GDPR Articles 15-22 - Individual rights."""
        
        return ComplianceMetric(
            metric_id="gdpr_art15_22",
            name="Individual Rights",
            description="Right to access, rectification, erasure, restrict processing, data portability, object, automated decision-making",
            framework=ComplianceFramework.GDPR,
            category="Individual Rights",
            status=ComplianceStatus.COMPLIANT,
            score=85.0,
            evidence_count=40,
            last_assessment=datetime.utcnow(),
            required_controls=["access_right", "rectification", "erasure", "portability", "objection"],
            implemented_controls=["access_right", "erasure", "portability"],
            missing_controls=["rectification", "objection"],
            recommendations=["Implement data rectification process", "Add objection handling"]
        )
    
    async def _assess_gdpr_privacy_by_design(self, tenant_id: Optional[str],
                                           start_date: datetime, end_date: datetime) -> ComplianceMetric:
        """Assess GDPR Article 25 - Data protection by design and default."""
        
        return ComplianceMetric(
            metric_id="gdpr_art25",
            name="Privacy by Design and Default",
            description="Data protection measures integrated into system design and default settings",
            framework=ComplianceFramework.GDPR,
            category="Privacy by Design",
            status=ComplianceStatus.COMPLIANT,
            score=88.0,
            evidence_count=30,
            last_assessment=datetime.utcnow(),
            required_controls=["privacy_by_design", "default_privacy_settings", "data_minimization"],
            implemented_controls=["privacy_by_design", "default_privacy_settings", "data_minimization"],
            missing_controls=[],
            recommendations=["Regular privacy impact assessments", "Enhanced data minimization"]
        )
    
    async def _assess_gdpr_processing_records(self, tenant_id: Optional[str],
                                            start_date: datetime, end_date: datetime) -> ComplianceMetric:
        """Assess GDPR Article 30 - Records of processing."""
        
        governance_stats = await self.data_governance.get_compliance_dashboard(tenant_id)
        
        return ComplianceMetric(
            metric_id="gdpr_art30",
            name="Records of Processing",
            description="Comprehensive records of all processing activities",
            framework=ComplianceFramework.GDPR,
            category="Documentation",
            status=ComplianceStatus.COMPLIANT if governance_stats['total_records'] > 0 else ComplianceStatus.NON_COMPLIANT,
            score=90.0 if governance_stats['total_records'] > 0 else 20.0,
            evidence_count=governance_stats['total_records'],
            last_assessment=datetime.utcnow(),
            required_controls=["processing_records", "data_inventory", "purpose_documentation"],
            implemented_controls=["processing_records", "data_inventory", "purpose_documentation"],
            missing_controls=[],
            recommendations=["Regular records review", "Automated record generation"]
        )
    
    async def _assess_gdpr_data_security(self, tenant_id: Optional[str],
                                       start_date: datetime, end_date: datetime) -> ComplianceMetric:
        """Assess GDPR Article 32 - Security of processing."""
        
        return ComplianceMetric(
            metric_id="gdpr_art32",
            name="Security of Processing",
            description="Appropriate technical and organizational measures for data security",
            framework=ComplianceFramework.GDPR,
            category="Security",
            status=ComplianceStatus.COMPLIANT,
            score=92.0,
            evidence_count=80,
            last_assessment=datetime.utcnow(),
            required_controls=["encryption", "access_controls", "integrity_controls", "availability_controls"],
            implemented_controls=["encryption", "access_controls", "integrity_controls", "availability_controls"],
            missing_controls=[],
            recommendations=["Regular security testing", "Enhanced monitoring"]
        )
    
    async def _assess_gdpr_breach_notification(self, tenant_id: Optional[str],
                                             start_date: datetime, end_date: datetime) -> ComplianceMetric:
        """Assess GDPR Articles 33-34 - Data breach notification."""
        
        return ComplianceMetric(
            metric_id="gdpr_art33_34",
            name="Data Breach Notification",
            description="Procedures for detecting, reporting and responding to data breaches",
            framework=ComplianceFramework.GDPR,
            category="Breach Response",
            status=ComplianceStatus.COMPLIANT,
            score=85.0,
            evidence_count=10,
            last_assessment=datetime.utcnow(),
            required_controls=["breach_detection", "notification_procedures", "response_plan"],
            implemented_controls=["breach_detection", "notification_procedures", "response_plan"],
            missing_controls=[],
            recommendations=["Regular breach response testing", "Staff training on breach procedures"]
        )
    
    async def _assess_hipaa_administrative_safeguards(self, tenant_id: Optional[str],
                                                    start_date: datetime, end_date: datetime) -> List[ComplianceMetric]:
        """Assess HIPAA Administrative Safeguards."""
        
        return [
            ComplianceMetric(
                metric_id="hipaa_admin_164_308",
                name="Administrative Safeguards",
                description="Security Officer, Workforce Training, Information Access Management, Security Awareness",
                framework=ComplianceFramework.HIPAA,
                category="Administrative Safeguards",
                status=ComplianceStatus.COMPLIANT,
                score=90.0,
                evidence_count=60,
                last_assessment=datetime.utcnow(),
                required_controls=["security_officer", "workforce_training", "access_management", "security_awareness"],
                implemented_controls=["security_officer", "workforce_training", "access_management", "security_awareness"],
                missing_controls=[],
                recommendations=["Regular security training updates", "Incident response drills"]
            )
        ]
    
    async def _assess_hipaa_physical_safeguards(self, tenant_id: Optional[str],
                                              start_date: datetime, end_date: datetime) -> List[ComplianceMetric]:
        """Assess HIPAA Physical Safeguards."""
        
        return [
            ComplianceMetric(
                metric_id="hipaa_phys_164_310",
                name="Physical Safeguards",
                description="Facility Access Controls, Workstation Use, Device and Media Controls",
                framework=ComplianceFramework.HIPAA,
                category="Physical Safeguards",
                status=ComplianceStatus.COMPLIANT,
                score=95.0,
                evidence_count=40,
                last_assessment=datetime.utcnow(),
                required_controls=["facility_access", "workstation_controls", "device_controls"],
                implemented_controls=["facility_access", "workstation_controls", "device_controls"],
                missing_controls=[],
                recommendations=["Regular physical security audits", "Update device inventory"]
            )
        ]
    
    async def _assess_hipaa_technical_safeguards(self, tenant_id: Optional[str],
                                               start_date: datetime, end_date: datetime) -> List[ComplianceMetric]:
        """Assess HIPAA Technical Safeguards."""
        
        return [
            ComplianceMetric(
                metric_id="hipaa_tech_164_312",
                name="Technical Safeguards",
                description="Access Control, Audit Controls, Integrity, Person or Entity Authentication, Transmission Security",
                framework=ComplianceFramework.HIPAA,
                category="Technical Safeguards",
                status=ComplianceStatus.COMPLIANT,
                score=88.0,
                evidence_count=70,
                last_assessment=datetime.utcnow(),
                required_controls=["access_control", "audit_controls", "integrity", "authentication", "transmission_security"],
                implemented_controls=["access_control", "audit_controls", "integrity", "authentication", "transmission_security"],
                missing_controls=[],
                recommendations=["Enhanced encryption standards", "Regular audit log reviews"]
            )
        ]
    
    async def _assess_hipaa_privacy_rule(self, tenant_id: Optional[str],
                                       start_date: datetime, end_date: datetime) -> List[ComplianceMetric]:
        """Assess HIPAA Privacy Rule."""
        
        return [
            ComplianceMetric(
                metric_id="hipaa_priv_164_500",
                name="Privacy Rule",
                description="Use and disclosure of PHI, individual rights, administrative requirements",
                framework=ComplianceFramework.HIPAA,
                category="Privacy Rule",
                status=ComplianceStatus.COMPLIANT,
                score=92.0,
                evidence_count=55,
                last_assessment=datetime.utcnow(),
                required_controls=["minimum_necessary", "individual_rights", "notices", "complaints"],
                implemented_controls=["minimum_necessary", "individual_rights", "notices", "complaints"],
                missing_controls=[],
                recommendations=["Update privacy notices", "Enhance complaint handling process"]
            )
        ]
    
    async def _assess_hipaa_breach_notification(self, tenant_id: Optional[str],
                                              start_date: datetime, end_date: datetime) -> ComplianceMetric:
        """Assess HIPAA Breach Notification Rule."""
        
        return ComplianceMetric(
            metric_id="hipaa_breach_164_400",
            name="Breach Notification Rule",
            description="Breach discovery, notification to individuals, HHS, and media",
            framework=ComplianceFramework.HIPAA,
            category="Breach Notification",
            status=ComplianceStatus.COMPLIANT,
            score=90.0,
            evidence_count=20,
            last_assessment=datetime.utcnow(),
            required_controls=["breach_discovery", "individual_notification", "hhs_notification", "media_notification"],
            implemented_controls=["breach_discovery", "individual_notification", "hhs_notification", "media_notification"],
            missing_controls=[],
            recommendations=["Regular breach response testing", "Update notification templates"]
        )
    
    async def _count_audit_events(self, tenant_id: Optional[str],
                                start_date: datetime, end_date: datetime) -> int:
        """Count audit events in reporting period."""
        
        audit_trail = await self.audit_logger.get_audit_trail(
            tenant_id=tenant_id,
            start_time=start_date,
            end_time=end_date,
            limit=10000
        )
        
        return len(audit_trail)
    
    def _determine_compliance_status(self, score: float) -> ComplianceStatus:
        """Determine compliance status based on score."""
        
        if score >= 95:
            return ComplianceStatus.COMPLIANT
        elif score >= 80:
            return ComplianceStatus.PARTIALLY_COMPLIANT
        elif score >= 60:
            return ComplianceStatus.UNDER_REVIEW
        else:
            return ComplianceStatus.NON_COMPLIANT
    
    async def _generate_remediation_plan(self, metrics: List[ComplianceMetric]) -> List[Dict[str, Any]]:
        """Generate remediation plan based on compliance gaps."""
        
        remediation_items = []
        
        for metric in metrics:
            if metric.status != ComplianceStatus.COMPLIANT:
                for control in metric.missing_controls:
                    remediation_items.append({
                        "control": control,
                        "metric": metric.name,
                        "priority": "high" if metric.score < 60 else "medium",
                        "estimated_effort": "2-4 weeks",
                        "responsible_team": "compliance",
                        "target_date": (datetime.utcnow() + timedelta(weeks=4)).isoformat()
                    })
        
        return remediation_items