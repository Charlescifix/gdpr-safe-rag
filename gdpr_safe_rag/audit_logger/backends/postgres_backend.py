"""PostgreSQL backend for production audit logging."""

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from gdpr_safe_rag.audit_logger.backends.base import BaseBackend
from gdpr_safe_rag.audit_logger.models import AuditEvent, Base, QueryFilters


class PostgresBackend(BaseBackend):
    """PostgreSQL storage backend using async SQLAlchemy with asyncpg.

    Production-grade backend with:
    - Connection pooling
    - JSONB support for efficient data querying
    - Proper indexing for audit queries
    - Transaction support
    """

    def __init__(
        self,
        database_url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        echo: bool = False,
    ) -> None:
        """Initialize PostgreSQL backend.

        Args:
            database_url: PostgreSQL connection URL
                (e.g., postgresql+asyncpg://user:pass@host/db)
            pool_size: Number of connections to keep in the pool
            max_overflow: Max connections beyond pool_size
            echo: Enable SQL logging
        """
        self._database_url = database_url
        self._engine = create_async_engine(
            database_url,
            echo=echo,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # Check connection health
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
        """Close database connections and dispose of the engine."""
        await self._engine.dispose()

    async def write(self, event: AuditEvent) -> str:
        """Write an audit event to the database.

        Uses a transaction to ensure atomicity.
        """
        async with self._session_factory() as session:
            async with session.begin():
                session.add(event)
            return event.id

    async def write_batch(self, events: list[AuditEvent]) -> list[str]:
        """Write multiple audit events in a single transaction.

        More efficient than individual writes for bulk operations.

        Args:
            events: List of events to write

        Returns:
            List of event IDs
        """
        async with self._session_factory() as session:
            async with session.begin():
                session.add_all(events)
            return [event.id for event in events]

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
        """Delete all events before a given date.

        Used for retention policy enforcement.
        """
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
