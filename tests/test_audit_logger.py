"""Tests for Audit Logger module."""

from datetime import datetime, timedelta

import pytest

from gdpr_safe_rag.audit_logger import AuditLogger, AuditEvent, EventType
from gdpr_safe_rag.audit_logger.backends.memory_backend import MemoryBackend
from gdpr_safe_rag.audit_logger.models import QueryFilters


class TestMemoryBackend:
    """Tests for MemoryBackend."""

    @pytest.mark.asyncio
    async def test_write_and_query(self) -> None:
        """Test writing and querying events."""
        backend = MemoryBackend()
        await backend.initialize()

        event = AuditEvent(
            event_type="test",
            user_id="user-1",
        )
        event_id = await backend.write(event)

        assert event_id is not None
        events = await backend.query(QueryFilters(limit=10))
        assert len(events) == 1
        assert events[0].event_type == "test"

        await backend.close()

    @pytest.mark.asyncio
    async def test_query_filters(self) -> None:
        """Test query filters."""
        backend = MemoryBackend()
        await backend.initialize()

        # Create events with different types
        for event_type in ["type_a", "type_b", "type_a"]:
            event = AuditEvent(event_type=event_type, user_id="user-1")
            await backend.write(event)

        # Filter by type
        type_a_events = await backend.query(
            QueryFilters(event_type="type_a", limit=10)
        )
        assert len(type_a_events) == 2

        type_b_events = await backend.query(
            QueryFilters(event_type="type_b", limit=10)
        )
        assert len(type_b_events) == 1

        await backend.close()

    @pytest.mark.asyncio
    async def test_get_by_id(self) -> None:
        """Test getting event by ID."""
        backend = MemoryBackend()
        await backend.initialize()

        event = AuditEvent(event_type="test", user_id="user-1")
        event_id = await backend.write(event)

        retrieved = await backend.get_by_id(event_id)
        assert retrieved is not None
        assert retrieved.id == event_id

        missing = await backend.get_by_id("nonexistent")
        assert missing is None

        await backend.close()

    @pytest.mark.asyncio
    async def test_delete_before(self) -> None:
        """Test deleting old events."""
        backend = MemoryBackend()
        await backend.initialize()

        # Create events with different timestamps
        now = datetime.now()
        old_event = AuditEvent(event_type="test", timestamp=now - timedelta(days=100))
        new_event = AuditEvent(event_type="test", timestamp=now)

        await backend.write(old_event)
        await backend.write(new_event)

        # Delete events older than 50 days
        cutoff = now - timedelta(days=50)
        deleted = await backend.delete_before(cutoff)

        assert deleted == 1
        events = await backend.query(QueryFilters(limit=10))
        assert len(events) == 1

        await backend.close()

    @pytest.mark.asyncio
    async def test_count(self) -> None:
        """Test counting events."""
        backend = MemoryBackend()
        await backend.initialize()

        for i in range(5):
            event = AuditEvent(event_type="test", user_id=f"user-{i % 2}")
            await backend.write(event)

        total = await backend.count()
        assert total == 5

        user_0_count = await backend.count(QueryFilters(user_id="user-0"))
        assert user_0_count == 3

        await backend.close()


class TestAuditLogger:
    """Tests for the main AuditLogger class."""

    @pytest.mark.asyncio
    async def test_log_ingestion(self, audit_logger: AuditLogger) -> None:
        """Test logging document ingestion."""
        event_id = await audit_logger.log_ingestion(
            document_id="doc-001",
            user_id="admin",
            pii_detected=True,
            pii_count=5,
        )

        assert event_id is not None
        events = await audit_logger.query_events(event_type=EventType.INGESTION)
        assert len(events) == 1
        assert events[0].resource_id == "doc-001"

    @pytest.mark.asyncio
    async def test_log_query(self, audit_logger: AuditLogger) -> None:
        """Test logging RAG queries."""
        event_id = await audit_logger.log_query(
            user_id="user-001",
            query_text="What is the policy?",
            retrieved_docs=["doc-001", "doc-002"],
            response_generated=True,
            session_id="session-001",
        )

        assert event_id is not None
        events = await audit_logger.query_events(event_type=EventType.QUERY)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_log_access(self, audit_logger: AuditLogger) -> None:
        """Test logging data access."""
        event_id = await audit_logger.log_access(
            user_id="user-001",
            action="download",
            resource="doc-001",
            purpose="training",
        )

        assert event_id is not None
        events = await audit_logger.query_events(event_type=EventType.ACCESS)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_log_deletion(self, audit_logger: AuditLogger) -> None:
        """Test logging data deletion."""
        event_id = await audit_logger.log_deletion(
            user_id="user-001",
            resource="user-data-001",
            reason="user_request",
        )

        assert event_id is not None
        events = await audit_logger.query_events(event_type=EventType.DELETION)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_log_consent_update(self, audit_logger: AuditLogger) -> None:
        """Test logging consent updates."""
        event_id = await audit_logger.log_consent_update(
            user_id="user-001",
            consent_type="marketing",
            granted=False,
        )

        assert event_id is not None
        events = await audit_logger.query_events(event_type=EventType.CONSENT_UPDATE)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_log_export(self, audit_logger: AuditLogger) -> None:
        """Test logging data export."""
        event_id = await audit_logger.log_export(
            user_id="user-001",
            export_format="csv",
            resource_ids=["doc-001", "doc-002"],
        )

        assert event_id is not None
        events = await audit_logger.query_events(event_type=EventType.EXPORT)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_query_by_user(self, audit_logger: AuditLogger) -> None:
        """Test querying events by user."""
        await audit_logger.log_query(
            user_id="user-001", query_text="Query 1", retrieved_docs=[]
        )
        await audit_logger.log_query(
            user_id="user-002", query_text="Query 2", retrieved_docs=[]
        )
        await audit_logger.log_query(
            user_id="user-001", query_text="Query 3", retrieved_docs=[]
        )

        user_1_events = await audit_logger.query_events(user_id="user-001")
        assert len(user_1_events) == 2

    @pytest.mark.asyncio
    async def test_query_by_date_range(self, audit_logger: AuditLogger) -> None:
        """Test querying events by date range."""
        await audit_logger.log_query(
            user_id="user-001", query_text="Query", retrieved_docs=[]
        )

        # Query for events in the last hour
        start_date = datetime.now() - timedelta(hours=1)
        events = await audit_logger.query_events(start_date=start_date)
        assert len(events) == 1

        # Query for events from yesterday (should be empty)
        old_start = datetime.now() - timedelta(days=2)
        old_end = datetime.now() - timedelta(days=1)
        old_events = await audit_logger.query_events(
            start_date=old_start, end_date=old_end
        )
        assert len(old_events) == 0

    @pytest.mark.asyncio
    async def test_get_user_activity(self, audit_logger: AuditLogger) -> None:
        """Test getting user activity."""
        await audit_logger.log_query(
            user_id="user-001", query_text="Query 1", retrieved_docs=[]
        )
        await audit_logger.log_access(
            user_id="user-001", action="view", resource="doc-001"
        )

        activity = await audit_logger.get_user_activity("user-001", days=30)
        assert len(activity) == 2

    @pytest.mark.asyncio
    async def test_enforce_retention(self, audit_logger: AuditLogger) -> None:
        """Test retention policy enforcement."""
        # Create an old event by directly manipulating the backend
        old_event = AuditEvent(
            event_type="test",
            user_id="user-001",
            timestamp=datetime.now() - timedelta(days=3000),  # ~8 years old
        )
        await audit_logger.backend.write(old_event)

        # Create a recent event
        await audit_logger.log_query(
            user_id="user-001", query_text="Recent query", retrieved_docs=[]
        )

        # Enforce retention (default ~7 years)
        deleted = await audit_logger.enforce_retention()
        assert deleted == 1

        # Verify only recent event remains
        events = await audit_logger.query_events(limit=100)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_export_compliance_report_text(
        self, audit_logger: AuditLogger
    ) -> None:
        """Test exporting compliance report as text."""
        await audit_logger.log_ingestion("doc-001", "admin", True, 5)
        await audit_logger.log_query(
            "user-001", "Query", ["doc-001"], response_generated=True
        )
        await audit_logger.log_deletion("user-002", "old-data", "retention")

        report = await audit_logger.export_compliance_report(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            format="text",
        )

        assert "GDPR Compliance Audit Report" in report
        assert "Total Events:" in report

    @pytest.mark.asyncio
    async def test_export_compliance_report_csv(
        self, audit_logger: AuditLogger
    ) -> None:
        """Test exporting compliance report as CSV."""
        await audit_logger.log_ingestion("doc-001", "admin", True, 5)

        report = await audit_logger.export_compliance_report(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            format="csv",
        )

        assert "id,event_type,timestamp" in report
        assert "ingestion" in report

    @pytest.mark.asyncio
    async def test_export_compliance_report_json(
        self, audit_logger: AuditLogger
    ) -> None:
        """Test exporting compliance report as JSON."""
        await audit_logger.log_ingestion("doc-001", "admin", True, 5)

        report = await audit_logger.export_compliance_report(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            format="json",
        )

        import json

        data = json.loads(report)
        assert isinstance(data, list)
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_context_manager(self, memory_backend: MemoryBackend) -> None:
        """Test using AuditLogger as context manager."""
        async with AuditLogger(backend=memory_backend) as logger:
            await logger.log_ingestion("doc-001", "admin", False, 0)

        # Backend should be closed after context exits
        assert not memory_backend._initialized


class TestAuditEvent:
    """Tests for AuditEvent model."""

    def test_to_dict(self) -> None:
        """Test converting event to dictionary."""
        event = AuditEvent(
            id="test-id",
            event_type="query",
            user_id="user-001",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
        )

        data = event.to_dict()
        assert data["id"] == "test-id"
        assert data["event_type"] == "query"
        assert data["user_id"] == "user-001"


class TestQueryFilters:
    """Tests for QueryFilters."""

    def test_query_filters_with_event_type_enum(self) -> None:
        """Test QueryFilters accepts EventType enum."""
        filters = QueryFilters(event_type=EventType.QUERY)
        assert filters.event_type == "query"

    def test_query_filters_with_string(self) -> None:
        """Test QueryFilters accepts string event type."""
        filters = QueryFilters(event_type="query")
        assert filters.event_type == "query"

    def test_query_filters_defaults(self) -> None:
        """Test QueryFilters default values."""
        filters = QueryFilters()
        assert filters.limit == 100
        assert filters.offset == 0
        assert filters.event_type is None
