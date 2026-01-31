"""Redaction strategies for PII."""

import hashlib
from abc import ABC, abstractmethod
from typing import ClassVar

from gdpr_safe_rag.pii_detector.models import PIIItem


class RedactionStrategy(ABC):
    """Abstract base class for redaction strategies."""

    @abstractmethod
    def generate_token(self, pii_item: PIIItem, index: int) -> str:
        """Generate a redaction token for a PII item.

        Args:
            pii_item: The PII item to redact
            index: Sequential index for this PII type

        Returns:
            Redaction token string
        """
        ...


class TokenRedactionStrategy(RedactionStrategy):
    """Token-based redaction: [EMAIL_1], [UK_POSTCODE_2], etc.

    This strategy creates human-readable, reversible tokens that
    indicate the type and occurrence number of each PII item.
    """

    def generate_token(self, pii_item: PIIItem, index: int) -> str:
        """Generate a token like [EMAIL_1] or [UK_POSTCODE_2]."""
        return f"[{pii_item.type.upper()}_{index}]"


class HashRedactionStrategy(RedactionStrategy):
    """Hash-based redaction: [EMAIL_a3f5b9], etc.

    This strategy creates tokens with a short hash of the original value,
    allowing correlation of identical values while hiding the actual content.
    """

    hash_length: ClassVar[int] = 6

    def generate_token(self, pii_item: PIIItem, index: int) -> str:
        """Generate a token like [EMAIL_a3f5b9]."""
        value_hash = hashlib.sha256(pii_item.value.encode()).hexdigest()[: self.hash_length]
        return f"[{pii_item.type.upper()}_{value_hash}]"


class CategoryRedactionStrategy(RedactionStrategy):
    """Category-based redaction: [EMAIL], [PHONE], etc.

    This strategy creates simple category tokens without distinguishing
    between multiple occurrences of the same type.
    """

    def generate_token(self, pii_item: PIIItem, index: int) -> str:
        """Generate a token like [EMAIL] or [PHONE]."""
        return f"[{pii_item.type.upper()}]"


class Redactor:
    """Handles text redaction using configurable strategies."""

    STRATEGIES: ClassVar[dict[str, type[RedactionStrategy]]] = {
        "token": TokenRedactionStrategy,
        "hash": HashRedactionStrategy,
        "category": CategoryRedactionStrategy,
    }

    def __init__(self, strategy: str = "token") -> None:
        """Initialize redactor with specified strategy.

        Args:
            strategy: Redaction strategy name ("token", "hash", or "category")

        Raises:
            ValueError: If strategy is not recognized
        """
        if strategy not in self.STRATEGIES:
            raise ValueError(
                f"Unknown redaction strategy: {strategy}. "
                f"Available: {list(self.STRATEGIES.keys())}"
            )
        self._strategy = self.STRATEGIES[strategy]()
        self._strategy_name = strategy

    @property
    def strategy_name(self) -> str:
        """Get the name of the current strategy."""
        return self._strategy_name

    def redact(
        self,
        text: str,
        pii_items: list[PIIItem],
    ) -> tuple[str, dict[str, str]]:
        """Redact PII items from text.

        Args:
            text: Original text containing PII
            pii_items: List of detected PII items (must be sorted by position)

        Returns:
            Tuple of (redacted_text, mapping_dict)
            mapping_dict maps tokens to original values
        """
        if not pii_items:
            return text, {}

        # Sort items by start position (descending) to replace from end
        sorted_items = sorted(pii_items, key=lambda x: x.start, reverse=True)

        # Track counts per type for token generation
        type_counts: dict[str, int] = {}
        for item in pii_items:
            type_counts[item.type] = type_counts.get(item.type, 0) + 1

        # Track current index per type (for forward iteration)
        type_indices: dict[str, int] = {t: 1 for t in type_counts}

        # Build mapping first (in forward order)
        mapping: dict[str, str] = {}
        for item in sorted(pii_items, key=lambda x: x.start):
            token = self._strategy.generate_token(item, type_indices[item.type])
            mapping[token] = item.value
            type_indices[item.type] += 1

        # Reset indices for actual redaction
        type_indices = {t: 1 for t in type_counts}

        # Process items in forward order to generate correct tokens
        # but apply replacements from end to preserve positions
        token_map: dict[int, str] = {}  # start position -> token
        for item in sorted(pii_items, key=lambda x: x.start):
            token = self._strategy.generate_token(item, type_indices[item.type])
            token_map[item.start] = token
            type_indices[item.type] += 1

        # Apply replacements from end to preserve positions
        redacted = text
        for item in sorted_items:
            token = token_map[item.start]
            redacted = redacted[: item.start] + token + redacted[item.end :]

        return redacted, mapping

    def restore(self, redacted_text: str, mapping: dict[str, str]) -> str:
        """Restore original text from redacted text using mapping.

        Args:
            redacted_text: Text with redaction tokens
            mapping: Dictionary mapping tokens to original values

        Returns:
            Restored original text
        """
        result = redacted_text
        for token, value in mapping.items():
            result = result.replace(token, value)
        return result
