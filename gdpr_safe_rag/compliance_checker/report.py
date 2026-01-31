"""Compliance report generation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from gdpr_safe_rag.compliance_checker.checks.base import CheckResult, CheckStatus


@dataclass
class ComplianceReport:
    """GDPR compliance report.

    Aggregates results from multiple compliance checks into
    a comprehensive report.
    """

    generated_at: datetime = field(default_factory=datetime.now)
    checks: list[CheckResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Check if all checks passed (or warned)."""
        return all(
            check.status in (CheckStatus.PASS, CheckStatus.WARNING, CheckStatus.SKIPPED)
            for check in self.checks
        )

    @property
    def total_checks(self) -> int:
        """Total number of checks run."""
        return len(self.checks)

    @property
    def passed_checks(self) -> int:
        """Number of checks that passed."""
        return sum(1 for c in self.checks if c.status == CheckStatus.PASS)

    @property
    def failed_checks(self) -> int:
        """Number of checks that failed."""
        return sum(1 for c in self.checks if c.status == CheckStatus.FAIL)

    @property
    def warning_checks(self) -> int:
        """Number of checks with warnings."""
        return sum(1 for c in self.checks if c.status == CheckStatus.WARNING)

    @property
    def error_checks(self) -> int:
        """Number of checks that errored."""
        return sum(1 for c in self.checks if c.status == CheckStatus.ERROR)

    @property
    def skipped_checks(self) -> int:
        """Number of checks that were skipped."""
        return sum(1 for c in self.checks if c.status == CheckStatus.SKIPPED)

    def add_check(self, result: CheckResult) -> None:
        """Add a check result to the report."""
        self.checks.append(result)

    def get_failures(self) -> list[CheckResult]:
        """Get all failed checks."""
        return [c for c in self.checks if c.status == CheckStatus.FAIL]

    def get_warnings(self) -> list[CheckResult]:
        """Get all checks with warnings."""
        return [c for c in self.checks if c.status == CheckStatus.WARNING]

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "overall_status": "PASS" if self.passed else "FAIL",
            "summary": {
                "total": self.total_checks,
                "passed": self.passed_checks,
                "failed": self.failed_checks,
                "warnings": self.warning_checks,
                "errors": self.error_checks,
                "skipped": self.skipped_checks,
            },
            "checks": [c.to_dict() for c in self.checks],
            "metadata": self.metadata,
        }

    def to_text(self, include_remediation: bool = True) -> str:
        """Format report as human-readable text.

        Args:
            include_remediation: Include remediation suggestions

        Returns:
            Formatted text report
        """
        lines = [
            "=" * 60,
            "GDPR COMPLIANCE REPORT",
            "=" * 60,
            "",
            f"Generated: {self.generated_at.isoformat()}",
            f"Overall Status: {'PASS' if self.passed else 'FAIL'}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Checks:  {self.total_checks}",
            f"  Passed:      {self.passed_checks}",
            f"  Failed:      {self.failed_checks}",
            f"  Warnings:    {self.warning_checks}",
            f"  Errors:      {self.error_checks}",
            f"  Skipped:     {self.skipped_checks}",
            "",
            "CHECK RESULTS",
            "-" * 40,
        ]

        # Status symbols
        symbols = {
            CheckStatus.PASS: "[PASS]",
            CheckStatus.FAIL: "[FAIL]",
            CheckStatus.WARNING: "[WARN]",
            CheckStatus.ERROR: "[ERR!]",
            CheckStatus.SKIPPED: "[SKIP]",
        }

        for check in self.checks:
            lines.append(f"{symbols[check.status]} {check.name}")
            lines.append(f"       {check.message}")

            if include_remediation and check.remediation:
                lines.append(f"       Remediation: {check.remediation}")

            lines.append("")

        # Add failures section if any
        failures = self.get_failures()
        if failures:
            lines.extend([
                "REQUIRED ACTIONS",
                "-" * 40,
            ])
            for i, check in enumerate(failures, 1):
                lines.append(f"{i}. {check.name}: {check.message}")
                if check.remediation:
                    lines.append(f"   Action: {check.remediation}")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)
