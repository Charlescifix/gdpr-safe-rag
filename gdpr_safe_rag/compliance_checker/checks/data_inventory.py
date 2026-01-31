"""Data inventory compliance check."""

from typing import Any

from gdpr_safe_rag.compliance_checker.checks.base import BaseCheck, CheckResult, CheckStatus


class DataInventoryCheck(BaseCheck):
    """Check that a proper data inventory exists.

    GDPR Article 30 requires maintaining records of processing activities.
    This check verifies that documents are being tracked and PII is being
    detected during ingestion.
    """

    name = "data_inventory"
    description = "Verify data inventory and PII detection"

    def __init__(self, min_documents: int = 0, max_pii_rate: float = 1.0) -> None:
        """Initialize the check.

        Args:
            min_documents: Minimum number of documents expected
            max_pii_rate: Maximum acceptable PII detection rate (0.0-1.0)
        """
        self.min_documents = min_documents
        self.max_pii_rate = max_pii_rate

    async def run(self, context: dict[str, Any]) -> CheckResult:
        """Run the data inventory check.

        Context should contain:
            - documents: List of document metadata dicts
            - audit_logger: AuditLogger instance (optional)

        Returns:
            CheckResult with inventory statistics
        """
        documents = context.get("documents", [])

        if not documents:
            if self.min_documents > 0:
                return CheckResult(
                    name=self.name,
                    status=CheckStatus.FAIL,
                    message=f"No documents found. Expected at least {self.min_documents}.",
                    remediation="Ensure documents are being ingested and tracked.",
                )
            return CheckResult(
                name=self.name,
                status=CheckStatus.PASS,
                message="No documents to check.",
                details={"document_count": 0},
            )

        # Analyze document inventory
        total_docs = len(documents)
        docs_with_pii = sum(1 for d in documents if d.get("pii_detected", False))
        total_pii_count = sum(d.get("pii_count", 0) for d in documents)
        pii_rate = docs_with_pii / total_docs if total_docs > 0 else 0.0

        # Collect PII type statistics
        pii_types: dict[str, int] = {}
        for doc in documents:
            for pii_type, count in doc.get("pii_type_counts", {}).items():
                pii_types[pii_type] = pii_types.get(pii_type, 0) + count

        details = {
            "document_count": total_docs,
            "documents_with_pii": docs_with_pii,
            "pii_detection_rate": round(pii_rate, 4),
            "total_pii_items": total_pii_count,
            "pii_types": pii_types,
        }

        # Determine status
        if total_docs < self.min_documents:
            return CheckResult(
                name=self.name,
                status=CheckStatus.FAIL,
                message=f"Document count ({total_docs}) below minimum ({self.min_documents}).",
                details=details,
                remediation="Ensure all documents are being ingested and tracked.",
            )

        if pii_rate > self.max_pii_rate:
            return CheckResult(
                name=self.name,
                status=CheckStatus.WARNING,
                message=f"High PII detection rate ({pii_rate:.1%}). Review data handling.",
                details=details,
                remediation="Review documents with PII and ensure proper redaction.",
            )

        return CheckResult(
            name=self.name,
            status=CheckStatus.PASS,
            message=f"Data inventory verified: {total_docs} documents, {pii_rate:.1%} with PII.",
            details=details,
        )
