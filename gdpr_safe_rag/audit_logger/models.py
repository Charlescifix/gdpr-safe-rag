"""SQLAlchemy models for audit logging."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class EventType(str, Enum):
    """Types of audit events."""

    INGESTION = "ingestion"
    QUERY = "query"
    ACCESS = "access"
    DELETION = "deletion"
    EXPORT = "export"
    CONSENT_UPDATE = "consent_update"
    RETENTION_CHECK = "retention_check"
    COMPLIANCE_CHECK = "compliance_check"


class AuditEvent(Base):
    """SQLAlchemy model for audit events.

    Stores all audit trail information with JSONB support for
    flexible event data storage.
    """

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    action: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    # Using Text for JSON storage (SQLite compatible)
    # For PostgreSQL, this would be JSONB
    data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    metadata_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index("ix_audit_events_timestamp_type", "timestamp", "event_type"),
        Index("ix_audit_events_user_timestamp", "user_id", "timestamp"),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        import json

        return {
            "id": self.id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "resource_id": self.resource_id,
            "action": self.action,
            "data": json.loads(self.data) if self.data else None,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else None,
        }


class QueryFilters:
    """Filters for querying audit events."""

    def __init__(
        self,
        event_type: str | EventType | None = None,
        user_id: str | None = None,
        resource_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> None:
        self.event_type = event_type.value if isinstance(event_type, EventType) else event_type
        self.user_id = user_id
        self.resource_id = resource_id
        self.start_date = start_date
        self.end_date = end_date
        self.limit = limit
        self.offset = offset
