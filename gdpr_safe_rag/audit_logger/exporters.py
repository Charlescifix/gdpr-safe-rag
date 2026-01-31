"""Export functionality for audit logs."""

import csv
import io
import json
from datetime import datetime

from gdpr_safe_rag.audit_logger.models import AuditEvent


class AuditExporter:
    """Export audit events to various formats."""

    @staticmethod
    def to_csv(events: list[AuditEvent]) -> str:
        """Export events to CSV format.

        Args:
            events: List of audit events

        Returns:
            CSV string
        """
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "id",
                "event_type",
                "timestamp",
                "user_id",
                "session_id",
                "resource_id",
                "action",
                "data",
                "metadata",
            ],
        )
        writer.writeheader()

        for event in events:
            writer.writerow(event.to_dict())

        return output.getvalue()

    @staticmethod
    def to_json(events: list[AuditEvent], pretty: bool = False) -> str:
        """Export events to JSON format.

        Args:
            events: List of audit events
            pretty: If True, format with indentation

        Returns:
            JSON string
        """
        data = [event.to_dict() for event in events]
        if pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)

    @staticmethod
    def to_compliance_report(
        events: list[AuditEvent],
        start_date: datetime,
        end_date: datetime,
        include_details: bool = True,
    ) -> dict:
        """Generate a compliance report from audit events.

        Args:
            events: List of audit events
            start_date: Report period start
            end_date: Report period end
            include_details: Include detailed event listings

        Returns:
            Dictionary containing compliance report data
        """
        report: dict = {
            "report_type": "GDPR Compliance Audit Report",
            "generated_at": datetime.now().isoformat(),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "summary": {
                "total_events": len(events),
                "events_by_type": {},
                "unique_users": set(),
                "unique_resources": set(),
            },
        }

        # Calculate summary statistics
        for event in events:
            event_type = event.event_type
            report["summary"]["events_by_type"][event_type] = (
                report["summary"]["events_by_type"].get(event_type, 0) + 1
            )
            if event.user_id:
                report["summary"]["unique_users"].add(event.user_id)
            if event.resource_id:
                report["summary"]["unique_resources"].add(event.resource_id)

        # Convert sets to counts
        report["summary"]["unique_users"] = len(report["summary"]["unique_users"])
        report["summary"]["unique_resources"] = len(report["summary"]["unique_resources"])

        # Add GDPR-specific sections
        report["gdpr_compliance"] = {
            "data_access_events": report["summary"]["events_by_type"].get("access", 0),
            "data_deletion_events": report["summary"]["events_by_type"].get("deletion", 0),
            "consent_events": report["summary"]["events_by_type"].get("consent_update", 0),
            "export_events": report["summary"]["events_by_type"].get("export", 0),
        }

        # Optionally include detailed event listings
        if include_details:
            report["details"] = {
                "deletions": [
                    e.to_dict()
                    for e in events
                    if e.event_type == "deletion"
                ],
                "consent_changes": [
                    e.to_dict()
                    for e in events
                    if e.event_type == "consent_update"
                ],
                "data_exports": [
                    e.to_dict()
                    for e in events
                    if e.event_type == "export"
                ],
            }

        return report

    @staticmethod
    def compliance_report_to_text(report: dict) -> str:
        """Format compliance report as human-readable text.

        Args:
            report: Compliance report dictionary

        Returns:
            Formatted text report
        """
        lines = [
            "=" * 60,
            report["report_type"],
            "=" * 60,
            "",
            f"Generated: {report['generated_at']}",
            f"Period: {report['period']['start']} to {report['period']['end']}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Events: {report['summary']['total_events']}",
            f"Unique Users: {report['summary']['unique_users']}",
            f"Unique Resources: {report['summary']['unique_resources']}",
            "",
            "Events by Type:",
        ]

        for event_type, count in report["summary"]["events_by_type"].items():
            lines.append(f"  - {event_type}: {count}")

        lines.extend([
            "",
            "GDPR COMPLIANCE METRICS",
            "-" * 40,
            f"Data Access Events: {report['gdpr_compliance']['data_access_events']}",
            f"Data Deletion Events: {report['gdpr_compliance']['data_deletion_events']}",
            f"Consent Update Events: {report['gdpr_compliance']['consent_events']}",
            f"Data Export Events: {report['gdpr_compliance']['export_events']}",
            "",
            "=" * 60,
        ])

        return "\n".join(lines)
