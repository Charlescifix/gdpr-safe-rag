# GDPR Safe RAG

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Production-grade Python toolkit for GDPR-compliant RAG (Retrieval-Augmented Generation) systems with automatic PII detection, audit trails, and compliance validation.

## Features

- **PII Detection**: Automatic detection of personal identifiable information with support for UK, EU, and common patterns
- **Redaction Strategies**: Multiple redaction approaches (token, hash, category) for different use cases
- **Audit Logging**: Comprehensive audit trails with PostgreSQL or SQLite backends
- **Compliance Checking**: Built-in GDPR compliance validation with detailed reports
- **Async-First**: Full async/await support for modern Python applications
- **Type Safe**: Complete type hints with mypy strict mode compatibility

## Quick Start

### Installation

```bash
pip install gdpr-safe-rag
```

Or install from source:

```bash
git clone https://github.com/Charlescifix/gdpr-safe-rag.git
cd gdpr-safe-rag
pip install -e .
```

### Basic PII Detection

```python
from gdpr_safe_rag import PIIDetector

# Initialize detector with UK patterns
detector = PIIDetector(region="UK", detection_level="strict")

# Sample text with PII
text = """
Contact John Smith at john.smith@example.com or call 07700 900123.
His NHS number is 123 456 7890.
"""

# Detect PII
items = detector.detect(text)
for item in items:
    print(f"{item.type}: {item.value} (confidence: {item.confidence:.2f})")

# Redact PII
result = detector.redact(text)
print(result.redacted_text)
# Output: Contact John Smith at [EMAIL_1] or call [PHONE_1].
#         His NHS number is [NHS_NUMBER_1].

# Get mapping for potential restoration
print(result.mapping)
# Output: {'[EMAIL_1]': 'john.smith@example.com', ...}
```

### Audit Logging

```python
import asyncio
from gdpr_safe_rag import AuditLogger

async def main():
    async with AuditLogger(storage_path="audit.db") as logger:
        # Log document ingestion
        await logger.log_ingestion(
            document_id="doc-001",
            user_id="admin",
            pii_detected=True,
            pii_count=5,
        )

        # Log user query
        await logger.log_query(
            user_id="user-123",
            query_text="What is the company policy?",
            retrieved_docs=["doc-001", "doc-002"],
        )

        # Log data deletion (right to erasure)
        await logger.log_deletion(
            user_id="user-456",
            resource="user-456-data",
            reason="user_request",
        )

        # Export compliance report
        from datetime import datetime, timedelta
        report = await logger.export_compliance_report(
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
        )
        print(report)

asyncio.run(main())
```

### Compliance Checking

```python
import asyncio
from gdpr_safe_rag import ComplianceChecker, AuditLogger

async def main():
    # Sample documents with metadata
    documents = [
        {
            "id": "doc-001",
            "created_at": datetime.now() - timedelta(days=30),
            "pii_detected": True,
            "pii_count": 5,
        },
    ]

    async with AuditLogger(storage_path="audit.db") as logger:
        checker = ComplianceChecker(retention_days=2555)
        report = await checker.run_all_checks(
            documents=documents,
            audit_logger=logger,
        )

        print(report.to_text())
        # Shows detailed compliance status with remediation suggestions

asyncio.run(main())
```

## Supported PII Types

### UK Patterns
- Email addresses
- Phone numbers (mobile and landline)
- UK postcodes
- NHS numbers (with checksum validation)
- National Insurance numbers
- Credit card numbers (with Luhn validation)
- IBAN (with modulo 97 validation)

### EU Patterns
- Email addresses
- Phone numbers
- Credit card numbers
- IBAN

## Configuration

Configuration can be set via environment variables or `.env` file:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/gdpr_rag

# PII Detection
PII_DETECTION_LEVEL=strict  # strict, moderate, lenient

# Audit Settings
AUDIT_RETENTION_DAYS=2555  # ~7 years
```

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/Charlescifix/gdpr-safe-rag.git
cd gdpr-safe-rag

# Install development dependencies
pip install -e ".[dev]"

# Start PostgreSQL for testing (optional)
docker-compose up -d postgres
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=gdpr_safe_rag --cov-report=html

# Run type checking
mypy gdpr_safe_rag --strict

# Run linting
ruff check gdpr_safe_rag
black --check gdpr_safe_rag
```

### Running Examples

```bash
# PII Detection (no database needed)
python examples/basic_pii_detection.py

# Audit Logging
python examples/audit_logging_postgres.py

# Compliance Check
python examples/compliance_check.py
```

## Architecture

```
gdpr_safe_rag/
├── pii_detector/        # PII detection and redaction
│   ├── detector.py      # Main PIIDetector class
│   ├── patterns/        # Pattern definitions by region
│   ├── redactor.py      # Redaction strategies
│   └── validators.py    # Checksum validators
├── audit_logger/        # Audit trail functionality
│   ├── logger.py        # Main AuditLogger class
│   ├── backends/        # Storage backends (PostgreSQL, SQLite, Memory)
│   └── exporters.py     # Report export functionality
└── compliance_checker/  # GDPR compliance validation
    ├── checker.py       # Main ComplianceChecker class
    └── checks/          # Individual compliance checks
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## Support

- GitHub Issues: [Report bugs or request features](https://github.com/Charlescifix/gdpr-safe-rag/issues)
- Documentation: [Full documentation](docs/)
