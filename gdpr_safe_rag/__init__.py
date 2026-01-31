"""
GDPR Safe RAG - Production-grade toolkit for GDPR-compliant RAG systems.

Provides automatic PII detection, audit trails, and compliance validation
for enterprise use with PostgreSQL backend.
"""

from gdpr_safe_rag.pii_detector import PIIDetector
from gdpr_safe_rag.audit_logger import AuditLogger
from gdpr_safe_rag.compliance_checker import ComplianceChecker

__version__ = "0.1.0"
__all__ = ["PIIDetector", "AuditLogger", "ComplianceChecker"]
