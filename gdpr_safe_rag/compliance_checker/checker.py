"""Main ComplianceChecker class."""

from typing import Any

from gdpr_safe_rag.audit_logger import AuditLogger
from gdpr_safe_rag.compliance_checker.checks import (
    BaseCheck,
    DataInventoryCheck,
    ErasureCheck,
    RetentionCheck,
)
from gdpr_safe_rag.compliance_checker.report import ComplianceReport
from gdpr_safe_rag.config import get_settings


class ComplianceChecker:
    """Main class for running GDPR compliance checks.

    Runs a suite of checks against documents, audit logs, and
    system configuration to verify GDPR compliance.

    Example:
        >>> checker = ComplianceChecker(retention_days=2555)
        >>> async with AuditLogger() as logger:
        ...     report = await checker.run_all_checks(
        ...         documents=docs,
        ...         audit_logger=logger
        ...     )
        >>> print(report.to_text())
    """

    def __init__(
        self,
        retention_days: int | None = None,
        custom_checks: list[BaseCheck] | None = None,
    ) -> None:
        """Initialize the compliance checker.

        Args:
            retention_days: Retention period in days (default from settings)
            custom_checks: Additional custom checks to run
        """
        settings = get_settings()
        self._retention_days = retention_days or settings.audit_retention_days

        # Initialize default checks
        self._checks: list[BaseCheck] = [
            DataInventoryCheck(),
            RetentionCheck(retention_days=self._retention_days),
            ErasureCheck(),
        ]

        # Add custom checks
        if custom_checks:
            self._checks.extend(custom_checks)

    @property
    def checks(self) -> list[BaseCheck]:
        """Get the list of checks."""
        return self._checks

    def add_check(self, check: BaseCheck) -> None:
        """Add a custom check.

        Args:
            check: Check instance to add
        """
        self._checks.append(check)

    async def run_check(
        self,
        check: BaseCheck,
        context: dict[str, Any],
    ) -> Any:
        """Run a single check.

        Args:
            check: Check to run
            context: Context for the check

        Returns:
            CheckResult from the check
        """
        try:
            return await check.run(context)
        except Exception as e:
            return check.error(f"Unexpected error: {str(e)}", e)

    async def run_all_checks(
        self,
        documents: list[dict[str, Any]] | None = None,
        audit_logger: AuditLogger | None = None,
        check_period_days: int = 90,
        additional_context: dict[str, Any] | None = None,
    ) -> ComplianceReport:
        """Run all compliance checks.

        Args:
            documents: List of document metadata dictionaries
            audit_logger: AuditLogger instance for audit checks
            check_period_days: Period to check for audit events
            additional_context: Additional context for checks

        Returns:
            ComplianceReport with all check results
        """
        # Build context
        context: dict[str, Any] = {
            "documents": documents or [],
            "audit_logger": audit_logger,
            "check_period_days": check_period_days,
        }

        if additional_context:
            context.update(additional_context)

        # Run all checks
        report = ComplianceReport()
        report.metadata = {
            "retention_days": self._retention_days,
            "document_count": len(documents) if documents else 0,
            "check_period_days": check_period_days,
        }

        for check in self._checks:
            result = await self.run_check(check, context)
            report.add_check(result)

        return report

    async def generate_report(
        self,
        documents: list[dict[str, Any]] | None = None,
        audit_logger: AuditLogger | None = None,
        format: str = "text",
        include_remediation: bool = True,
    ) -> str:
        """Run checks and generate a formatted report.

        Args:
            documents: List of document metadata dictionaries
            audit_logger: AuditLogger instance
            format: Output format (text, json)
            include_remediation: Include remediation suggestions

        Returns:
            Formatted report string
        """
        report = await self.run_all_checks(
            documents=documents,
            audit_logger=audit_logger,
        )

        if format == "json":
            import json
            return json.dumps(report.to_dict(), indent=2, default=str)

        return report.to_text(include_remediation=include_remediation)
