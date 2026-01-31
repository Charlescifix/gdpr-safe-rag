"""In-memory backend for testing."""

from datetime import datetime
from uuid import uuid4

from gdpr_safe_rag.audit_logger.backends.base import BaseBackend
from gdpr_safe_rag.audit_logger.models import AuditEvent, QueryFilters


class MemoryBackend(BaseBackend):
    """In-memory storage backend for testing.

    Events are stored in a list and lost when the backend is closed.
    Useful for unit tests and development.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the backend."""
        self._events = []
        self._initialized = True

    async def close(self) -> None:
        """Close the backend."""
        self._initialized = False

    async def write(self, event: AuditEvent) -> str:
        """Write an event to memory."""
        if not event.id:
            event.id = str(uuid4())
        if not event.timestamp:
            event.timestamp = datetime.now()
        self._events.append(event)
        return event.id

    async def query(self, filters: QueryFilters) -> list[AuditEvent]:
        """Query events with filters."""
        results = self._events.copy()

        if filters.event_type:
            results = [e for e in results if e.event_type == filters.event_type]

        if filters.user_id:
            results = [e for e in results if e.user_id == filters.user_id]

        if filters.resource_id:
            results = [e for e in results if e.resource_id == filters.resource_id]

        if filters.start_date:
            results = [e for e in results if e.timestamp and e.timestamp >= filters.start_date]

        if filters.end_date:
            results = [e for e in results if e.timestamp and e.timestamp <= filters.end_date]

        # Sort by timestamp descending
        results.sort(key=lambda e: e.timestamp or datetime.min, reverse=True)

        # Apply offset and limit
        start = filters.offset
        end = start + filters.limit
        return results[start:end]

    async def get_by_id(self, event_id: str) -> AuditEvent | None:
        """Get event by ID."""
        for event in self._events:
            if event.id == event_id:
                return event
        return None

    async def delete_before(self, date: datetime) -> int:
        """Delete events before date."""
        original_count = len(self._events)
        self._events = [e for e in self._events if e.timestamp and e.timestamp >= date]
        return original_count - len(self._events)

    async def count(self, filters: QueryFilters | None = None) -> int:
        """Count events matching filters."""
        if filters is None:
            return len(self._events)

        # Create a copy of filters with no limit for counting
        count_filters = QueryFilters(
            event_type=filters.event_type,
            user_id=filters.user_id,
            resource_id=filters.resource_id,
            start_date=filters.start_date,
            end_date=filters.end_date,
            limit=len(self._events),  # No limit for counting
            offset=0,
        )
        results = await self.query(count_filters)
        return len(results)
