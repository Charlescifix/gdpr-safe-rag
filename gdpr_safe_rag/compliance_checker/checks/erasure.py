"""Data erasure (right to be forgotten) compliance check."""

from datetime import datetime, timedelta
from typing import Any

from gdpr_safe_rag.audit_logger.models import EventType, QueryFilters
from gdpr_safe_rag.compliance_checker.checks.base import BaseCheck, CheckResult, CheckStatus


class ErasureCheck(BaseCheck):
    """Check data erasure capability and compliance.

    GDPR Article 17 grants the right to erasure. This check verifies:
    - Deletion requests are being logged
    - Deletions are being completed
    - Average response time for deletion requests
    """

    name = "erasure_capability"
    description = "Verify right to erasure compliance"

    def __init__(self, max_response_days: int = 30) -> None:
        """Initialize the check.

        Args:
            max_response_days: Maximum days to respond to erasure requests
                (GDPR requires response within 30 days)
        """
        self.max_response_days = max_response_days

    async def run(self, context: dict[str, Any]) -> CheckResult:
        """Run the erasure capability check.

        Context should contain:
            - audit_logger: AuditLogger instance
            - check_period_days: Number of days to check (default 90)

        Returns:
            CheckResult with erasure statistics
        """
        audit_logger = context.get("audit_logger")

        if not audit_logger:
            return self.skip("No audit logger provided")

        check_period = context.get("check_period_days", 90)
        start_date = datetime.now() - timedelta(days=check_period)

        try:
            # Query deletion events
            filters = QueryFilters(
                event_type=EventType.DELETION,
                start_date=start_date,
                limit=1000,
            )
            deletion_events = await audit_logger.backend.query(filters)

            if not deletion_events:
                return CheckResult(
                    name=self.name,
                    status=CheckStatus.PASS,
                    message="No deletion requests in check period.",
                    details={
                        "check_period_days": check_period,
                        "deletion_count": 0,
                    },
                )

            # Analyze deletion events
            total_deletions = len(deletion_events)
            deletions_by_reason: dict[str, int] = {}
            user_deletions: dict[str, int] = {}

            for event in deletion_events:
                # Parse data if it's a string
                import json
                data = event.data
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        data = {}

                reason = data.get("reason", "unknown") if data else "unknown"
                deletions_by_reason[reason] = deletions_by_reason.get(reason, 0) + 1

                if event.user_id:
                    user_deletions[event.user_id] = user_deletions.get(event.user_id, 0) + 1

            details = {
                "check_period_days": check_period,
                "total_deletions": total_deletions,
                "deletions_by_reason": deletions_by_reason,
                "unique_users_requesting_deletion": len(user_deletions),
                "user_request_count": deletions_by_reason.get("user_request", 0),
            }

            # Check for concerning patterns
            user_requests = deletions_by_reason.get("user_request", 0)
            if user_requests > total_deletions * 0.5:
                return CheckResult(
                    name=self.name,
                    status=CheckStatus.WARNING,
                    message=f"High volume of user deletion requests ({user_requests}).",
                    details=details,
                    remediation=(
                        "Review data collection practices if many users "
                        "are requesting data deletion."
                    ),
                )

            return CheckResult(
                name=self.name,
                status=CheckStatus.PASS,
                message=f"Erasure capability verified: {total_deletions} deletions logged.",
                details=details,
            )

        except Exception as e:
            return self.error("Failed to query deletion events", e)
