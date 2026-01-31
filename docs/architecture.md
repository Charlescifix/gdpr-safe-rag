# Architecture Overview

This document describes the architecture and design decisions of GDPR Safe RAG.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GDPR Safe RAG                             │
├─────────────────┬─────────────────────┬─────────────────────────┤
│   PII Detector  │    Audit Logger     │   Compliance Checker    │
├─────────────────┼─────────────────────┼─────────────────────────┤
│  • Detection    │  • Event Logging    │  • Data Inventory       │
│  • Redaction    │  • Query/Export     │  • Retention Policy     │
│  • Validation   │  • Retention        │  • Erasure Capability   │
└────────┬────────┴──────────┬──────────┴───────────┬─────────────┘
         │                   │                      │
         │                   ▼                      │
         │         ┌─────────────────┐              │
         │         │    Backends     │              │
         │         ├─────────────────┤              │
         │         │ • PostgreSQL    │◄─────────────┘
         │         │ • SQLite        │
         │         │ • Memory        │
         │         └─────────────────┘
         │
         ▼
┌─────────────────┐
│    Patterns     │
├─────────────────┤
│ • UK Patterns   │
│ • EU Patterns   │
│ • Common        │
└─────────────────┘
```

## Component Details

### PII Detector Module

The PII Detector is responsible for identifying and redacting personal identifiable information.

```
pii_detector/
├── detector.py      # Main PIIDetector class
├── models.py        # PIIItem, RedactionResult dataclasses
├── redactor.py      # Redaction strategies
├── validators.py    # Checksum validation (Luhn, NHS, IBAN)
└── patterns/
    ├── base.py          # Abstract PIIPattern class
    ├── common.py        # Email, phone, credit card
    ├── uk_patterns.py   # UK-specific patterns
    └── eu_patterns.py   # EU-specific patterns
```

#### Pattern Architecture

Each PII pattern is a class that:
1. Defines a regex pattern for initial matching
2. Implements validation logic (checksums, format rules)
3. Provides confidence scoring

```python
class PIIPattern(ABC):
    name: str              # Unique identifier
    pattern: re.Pattern    # Regex for detection
    priority: int          # Higher = matched first
    confidence: float      # Base confidence score

    @abstractmethod
    def validate(self, match: str) -> bool:
        """Additional validation beyond regex"""
        ...

    def get_confidence(self, match: str) -> float:
        """Dynamic confidence based on match quality"""
        ...
```

#### Redaction Strategies

Three built-in strategies with different trade-offs:

| Strategy | Output | Reversible | Privacy |
|----------|--------|------------|---------|
| Token | `[EMAIL_1]` | Yes (with mapping) | High |
| Hash | `[EMAIL_a3f5b9]` | Correlation possible | Medium |
| Category | `[EMAIL]` | No | Highest |

### Audit Logger Module

The Audit Logger provides comprehensive audit trails for GDPR compliance.

```
audit_logger/
├── logger.py        # Main AuditLogger class
├── models.py        # SQLAlchemy models
├── exporters.py     # Report generation
└── backends/
    ├── base.py          # Abstract BaseBackend
    ├── postgres_backend.py  # PostgreSQL (production)
    ├── sqlite_backend.py    # SQLite (lightweight)
    └── memory_backend.py    # In-memory (testing)
```

#### Event Types

```python
class EventType(str, Enum):
    INGESTION = "ingestion"      # Document added
    QUERY = "query"              # User query executed
    ACCESS = "access"            # Data accessed
    DELETION = "deletion"        # Data deleted
    EXPORT = "export"            # Data exported
    CONSENT_UPDATE = "consent_update"  # Consent changed
    RETENTION_CHECK = "retention_check"  # Retention enforced
    COMPLIANCE_CHECK = "compliance_check"  # Compliance verified
```

#### Backend Interface

All backends implement the same async interface:

```python
class BaseBackend(ABC):
    async def initialize(self) -> None: ...
    async def close(self) -> None: ...
    async def write(self, event: AuditEvent) -> str: ...
    async def query(self, filters: QueryFilters) -> list[AuditEvent]: ...
    async def delete_before(self, date: datetime) -> int: ...
    async def count(self, filters: QueryFilters | None = None) -> int: ...
```

### Compliance Checker Module

The Compliance Checker validates GDPR compliance across the system.

```
compliance_checker/
├── checker.py       # Main ComplianceChecker class
├── report.py        # ComplianceReport generation
└── checks/
    ├── base.py          # Abstract BaseCheck
    ├── data_inventory.py    # Article 30 compliance
    ├── retention.py     # Article 5(1)(e) compliance
    └── erasure.py       # Article 17 compliance
```

#### Check Interface

```python
class BaseCheck(ABC):
    name: str
    description: str

    @abstractmethod
    async def run(self, context: dict) -> CheckResult: ...
```

#### Built-in Checks

1. **Data Inventory Check** (GDPR Art. 30)
   - Verifies document tracking
   - Monitors PII detection rates
   - Reports inventory statistics

2. **Retention Check** (GDPR Art. 5(1)(e))
   - Identifies expired documents
   - Warns about expiring documents
   - Enforces retention policies

3. **Erasure Check** (GDPR Art. 17)
   - Verifies deletion capability
   - Monitors deletion requests
   - Tracks response times

## Data Flow

### Document Ingestion

```
Document → PIIDetector.process_for_rag()
    │
    ├── Detect PII
    ├── Redact content
    ├── Generate metadata
    │
    ▼
AuditLogger.log_ingestion()
    │
    └── Store event with PII statistics
```

### User Query

```
User Query → RAG System
    │
    ├── Retrieve documents
    ├── Generate response
    │
    ▼
AuditLogger.log_query()
    │
    └── Store query, retrieved docs, user ID
```

### Compliance Verification

```
ComplianceChecker.run_all_checks()
    │
    ├── DataInventoryCheck
    │   └── Analyze document metadata
    │
    ├── RetentionCheck
    │   └── Check document ages
    │
    └── ErasureCheck
        └── Query deletion events
    │
    ▼
ComplianceReport
    │
    └── Aggregated results with remediation
```

## Design Decisions

### Async-First

All I/O operations are async to support:
- High-throughput document processing
- Non-blocking audit logging
- Concurrent compliance checks

### Pattern Extensibility

New PII patterns can be added by:
1. Creating a class extending `PIIPattern`
2. Implementing `validate()` method
3. Passing to `PIIDetector(custom_patterns=[...])`

### Backend Abstraction

The backend interface allows:
- Easy testing with in-memory backend
- Local development with SQLite
- Production deployment with PostgreSQL
- Future backends (e.g., cloud databases)

### Type Safety

Full type hints enable:
- IDE autocomplete
- Static type checking with mypy
- Self-documenting APIs

## Security Considerations

### PII Mapping Storage

The mapping between tokens and original values should be:
- Stored securely (encrypted at rest)
- Access-controlled
- Retained only as long as needed
- Deleted when source documents are deleted

### Audit Log Integrity

Consider:
- Append-only logging
- Checksums for tamper detection
- Secure backup procedures

### Database Security

For PostgreSQL:
- Use SSL/TLS connections
- Implement row-level security if needed
- Regular security audits

## Performance Considerations

### PII Detection

- Patterns are compiled once at initialization
- Priority ordering reduces unnecessary checks
- Consider batch processing for large volumes

### Audit Logging

- Async writes don't block main operations
- Connection pooling for PostgreSQL
- Batch writes available for bulk operations

### Compliance Checks

- Checks run in parallel where possible
- Pagination for large document sets
- Caching for repeated queries

## Deployment Options

### Single Server

```
Application ─── GDPR Safe RAG ─── SQLite
```

### Production

```
Application Cluster
        │
        ├── GDPR Safe RAG
        │
        └── PostgreSQL (with replication)
```

### Kubernetes

```yaml
# Suggested resource allocation
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```
