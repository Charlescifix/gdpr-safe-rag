"""Custom exceptions for GDPR Safe RAG."""


class GDPRSafeRAGError(Exception):
    """Base exception for all GDPR Safe RAG errors."""

    pass


# PII Detector Exceptions
class PIIDetectorError(GDPRSafeRAGError):
    """Base exception for PII detector errors."""

    pass


class PatternValidationError(PIIDetectorError):
    """Raised when a PII pattern validation fails."""

    pass


class InvalidPatternError(PIIDetectorError):
    """Raised when a custom pattern is invalid."""

    pass


class RedactionError(PIIDetectorError):
    """Raised when redaction fails."""

    pass


# Audit Logger Exceptions
class AuditLoggerError(GDPRSafeRAGError):
    """Base exception for audit logger errors."""

    pass


class BackendConnectionError(AuditLoggerError):
    """Raised when connection to audit backend fails."""

    pass


class BackendWriteError(AuditLoggerError):
    """Raised when writing to audit backend fails."""

    pass


class BackendQueryError(AuditLoggerError):
    """Raised when querying audit backend fails."""

    pass


class InvalidEventError(AuditLoggerError):
    """Raised when an audit event is invalid."""

    pass


class RetentionPolicyError(AuditLoggerError):
    """Raised when retention policy enforcement fails."""

    pass


# Compliance Checker Exceptions
class ComplianceCheckerError(GDPRSafeRAGError):
    """Base exception for compliance checker errors."""

    pass


class CheckExecutionError(ComplianceCheckerError):
    """Raised when a compliance check fails to execute."""

    pass


class ReportGenerationError(ComplianceCheckerError):
    """Raised when report generation fails."""

    pass


class ConfigurationError(GDPRSafeRAGError):
    """Raised when configuration is invalid."""

    pass
