"""SQLite backend for lightweight/local audit logging."""

from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from gdpr_safe_rag.audit_logger.backends.base import BaseBackend
from gdpr_safe_rag.audit_logger.models import AuditEvent, Base, QueryFilters


class SQLiteBackend(BaseBackend):
    """SQLite storage backend using async SQLAlchemy.

    Suitable for local development, testing, and lightweight deployments.
    For production use with high volume, prefer PostgresBackend.
    """

    def __init__(self, database_path: str | Path = "audit_log.db") -> None:
        """Initialize SQLite backend.

        Args:
            database_path: Path to SQLite database file
        """
        self._database_path = Path(database_path)
        self._database_url = f"sqlite+aiosqlite:///{self._database_path}"
        self._engine = create_async_engine(
            self._database_url,
            echo=False,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def initialize(self) -> None:
        """Create database tables."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        """Close database connections."""
        await self._engine.dispose()

    async def write(self, event: AuditEvent) -> str:
        """Write an audit event to the database."""
        async with self._session_factory() as session:
            async with session.begin():
                session.add(event)
            return event.id

    async def query(self, filters: QueryFilters) -> list[AuditEvent]:
        """Query audit events with filters."""
        async with self._session_factory() as session:
            stmt = select(AuditEvent)

            if filters.event_type:
                stmt = stmt.where(AuditEvent.event_type == filters.event_type)

            if filters.user_id:
                stmt = stmt.where(AuditEvent.user_id == filters.user_id)

            if filters.resource_id:
                stmt = stmt.where(AuditEvent.resource_id == filters.resource_id)

            if filters.start_date:
                stmt = stmt.where(AuditEvent.timestamp >= filters.start_date)

            if filters.end_date:
                stmt = stmt.where(AuditEvent.timestamp <= filters.end_date)

            stmt = stmt.order_by(AuditEvent.timestamp.desc())
            stmt = stmt.offset(filters.offset).limit(filters.limit)

            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_by_id(self, event_id: str) -> AuditEvent | None:
        """Get a specific audit event by ID."""
        async with self._session_factory() as session:
            stmt = select(AuditEvent).where(AuditEvent.id == event_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def delete_before(self, date: datetime) -> int:
        """Delete all events before a given date."""
        async with self._session_factory() as session:
            async with session.begin():
                stmt = delete(AuditEvent).where(AuditEvent.timestamp < date)
                result = await session.execute(stmt)
                return result.rowcount

    async def count(self, filters: QueryFilters | None = None) -> int:
        """Count events matching filters."""
        async with self._session_factory() as session:
            stmt = select(func.count()).select_from(AuditEvent)

            if filters:
                if filters.event_type:
                    stmt = stmt.where(AuditEvent.event_type == filters.event_type)

                if filters.user_id:
                    stmt = stmt.where(AuditEvent.user_id == filters.user_id)

                if filters.resource_id:
                    stmt = stmt.where(AuditEvent.resource_id == filters.resource_id)

                if filters.start_date:
                    stmt = stmt.where(AuditEvent.timestamp >= filters.start_date)

                if filters.end_date:
                    stmt = stmt.where(AuditEvent.timestamp <= filters.end_date)

            result = await session.execute(stmt)
            return result.scalar() or 0
