"""Data retention compliance check."""

from datetime import datetime, timedelta
from typing import Any

from gdpr_safe_rag.compliance_checker.checks.base import BaseCheck, CheckResult, CheckStatus


class RetentionCheck(BaseCheck):
    """Check data retention policy compliance.

    GDPR Article 5(1)(e) requires that personal data is kept no longer
    than necessary. This check verifies that documents don't exceed
    the retention period.
    """

    name = "retention_policy"
    description = "Verify data retention policy compliance"

    def __init__(self, retention_days: int = 2555) -> None:
        """Initialize the check.

        Args:
            retention_days: Maximum retention period in days (~7 years default)
        """
        self.retention_days = retention_days

    async def run(self, context: dict[str, Any]) -> CheckResult:
        """Run the retention policy check.

        Context should contain:
            - documents: List of document metadata dicts with 'created_at' field

        Returns:
            CheckResult with retention analysis
        """
        documents = context.get("documents", [])

        if not documents:
            return CheckResult(
                name=self.name,
                status=CheckStatus.PASS,
                message="No documents to check retention.",
                details={"document_count": 0},
            )

        now = datetime.now()
        cutoff_date = now - timedelta(days=self.retention_days)

        expired_docs = []
        expiring_soon = []  # Within 30 days of expiration
        expiring_threshold = now - timedelta(days=self.retention_days - 30)

        for doc in documents:
            created_at = doc.get("created_at")
            if not created_at:
                continue

            # Handle both datetime objects and ISO strings
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except ValueError:
                    continue

            # Remove timezone info for comparison if needed
            if created_at.tzinfo is not None:
                created_at = created_at.replace(tzinfo=None)

            if created_at < cutoff_date:
                expired_docs.append({
                    "id": doc.get("id", doc.get("document_id", "unknown")),
                    "created_at": created_at.isoformat(),
                    "days_old": (now - created_at).days,
                })
            elif created_at < expiring_threshold:
                expiring_soon.append({
                    "id": doc.get("id", doc.get("document_id", "unknown")),
                    "created_at": created_at.isoformat(),
                    "days_until_expiration": self.retention_days - (now - created_at).days,
                })

        details = {
            "retention_days": self.retention_days,
            "documents_checked": len(documents),
            "expired_count": len(expired_docs),
            "expiring_soon_count": len(expiring_soon),
            "expired_documents": expired_docs[:10],  # Limit for readability
            "expiring_soon": expiring_soon[:10],
        }

        if expired_docs:
            return CheckResult(
                name=self.name,
                status=CheckStatus.FAIL,
                message=f"{len(expired_docs)} documents exceed retention period.",
                details=details,
                remediation=(
                    f"Delete or archive {len(expired_docs)} documents that exceed "
                    f"the {self.retention_days}-day retention period."
                ),
            )

        if expiring_soon:
            return CheckResult(
                name=self.name,
                status=CheckStatus.WARNING,
                message=f"{len(expiring_soon)} documents expiring within 30 days.",
                details=details,
                remediation=(
                    "Review and plan for deletion or archival of documents "
                    "approaching retention limit."
                ),
            )

        return CheckResult(
            name=self.name,
            status=CheckStatus.PASS,
            message=f"All {len(documents)} documents within retention period.",
            details=details,
        )
