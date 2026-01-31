"""LangChain integration example.

This example demonstrates how to integrate GDPR Safe RAG
with a LangChain RAG pipeline for automatic PII handling.

Note: This is a conceptual example. LangChain is not included
in the dependencies by default.
"""

import asyncio
from datetime import datetime
from typing import Any

from gdpr_safe_rag.audit_logger import AuditLogger
from gdpr_safe_rag.audit_logger.backends.memory_backend import MemoryBackend
from gdpr_safe_rag.pii_detector import PIIDetector


class GDPRSafeDocumentLoader:
    """A document loader wrapper that automatically handles PII.

    This class demonstrates how to wrap a document loader to:
    1. Detect PII in loaded documents
    2. Redact PII before indexing
    3. Log ingestion events for audit trails
    4. Store PII mappings for potential restoration
    """

    def __init__(
        self,
        pii_detector: PIIDetector,
        audit_logger: AuditLogger,
        store_mapping: bool = True,
    ) -> None:
        """Initialize the GDPR-safe document loader.

        Args:
            pii_detector: PIIDetector instance
            audit_logger: AuditLogger instance
            store_mapping: Whether to store PII mappings
        """
        self.detector = pii_detector
        self.logger = audit_logger
        self.store_mapping = store_mapping
        self._mappings: dict[str, dict[str, str]] = {}

    async def load_and_process(
        self,
        documents: list[dict[str, Any]],
        user_id: str = "system",
    ) -> list[dict[str, Any]]:
        """Load and process documents with PII handling.

        Args:
            documents: List of documents with 'content' and 'id' fields
            user_id: User initiating the load

        Returns:
            List of processed documents with redacted content
        """
        processed = []

        for doc in documents:
            doc_id = doc.get("id", f"doc-{len(processed)}")
            content = doc.get("content", "")

            # Process for RAG (detect and redact PII)
            redacted_content, metadata = self.detector.process_for_rag(
                content, document_id=doc_id
            )

            # Log the ingestion
            await self.logger.log_ingestion(
                document_id=doc_id,
                user_id=user_id,
                pii_detected=metadata["pii_detected"],
                pii_count=metadata["pii_count"],
                metadata={
                    "pii_types": metadata["pii_types"],
                    "processed_at": datetime.now().isoformat(),
                },
            )

            # Store mapping if requested
            if self.store_mapping:
                result = self.detector.redact(content)
                self._mappings[doc_id] = result.mapping

            # Create processed document
            processed_doc = {
                **doc,
                "content": redacted_content,
                "metadata": {
                    **doc.get("metadata", {}),
                    "pii_redacted": metadata["pii_detected"],
                    "pii_count": metadata["pii_count"],
                },
            }
            processed.append(processed_doc)

            print(f"Processed {doc_id}: {metadata['pii_count']} PII items redacted")

        return processed

    def get_mapping(self, doc_id: str) -> dict[str, str]:
        """Get PII mapping for a document.

        Args:
            doc_id: Document identifier

        Returns:
            Mapping of tokens to original values
        """
        return self._mappings.get(doc_id, {})


class GDPRSafeRetriever:
    """A retriever wrapper that logs all queries for audit trails.

    This class demonstrates how to wrap a retriever to:
    1. Log all queries with user identification
    2. Track retrieved documents
    3. Support purpose specification for access logging
    """

    def __init__(
        self,
        audit_logger: AuditLogger,
    ) -> None:
        """Initialize the GDPR-safe retriever.

        Args:
            audit_logger: AuditLogger instance
        """
        self.logger = audit_logger

    async def retrieve(
        self,
        query: str,
        user_id: str,
        session_id: str | None = None,
        purpose: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve documents with audit logging.

        Args:
            query: Search query
            user_id: User making the query
            session_id: Optional session identifier
            purpose: Purpose of the query (for GDPR compliance)

        Returns:
            List of retrieved documents (mock implementation)
        """
        # Mock retrieval - in real use, this would call actual retriever
        mock_results = [
            {"id": "doc-001", "content": "Sample content 1", "score": 0.95},
            {"id": "doc-002", "content": "Sample content 2", "score": 0.87},
        ]

        # Log the query
        await self.logger.log_query(
            user_id=user_id,
            query_text=query,
            retrieved_docs=[r["id"] for r in mock_results],
            response_generated=True,
            session_id=session_id,
            metadata={"purpose": purpose} if purpose else None,
        )

        return mock_results


async def main() -> None:
    print("=" * 60)
    print("GDPR Safe RAG - LangChain Integration Example")
    print("=" * 60)

    # Initialize components
    detector = PIIDetector(region="UK", detection_level="strict")
    backend = MemoryBackend()

    async with AuditLogger(backend=backend) as logger:
        # Create GDPR-safe wrappers
        doc_loader = GDPRSafeDocumentLoader(detector, logger)
        retriever = GDPRSafeRetriever(logger)

        # Sample documents
        print("\n1. LOADING DOCUMENTS WITH PII HANDLING")
        print("-" * 40)

        documents = [
            {
                "id": "policy-001",
                "content": """
                Remote Work Policy

                For questions, contact HR at hr@company.com or call 020 7123 4567.
                Your manager John Smith (john.smith@company.com) can also help.
                """,
                "metadata": {"type": "policy"},
            },
            {
                "id": "guide-001",
                "content": """
                Employee Guide

                If you need medical leave, provide your NHS number to HR.
                Example: 123 456 7890 (this is just an example number).
                """,
                "metadata": {"type": "guide"},
            },
        ]

        processed_docs = await doc_loader.load_and_process(
            documents, user_id="admin"
        )

        print("\nProcessed documents:")
        for doc in processed_docs:
            print(f"\n{doc['id']}:")
            print(f"  Content preview: {doc['content'][:100]}...")
            print(f"  PII redacted: {doc['metadata']['pii_redacted']}")
            print(f"  PII count: {doc['metadata']['pii_count']}")

        # Simulate queries
        print("\n2. QUERYING WITH AUDIT LOGGING")
        print("-" * 40)

        queries = [
            ("What is the remote work policy?", "user-001", "work planning"),
            ("How do I request medical leave?", "user-002", "personal inquiry"),
        ]

        for query, user_id, purpose in queries:
            results = await retriever.retrieve(
                query=query,
                user_id=user_id,
                session_id=f"session-{user_id}",
                purpose=purpose,
            )
            print(f"\nQuery: '{query}'")
            print(f"  User: {user_id}")
            print(f"  Results: {len(results)} documents")

        # Show audit trail
        print("\n3. AUDIT TRAIL")
        print("-" * 40)

        all_events = await logger.query_events(limit=10)
        print(f"Total events logged: {len(all_events)}")

        for event in all_events:
            print(f"\n  {event.event_type}: {event.timestamp}")
            print(f"    User: {event.user_id}")
            if event.resource_id:
                print(f"    Resource: {event.resource_id}")

        # Show PII mapping retrieval (for authorized access)
        print("\n4. PII MAPPING ACCESS (Authorized Use)")
        print("-" * 40)

        mapping = doc_loader.get_mapping("policy-001")
        if mapping:
            print("PII mapping for policy-001:")
            for token, original in mapping.items():
                print(f"  {token} -> {original}")
        else:
            print("No PII mapping stored for policy-001")

    print("\n" + "=" * 60)
    print("Integration example completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
