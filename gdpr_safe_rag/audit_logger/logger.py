"""Main AuditLogger class."""

import json
from datetime import datetime, timedelta
from typing import Any

from gdpr_safe_rag.audit_logger.backends.base import BaseBackend
from gdpr_safe_rag.audit_logger.backends.memory_backend import MemoryBackend
from gdpr_safe_rag.audit_logger.backends.sqlite_backend import SQLiteBackend
from gdpr_safe_rag.audit_logger.exporters import AuditExporter
from gdpr_safe_rag.audit_logger.models import AuditEvent, EventType, QueryFilters
from gdpr_safe_rag.config import get_settings


class AuditLogger:
    """Main class for GDPR-compliant audit logging.

    Provides methods for logging various events (ingestion, query, access,
    deletion) with support for multiple storage backends.

    Example:
        >>> async with AuditLogger(storage_path="audit.db") as logger:
        ...     await logger.log_query(
        ...         user_id="user123",
        ...         query_text="What is the policy?",
        ...         retrieved_docs=["doc1", "doc2"]
        ...     )
    """

    def __init__(
        self,
        storage_path: str | None = None,
        backend: BaseBackend | None = None,
        retention_days: int | None = None,
    ) -> None:
        """Initialize the audit logger.

        Args:
            storage_path: Path for SQLite backend (ignored if backend provided)
            backend: Custom backend instance (optional)
            retention_days: Number of days to retain logs (default from settings)
        """
        settings = get_settings()

        if backend:
            self._backend = backend
        elif storage_path:
            self._backend = SQLiteBackend(storage_path)
        else:
            # Default to memory backend for testing
            self._backend = MemoryBackend()

        self._retention_days = retention_days or settings.audit_retention_days
        self._initialized = False

    @property
    def backend(self) -> BaseBackend:
        """Get the storage backend."""
        return self._backend

    @property
    def retention_days(self) -> int:
        """Get the retention period in days."""
        return self._retention_days

    async def initialize(self) -> None:
        """Initialize the audit logger and backend."""
        await self._backend.initialize()
        self._initialized = True

    async def close(self) -> None:
        """Close the audit logger and backend."""
        await self._backend.close()
        self._initialized = False

    async def __aenter__(self) -> "AuditLogger":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    def _create_event(
        self,
        event_type: EventType,
        user_id: str | None = None,
        session_id: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Create an audit event.

        Args:
            event_type: Type of event
            user_id: User performing the action
            session_id: Session identifier
            resource_id: Resource being acted upon
            action: Specific action taken
            data: Event-specific data
            metadata: Additional metadata

        Returns:
            AuditEvent instance
        """
        return AuditEvent(
            event_type=event_type.value,
            user_id=user_id,
            session_id=session_id,
            resource_id=resource_id,
            action=action,
            data=json.dumps(data) if data else None,
            metadata_json=json.dumps(metadata) if metadata else None,
        )

    async def log_ingestion(
        self,
        document_id: str,
        user_id: str | None = None,
        pii_detected: bool = False,
        pii_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Log a document ingestion event.

        Args:
            document_id: Identifier of the ingested document
            user_id: User who initiated the ingestion
            pii_detected: Whether PII was detected
            pii_count: Number of PII items detected
            metadata: Additional metadata

        Returns:
            Event ID
        """
        data = {
            "pii_detected": pii_detected,
            "pii_count": pii_count,
        }
        event = self._create_event(
            event_type=EventType.INGESTION,
            user_id=user_id,
            resource_id=document_id,
            action="ingest",
            data=data,
            metadata=metadata,
        )
        return await self._backend.write(event)

    async def log_query(
        self,
        user_id: str,
        query_text: str,
        retrieved_docs: list[str] | None = None,
        response_generated: bool = False,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Log a RAG query event.

        Args:
            user_id: User making the query
            query_text: The query text
            retrieved_docs: List of retrieved document IDs
            response_generated: Whether a response was generated
            session_id: Session identifier
            metadata: Additional metadata

        Returns:
            Event ID
        """
        data = {
            "query_text": query_text,
            "retrieved_docs": retrieved_docs or [],
            "retrieved_count": len(retrieved_docs) if retrieved_docs else 0,
            "response_generated": response_generated,
        }
        event = self._create_event(
            event_type=EventType.QUERY,
            user_id=user_id,
            session_id=session_id,
            action="query",
            data=data,
            metadata=metadata,
        )
        return await self._backend.write(event)

    async def log_access(
        self,
        user_id: str,
        action: str,
        resource: str,
        purpose: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Log a data access event.

        Args:
            user_id: User accessing the data
            action: Action performed (view, download, etc.)
            resource: Resource being accessed
            purpose: Purpose of access (for GDPR compliance)
            metadata: Additional metadata

        Returns:
            Event ID
        """
        data = {"purpose": purpose} if purpose else None
        event = self._create_event(
            event_type=EventType.ACCESS,
            user_id=user_id,
            resource_id=resource,
            action=action,
            data=data,
            metadata=metadata,
        )
        return await self._backend.write(event)

    async def log_deletion(
        self,
        user_id: str,
        resource: str,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Log a data deletion event.

        Args:
            user_id: User requesting/performing deletion
            resource: Resource being deleted
            reason: Reason for deletion (e.g., "user_request", "retention_policy")
            metadata: Additional metadata

        Returns:
            Event ID
        """
        data = {"reason": reason}
        event = self._create_event(
            event_type=EventType.DELETION,
            user_id=user_id,
            resource_id=resource,
            action="delete",
            data=data,
            metadata=metadata,
        )
        return await self._backend.write(event)

    async def log_consent_update(
        self,
        user_id: str,
        consent_type: str,
        granted: bool,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Log a consent update event.

        Args:
            user_id: User updating consent
            consent_type: Type of consent (e.g., "marketing", "analytics")
            granted: Whether consent was granted or revoked
            metadata: Additional metadata

        Returns:
            Event ID
        """
        data = {
            "consent_type": consent_type,
            "granted": granted,
        }
        event = self._create_event(
            event_type=EventType.CONSENT_UPDATE,
            user_id=user_id,
            action="consent_update",
            data=data,
            metadata=metadata,
        )
        return await self._backend.write(event)

    async def log_export(
        self,
        user_id: str,
        export_format: str,
        resource_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Log a data export event.

        Args:
            user_id: User requesting/receiving export
            export_format: Format of export (csv, json, etc.)
            resource_ids: IDs of exported resources
            metadata: Additional metadata

        Returns:
            Event ID
        """
        data = {
            "format": export_format,
            "resource_ids": resource_ids or [],
            "resource_count": len(resource_ids) if resource_ids else 0,
        }
        event = self._create_event(
            event_type=EventType.EXPORT,
            user_id=user_id,
            action="export",
            data=data,
            metadata=metadata,
        )
        return await self._backend.write(event)

    async def query_events(
        self,
        event_type: str | EventType | None = None,
        user_id: str | None = None,
        resource_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]:
        """Query audit events with filters.

        Args:
            event_type: Filter by event type
            user_id: Filter by user ID
            resource_id: Filter by resource ID
            start_date: Filter events after this date
            end_date: Filter events before this date
            limit: Maximum events to return
            offset: Number of events to skip

        Returns:
            List of matching audit events
        """
        filters = QueryFilters(
            event_type=event_type,
            user_id=user_id,
            resource_id=resource_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        return await self._backend.query(filters)

    async def get_user_activity(
        self,
        user_id: str,
        days: int = 30,
    ) -> list[AuditEvent]:
        """Get all activity for a specific user.

        Args:
            user_id: User to query
            days: Number of days to look back

        Returns:
            List of user's audit events
        """
        start_date = datetime.now() - timedelta(days=days)
        return await self.query_events(
            user_id=user_id,
            start_date=start_date,
            limit=1000,
        )

    async def enforce_retention(self) -> int:
        """Enforce retention policy by deleting old events.

        Returns:
            Number of events deleted
        """
        cutoff_date = datetime.now() - timedelta(days=self._retention_days)
        return await self._backend.delete_before(cutoff_date)

    async def export_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = "text",
    ) -> str:
        """Export a compliance report for the specified period.

        Args:
            start_date: Report period start
            end_date: Report period end
            format: Output format (text, csv, json)

        Returns:
            Formatted report string
        """
        events = await self.query_events(
            start_date=start_date,
            end_date=end_date,
            limit=10000,
        )

        if format == "csv":
            return AuditExporter.to_csv(events)
        elif format == "json":
            return AuditExporter.to_json(events, pretty=True)
        else:
            report = AuditExporter.to_compliance_report(
                events, start_date, end_date
            )
            return AuditExporter.compliance_report_to_text(report)
