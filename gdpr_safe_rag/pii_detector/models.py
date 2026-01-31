"""Pydantic models for PII detection."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PIIItem:
    """Represents a detected PII item in text.

    Attributes:
        type: The type of PII (e.g., "email", "uk_postcode", "nhs_number")
        value: The detected PII value
        start: Start position in the original text
        end: End position in the original text
        confidence: Confidence score (0.0 to 1.0), higher for validated items
    """

    type: str
    value: str
    start: int
    end: int
    confidence: float = 1.0

    def __post_init__(self) -> None:
        """Validate the PIIItem."""
        if self.start < 0:
            raise ValueError("start must be non-negative")
        if self.end <= self.start:
            raise ValueError("end must be greater than start")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(slots=True)
class RedactionResult:
    """Result of redacting PII from text.

    Attributes:
        redacted_text: The text with PII replaced by tokens
        pii_items: List of detected PII items
        mapping: Dictionary mapping tokens to original values
        stats: Statistics about the redaction
    """

    redacted_text: str
    pii_items: list[PIIItem]
    mapping: dict[str, str]
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def pii_count(self) -> int:
        """Return total count of PII items detected."""
        return len(self.pii_items)

    @property
    def pii_types(self) -> set[str]:
        """Return set of PII types detected."""
        return {item.type for item in self.pii_items}

    def get_items_by_type(self, pii_type: str) -> list[PIIItem]:
        """Get all PII items of a specific type."""
        return [item for item in self.pii_items if item.type == pii_type]
