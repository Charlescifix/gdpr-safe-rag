"""Abstract base class for audit logger backends."""

from abc import ABC, abstractmethod
from datetime import datetime

from gdpr_safe_rag.audit_logger.models import AuditEvent, QueryFilters


class BaseBackend(ABC):
    """Abstract base class for audit storage backends.

    All backends must implement these async methods for
    writing, querying, and managing audit events.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the backend (create tables, connections, etc.)."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close connections and cleanup resources."""
        ...

    @abstractmethod
    async def write(self, event: AuditEvent) -> str:
        """Write an audit event to storage.

        Args:
            event: The audit event to store

        Returns:
            The event ID
        """
        ...

    @abstractmethod
    async def query(self, filters: QueryFilters) -> list[AuditEvent]:
        """Query audit events with filters.

        Args:
            filters: Query filters to apply

        Returns:
            List of matching audit events
        """
        ...

    @abstractmethod
    async def get_by_id(self, event_id: str) -> AuditEvent | None:
        """Get a specific audit event by ID.

        Args:
            event_id: The event ID to retrieve

        Returns:
            The audit event or None if not found
        """
        ...

    @abstractmethod
    async def delete_before(self, date: datetime) -> int:
        """Delete all events before a given date.

        Used for retention policy enforcement.

        Args:
            date: Delete events with timestamps before this date

        Returns:
            Number of events deleted
        """
        ...

    @abstractmethod
    async def count(self, filters: QueryFilters | None = None) -> int:
        """Count events matching filters.

        Args:
            filters: Optional query filters

        Returns:
            Count of matching events
        """
        ...

    async def __aenter__(self) -> "BaseBackend":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: object) -> None:
        """Async context manager exit."""
        await self.close()
