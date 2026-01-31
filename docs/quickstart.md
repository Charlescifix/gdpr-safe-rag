# Quick Start Guide

This guide will help you get started with GDPR Safe RAG in your Python application.

## Installation

### From PyPI

```bash
pip install gdpr-safe-rag
```

### From Source

```bash
git clone https://github.com/example/gdpr-safe-rag.git
cd gdpr-safe-rag
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev]"
```

## Basic Usage

### 1. PII Detection

The `PIIDetector` class is the main entry point for detecting and redacting PII.

```python
from gdpr_safe_rag import PIIDetector

# Create a detector configured for UK data
detector = PIIDetector(
    region="UK",           # UK, EU, or COMMON
    detection_level="strict",  # strict, moderate, or lenient
    redaction_strategy="token",  # token, hash, or category
)

# Detect PII in text
text = "Contact john@example.com or call 07700 900123"
items = detector.detect(text)

# Each item contains:
# - type: The PII type (email, phone, etc.)
# - value: The detected value
# - start/end: Position in the text
# - confidence: Detection confidence (0.0-1.0)

for item in items:
    print(f"Found {item.type}: {item.value}")
```

### 2. Redacting PII

```python
# Redact PII and get mapping for potential restoration
result = detector.redact(text)

print(result.redacted_text)
# Output: Contact [EMAIL_1] or call [PHONE_1]

print(result.mapping)
# Output: {'[EMAIL_1]': 'john@example.com', '[PHONE_1]': '07700 900123'}

# Restore original text if needed (e.g., for authorized users)
original = detector.restore(result.redacted_text, result.mapping)
```

### 3. RAG Pipeline Integration

```python
# Process documents for RAG ingestion
document = "Customer email: john@example.com, NHS: 123 456 7890"

redacted_text, metadata = detector.process_for_rag(
    document,
    document_id="doc-001"
)

# metadata contains:
# - pii_detected: bool
# - pii_count: int
# - pii_types: list of detected types
# - pii_type_counts: counts per type

# Use redacted_text for indexing
# Store metadata for audit trails
```

### 4. Audit Logging

```python
import asyncio
from gdpr_safe_rag import AuditLogger

async def setup_logging():
    # Create logger with SQLite backend
    async with AuditLogger(storage_path="audit.db") as logger:
        # Log document ingestion
        await logger.log_ingestion(
            document_id="doc-001",
            user_id="system",
            pii_detected=True,
            pii_count=5,
        )

        # Log user query
        await logger.log_query(
            user_id="user-123",
            query_text="What is the policy?",
            retrieved_docs=["doc-001", "doc-002"],
            response_generated=True,
        )

        # Log data access
        await logger.log_access(
            user_id="user-123",
            action="view",
            resource="doc-001",
            purpose="work task",
        )

        # Log deletion (GDPR Art. 17)
        await logger.log_deletion(
            user_id="user-456",
            resource="user-data",
            reason="user_request",
        )

asyncio.run(setup_logging())
```

### 5. Compliance Checking

```python
import asyncio
from datetime import datetime, timedelta
from gdpr_safe_rag import ComplianceChecker, AuditLogger

async def check_compliance():
    # Prepare document metadata
    documents = [
        {
            "id": "doc-001",
            "created_at": datetime.now() - timedelta(days=30),
            "pii_detected": True,
            "pii_count": 5,
            "pii_type_counts": {"email": 3, "phone": 2},
        },
    ]

    async with AuditLogger(storage_path="audit.db") as logger:
        # Create checker with 7-year retention
        checker = ComplianceChecker(retention_days=2555)

        # Run all compliance checks
        report = await checker.run_all_checks(
            documents=documents,
            audit_logger=logger,
        )

        # Display results
        print(report.to_text())

        # Check if compliant
        if report.passed:
            print("All compliance checks passed!")
        else:
            for failure in report.get_failures():
                print(f"FAIL: {failure.name}")
                print(f"  {failure.message}")
                if failure.remediation:
                    print(f"  Fix: {failure.remediation}")

asyncio.run(check_compliance())
```

## Redaction Strategies

### Token Strategy (Default)

Creates readable tokens with type and index:
```
john@example.com → [EMAIL_1]
07700 900123 → [PHONE_1]
```

### Hash Strategy

Creates tokens with short hash of original value:
```
john@example.com → [EMAIL_a3f5b9]
```

Useful when you need to identify identical values without revealing content.

### Category Strategy

Creates simple category tokens:
```
john@example.com → [EMAIL]
jane@example.com → [EMAIL]
```

All values of the same type get the same token.

## Detection Levels

- **Strict**: Lowest confidence threshold (0.5), catches more potential PII
- **Moderate**: Medium threshold (0.7), balanced approach
- **Lenient**: Highest threshold (0.9), only high-confidence matches

## PostgreSQL Setup

For production use, we recommend PostgreSQL:

```bash
# Start PostgreSQL with Docker
docker-compose up -d postgres

# Set environment variable
export DATABASE_URL=postgresql+asyncpg://gdpr_rag:devpassword@localhost:5432/gdpr_safe_rag
```

Then use the PostgreSQL backend:

```python
from gdpr_safe_rag.audit_logger.backends.postgres_backend import PostgresBackend

backend = PostgresBackend(
    database_url="postgresql+asyncpg://user:pass@localhost/db",
    pool_size=5,
)

async with AuditLogger(backend=backend) as logger:
    # Use logger as normal
    pass
```

## Next Steps

- See [Architecture](architecture.md) for system design details
- Check the `examples/` directory for more usage examples
- Run `pytest tests/` to verify your installation
