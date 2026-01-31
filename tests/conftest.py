"""Pytest configuration and fixtures."""

import asyncio
import inspect

import pytest

from gdpr_safe_rag.audit_logger import AuditLogger
from gdpr_safe_rag.audit_logger.backends.memory_backend import MemoryBackend
from gdpr_safe_rag.pii_detector import PIIDetector


@pytest.fixture
def pii_detector() -> PIIDetector:
    """Create a PIIDetector instance for testing."""
    return PIIDetector(region="UK", detection_level="strict")


@pytest.fixture
def pii_detector_moderate() -> PIIDetector:
    """Create a PIIDetector with moderate detection level."""
    return PIIDetector(region="UK", detection_level="moderate")


@pytest.fixture
def memory_backend() -> MemoryBackend:
    """Create a MemoryBackend instance for testing."""
    return MemoryBackend()


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for the test suite."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as using asyncio without requiring pytest-asyncio",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Run async tests with asyncio without relying on external plugins."""
    testfunction = pyfuncitem.obj
    if inspect.iscoroutinefunction(testfunction):
        funcargs = {
            arg: pyfuncitem.funcargs[arg] for arg in pyfuncitem._fixtureinfo.argnames
        }
        asyncio.run(testfunction(**funcargs))
        return True
    return None


@pytest.fixture
def audit_logger(memory_backend: MemoryBackend) -> AuditLogger:
    """Create an AuditLogger instance with memory backend."""
    logger = AuditLogger(backend=memory_backend)
    asyncio.run(logger.initialize())
    yield logger
    asyncio.run(logger.close())


# Sample texts for testing
@pytest.fixture
def sample_text_with_pii() -> str:
    """Sample text containing various UK PII."""
    return """
    Contact John Smith at john.smith@example.com or call 07700 900123.
    His NHS number is 123 456 7890 and NI number is AB123456C.
    Send mail to 10 Downing Street, London SW1A 2AA.
    Credit card: 4532 0123 4567 8901
    IBAN: GB82 WEST 1234 5698 7654 32
    """


@pytest.fixture
def sample_text_no_pii() -> str:
    """Sample text without PII."""
    return """
    This is a sample document about company policies.
    It contains no personal information.
    The weather today is sunny with a high of 20 degrees.
    """


@pytest.fixture
def sample_documents() -> list[dict]:
    """Sample documents for compliance testing."""
    from datetime import datetime, timedelta

    return [
        {
            "id": "doc-001",
            "created_at": datetime.now() - timedelta(days=30),
            "pii_detected": True,
            "pii_count": 5,
            "pii_type_counts": {"email": 3, "phone": 2},
        },
        {
            "id": "doc-002",
            "created_at": datetime.now() - timedelta(days=60),
            "pii_detected": False,
            "pii_count": 0,
            "pii_type_counts": {},
        },
        {
            "id": "doc-003",
            "created_at": datetime.now() - timedelta(days=90),
            "pii_detected": True,
            "pii_count": 10,
            "pii_type_counts": {"email": 5, "nhs_number": 5},
        },
    ]
