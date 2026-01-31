"""Audit logging example with PostgreSQL (or SQLite fallback).

This example demonstrates:
- Logging various audit events
- Querying audit trails
- Exporting compliance reports

To run with PostgreSQL:
    docker-compose up -d postgres
    export DATABASE_URL=postgresql+asyncpg://gdpr_rag:devpassword@localhost:5432/gdpr_safe_rag
    python examples/audit_logging_postgres.py

Or run with SQLite (default):
    python examples/audit_logging_postgres.py
"""

import asyncio
import os
from datetime import datetime, timedelta

from gdpr_safe_rag.audit_logger import AuditLogger
from gdpr_safe_rag.audit_logger.backends.sqlite_backend import SQLiteBackend


async def main() -> None:
    print("=" * 60)
    print("GDPR Safe RAG - Audit Logging Example")
    print("=" * 60)

    # Use SQLite for simplicity (PostgreSQL would use postgres_backend)
    db_path = "example_audit.db"

    # Clean up previous runs
    if os.path.exists(db_path):
        os.remove(db_path)

    backend = SQLiteBackend(db_path)

    async with AuditLogger(backend=backend) as logger:
        # 1. Log document ingestion
        print("\n1. LOGGING DOCUMENT INGESTION")
        print("-" * 40)

        for i in range(3):
            event_id = await logger.log_ingestion(
                document_id=f"doc-{i+1:03d}",
                user_id="system",
                pii_detected=i % 2 == 0,
                pii_count=5 if i % 2 == 0 else 0,
                metadata={"source": "upload", "format": "pdf"},
            )
            print(f"Logged ingestion: {event_id[:8]}... (doc-{i+1:03d})")

        # 2. Log queries
        print("\n2. LOGGING QUERIES")
        print("-" * 40)

        queries = [
            "What is the company policy on remote work?",
            "How do I request time off?",
            "What are the benefits available?",
        ]

        for i, query in enumerate(queries):
            event_id = await logger.log_query(
                user_id=f"user-{(i % 2) + 1:03d}",
                query_text=query,
                retrieved_docs=["doc-001", "doc-002"],
                response_generated=True,
                session_id=f"session-{i+1:03d}",
            )
            print(f"Logged query: {event_id[:8]}... (user-{(i % 2) + 1:03d})")

        # 3. Log access events
        print("\n3. LOGGING ACCESS EVENTS")
        print("-" * 40)

        event_id = await logger.log_access(
            user_id="user-001",
            action="download",
            resource="doc-001",
            purpose="Training material preparation",
        )
        print(f"Logged access: {event_id[:8]}...")

        # 4. Log deletion (right to erasure)
        print("\n4. LOGGING DELETION (GDPR Art. 17)")
        print("-" * 40)

        event_id = await logger.log_deletion(
            user_id="user-003",
            resource="user-003-data",
            reason="user_request",
            metadata={"requested_at": datetime.now().isoformat()},
        )
        print(f"Logged deletion: {event_id[:8]}...")

        # 5. Query audit events
        print("\n5. QUERYING AUDIT EVENTS")
        print("-" * 40)

        # Get all events for a user
        user_events = await logger.query_events(user_id="user-001")
        print(f"Events for user-001: {len(user_events)}")

        # Get all query events
        query_events = await logger.query_events(event_type="query")
        print(f"Query events: {len(query_events)}")

        # Get events from last hour
        recent_events = await logger.query_events(
            start_date=datetime.now() - timedelta(hours=1)
        )
        print(f"Events in last hour: {len(recent_events)}")

        # 6. Export compliance report
        print("\n6. COMPLIANCE REPORT")
        print("-" * 40)

        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        report = await logger.export_compliance_report(
            start_date=start_date,
            end_date=end_date,
            format="text",
        )
        print(report)

        # 7. Show individual event details
        print("\n7. EVENT DETAILS")
        print("-" * 40)

        events = await logger.query_events(limit=3)
        for event in events:
            print(f"\nEvent: {event.id[:8]}...")
            print(f"  Type: {event.event_type}")
            print(f"  User: {event.user_id}")
            print(f"  Time: {event.timestamp}")
            print(f"  Data: {event.data[:50]}..." if event.data else "  Data: None")

    # Clean up
    if os.path.exists(db_path):
        os.remove(db_path)

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
