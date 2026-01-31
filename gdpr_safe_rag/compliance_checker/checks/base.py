"""Base class for compliance checks."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CheckStatus(str, Enum):
    """Status of a compliance check."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    """Result of a compliance check.

    Attributes:
        name: Name of the check
        status: Check status (pass, fail, warning, error, skipped)
        message: Human-readable description of the result
        details: Additional details about the check
        remediation: Suggested remediation steps if applicable
    """

    name: str
    status: CheckStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    remediation: str | None = None

    @property
    def passed(self) -> bool:
        """Check if the result is passing."""
        return self.status in (CheckStatus.PASS, CheckStatus.WARNING)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "remediation": self.remediation,
        }


class BaseCheck(ABC):
    """Abstract base class for compliance checks."""

    name: str = "base_check"
    description: str = "Base compliance check"

    @abstractmethod
    async def run(self, context: dict[str, Any]) -> CheckResult:
        """Run the compliance check.

        Args:
            context: Context containing resources to check
                (e.g., audit_logger, pii_detector, documents)

        Returns:
            CheckResult with status and details
        """
        ...

    def skip(self, reason: str) -> CheckResult:
        """Create a skipped result.

        Args:
            reason: Reason for skipping

        Returns:
            CheckResult with SKIPPED status
        """
        return CheckResult(
            name=self.name,
            status=CheckStatus.SKIPPED,
            message=f"Check skipped: {reason}",
        )

    def error(self, message: str, exception: Exception | None = None) -> CheckResult:
        """Create an error result.

        Args:
            message: Error message
            exception: Optional exception that caused the error

        Returns:
            CheckResult with ERROR status
        """
        details = {}
        if exception:
            details["exception"] = str(exception)
            details["exception_type"] = type(exception).__name__

        return CheckResult(
            name=self.name,
            status=CheckStatus.ERROR,
            message=f"Check error: {message}",
            details=details,
        )
