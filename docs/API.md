# API Reference

Complete API documentation for gdpr-safe-rag.

## Installation

```bash
pip install gdpr-safe-rag

# With optional dependencies
pip install gdpr-safe-rag[postgres]  # PostgreSQL support
pip install gdpr-safe-rag[ner]       # spaCy NER support
pip install gdpr-safe-rag[all]       # All optional dependencies
```

---

## PIIDetector

Main class for detecting and redacting PII in text.

### Constructor

```python
from gdpr_safe_rag import PIIDetector

detector = PIIDetector(
    region="UK",              # Region: "UK", "EU", "COMMON"
    detection_level="strict", # Sensitivity: "strict", "moderate", "lenient"
    redaction_strategy="token", # Strategy: "token", "hash", "category"
    custom_patterns=None      # List of custom pattern classes
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `region` | `str` | `"UK"` | Region for pattern selection (UK, EU, COMMON) |
| `detection_level` | `str` | `"strict"` | Detection sensitivity level |
| `redaction_strategy` | `str` | `"token"` | How PII is replaced in text |
| `custom_patterns` | `list` | `None` | Additional pattern classes |

### Detection Levels

| Level | Confidence Threshold | Description |
|-------|---------------------|-------------|
| `strict` | 0.5 | Include lower confidence matches |
| `moderate` | 0.7 | Balanced detection |
| `lenient` | 0.9 | Only high confidence matches |

### Redaction Strategies

| Strategy | Example Output | Description |
|----------|---------------|-------------|
| `token` | `[EMAIL_1]` | Human-readable, reversible tokens |
| `hash` | `[EMAIL_a3f5b9]` | Short hash of original value |
| `category` | `[EMAIL]` | Simple category tokens |

### Methods

#### `detect(text: str) -> list[PIIItem]`

Detect all PII in text without redacting.

```python
items = detector.detect("Contact john@example.com or call 07700 900123")

for item in items:
    print(f"{item.type}: {item.value} (confidence: {item.confidence})")
```

**Returns:** List of `PIIItem` objects.

---

#### `redact(text: str) -> RedactionResult`

Detect and redact all PII in text.

```python
result = detector.redact("Email: john@example.com, Phone: 07700 900123")

print(result.redacted_text)  # "Email: [EMAIL_1], Phone: [UK_PHONE_1]"
print(result.pii_count)       # 2
print(result.pii_types)       # {'email', 'uk_phone'}
print(result.mapping)         # {'[EMAIL_1]': 'john@example.com', ...}
```

**Returns:** `RedactionResult` object with:
- `redacted_text`: Text with PII replaced
- `pii_items`: List of detected PIIItem objects
- `mapping`: Dict mapping tokens to original values
- `stats`: Detection statistics
- `pii_count`: Total PII count
- `pii_types`: Set of detected PII types

---

#### `process_for_rag(document: str, document_id: str = None) -> tuple[str, dict]`

Process a document for RAG ingestion with metadata for audit trails.

```python
redacted_text, metadata = detector.process_for_rag(
    document="Customer email: john@example.com",
    document_id="doc_123"
)

# metadata = {
#     "pii_detected": True,
#     "pii_count": 1,
#     "pii_types": ["email"],
#     "detection_level": "strict",
#     "region": "UK",
#     "document_id": "doc_123",
#     "pii_type_counts": {"email": 1}
# }
```

**Returns:** Tuple of (redacted_text, metadata_dict)

---

#### `restore(redacted_text: str, mapping: dict) -> str`

Restore original text from redacted text using mapping.

```python
original = detector.restore(result.redacted_text, result.mapping)
```

---

## AuditLogger

GDPR-compliant audit logging with multiple storage backends.

### Constructor

```python
from gdpr_safe_rag import AuditLogger

# SQLite backend (default for production)
logger = AuditLogger(storage_path="audit.db")

# Memory backend (for testing)
logger = AuditLogger()

# Custom retention
logger = AuditLogger(storage_path="audit.db", retention_days=2555)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `storage_path` | `str` | `None` | Path for SQLite database |
| `backend` | `BaseBackend` | `None` | Custom backend instance |
| `retention_days` | `int` | `2555` | Log retention period (~7 years) |

### Usage (Async Context Manager)

```python
async with AuditLogger(storage_path="audit.db") as logger:
    await logger.log_query(
        user_id="user123",
        query_text="What is the policy?",
        retrieved_docs=["doc1", "doc2"]
    )
```

### Methods

#### `log_ingestion(...) -> str`

Log a document ingestion event.

```python
event_id = await logger.log_ingestion(
    document_id="doc_123",
    user_id="admin",
    pii_detected=True,
    pii_count=5,
    metadata={"source": "upload"}
)
```

---

#### `log_query(...) -> str`

Log a RAG query event.

```python
event_id = await logger.log_query(
    user_id="user123",
    query_text="What is the refund policy?",
    retrieved_docs=["doc1", "doc2"],
    response_generated=True,
    session_id="session_abc"
)
```

---

#### `log_access(...) -> str`

Log a data access event.

```python
event_id = await logger.log_access(
    user_id="user123",
    action="download",
    resource="report.pdf",
    purpose="customer_support"
)
```

---

#### `log_deletion(...) -> str`

Log a data deletion event.

```python
event_id = await logger.log_deletion(
    user_id="user123",
    resource="user_data_123",
    reason="user_request"
)
```

---

#### `log_consent_update(...) -> str`

Log a consent update event.

```python
event_id = await logger.log_consent_update(
    user_id="user123",
    consent_type="marketing",
    granted=False
)
```

---

#### `log_export(...) -> str`

Log a data export event.

```python
event_id = await logger.log_export(
    user_id="user123",
    export_format="json",
    resource_ids=["doc1", "doc2"]
)
```

---

#### `query_events(...) -> list[AuditEvent]`

Query audit events with filters.

```python
events = await logger.query_events(
    event_type="query",
    user_id="user123",
    start_date=datetime(2024, 1, 1),
    limit=100
)
```

---

#### `get_user_activity(user_id: str, days: int = 30) -> list[AuditEvent]`

Get all activity for a specific user.

```python
events = await logger.get_user_activity("user123", days=30)
```

---

#### `enforce_retention() -> int`

Delete events older than retention period.

```python
deleted_count = await logger.enforce_retention()
```

---

#### `export_compliance_report(...) -> str`

Export a compliance report.

```python
report = await logger.export_compliance_report(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    format="text"  # or "csv", "json"
)
```

---

## ComplianceChecker

Run GDPR compliance checks against documents and audit logs.

### Constructor

```python
from gdpr_safe_rag import ComplianceChecker

checker = ComplianceChecker(
    retention_days=2555,
    custom_checks=None
)
```

### Methods

#### `run_all_checks(...) -> ComplianceReport`

Run all compliance checks.

```python
async with AuditLogger(storage_path="audit.db") as logger:
    report = await checker.run_all_checks(
        documents=[{"id": "doc1", "has_pii": True}],
        audit_logger=logger,
        check_period_days=90
    )

    print(f"Compliant: {report.is_compliant}")
    print(f"Passed: {report.passed_count}/{report.total_count}")
```

---

#### `generate_report(...) -> str`

Run checks and generate a formatted report.

```python
report_text = await checker.generate_report(
    documents=docs,
    audit_logger=logger,
    format="text",  # or "json"
    include_remediation=True
)
print(report_text)
```

---

#### `add_check(check: BaseCheck) -> None`

Add a custom compliance check.

```python
from gdpr_safe_rag.compliance_checker.checks import BaseCheck

class CustomCheck(BaseCheck):
    name = "custom_check"
    description = "My custom compliance check"

    async def run(self, context):
        # Your check logic
        return self.pass_check("Check passed")

checker.add_check(CustomCheck())
```

---

## Data Models

### PIIItem

Represents a detected PII item.

```python
@dataclass
class PIIItem:
    type: str        # PII type (e.g., "email", "uk_postcode")
    value: str       # Detected value
    start: int       # Start position in text
    end: int         # End position in text
    confidence: float  # 0.0 to 1.0
```

### RedactionResult

Result of PII redaction.

```python
@dataclass
class RedactionResult:
    redacted_text: str
    pii_items: list[PIIItem]
    mapping: dict[str, str]
    stats: dict[str, Any]

    # Properties
    pii_count: int
    pii_types: set[str]

    # Methods
    def get_items_by_type(self, pii_type: str) -> list[PIIItem]
```

---

## Configuration

Settings can be configured via environment variables or `.env` file:

```bash
# .env
DATABASE_URL=sqlite+aiosqlite:///./gdpr_safe_rag.db
LOG_LEVEL=INFO
PII_DETECTION_LEVEL=strict
PII_DEFAULT_REDACTION_STRATEGY=token
AUDIT_RETENTION_DAYS=2555
PII_ENCRYPTION_KEY=your-base64-key  # Optional
```

Access settings programmatically:

```python
from gdpr_safe_rag.config import get_settings

settings = get_settings()
print(settings.pii_detection_level)
print(settings.audit_retention_days)
```

---

## Supported PII Types

### Common Patterns
- `email` - Email addresses
- `phone` - International phone numbers
- `credit_card` - Credit card numbers
- `ip_address` - IPv4 addresses
- `iban` - International Bank Account Numbers

### UK Patterns
- `uk_postcode` - UK postal codes
- `uk_phone` - UK phone numbers
- `uk_national_insurance` - NI numbers
- `nhs_number` - NHS numbers

### EU Patterns
- `eu_vat` - EU VAT numbers
- Regional ID patterns

---

## Complete Example

```python
import asyncio
from gdpr_safe_rag import PIIDetector, AuditLogger, ComplianceChecker

async def main():
    # Initialize detector
    detector = PIIDetector(region="UK", detection_level="strict")

    # Process document
    document = """
    Customer: John Smith
    Email: john.smith@example.com
    Phone: 07700 900123
    Postcode: SW1A 1AA
    """

    redacted, metadata = detector.process_for_rag(document, "doc_001")
    print(f"Redacted: {redacted}")
    print(f"PII found: {metadata['pii_count']}")

    # Log to audit trail
    async with AuditLogger(storage_path="audit.db") as logger:
        await logger.log_ingestion(
            document_id="doc_001",
            user_id="system",
            pii_detected=metadata["pii_detected"],
            pii_count=metadata["pii_count"]
        )

        # Run compliance check
        checker = ComplianceChecker()
        report = await checker.run_all_checks(
            documents=[{"id": "doc_001", **metadata}],
            audit_logger=logger
        )
        print(f"Compliance: {'PASS' if report.is_compliant else 'FAIL'}")

asyncio.run(main())
```
