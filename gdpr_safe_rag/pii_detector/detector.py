"""Main PII Detector class."""

from typing import Any

from gdpr_safe_rag.config import DetectionLevel, get_settings
from gdpr_safe_rag.pii_detector.models import PIIItem, RedactionResult
from gdpr_safe_rag.pii_detector.patterns import PIIPattern, get_patterns_for_region
from gdpr_safe_rag.pii_detector.redactor import Redactor


class PIIDetector:
    """Main class for detecting and redacting PII in text.

    Supports multiple regions (UK, EU, COMMON) and configurable
    detection levels and redaction strategies.

    Example:
        >>> detector = PIIDetector(region="UK")
        >>> result = detector.redact("Contact john@example.com")
        >>> print(result.redacted_text)
        Contact [EMAIL_1]
    """

    # Confidence thresholds for detection levels
    CONFIDENCE_THRESHOLDS = {
        DetectionLevel.STRICT: 0.5,  # Include lower confidence matches
        DetectionLevel.MODERATE: 0.7,
        DetectionLevel.LENIENT: 0.9,  # Only high confidence matches
    }

    def __init__(
        self,
        region: str = "UK",
        detection_level: str | DetectionLevel = "strict",
        redaction_strategy: str = "token",
        custom_patterns: list[type[PIIPattern]] | None = None,
    ) -> None:
        """Initialize the PII detector.

        Args:
            region: Region for pattern selection (UK, EU, COMMON)
            detection_level: Sensitivity level (strict, moderate, lenient)
            redaction_strategy: Strategy for redaction (token, hash, category)
            custom_patterns: Additional pattern classes to use
        """
        self._region = region.upper()

        # Handle detection level
        if isinstance(detection_level, str):
            self._detection_level = DetectionLevel(detection_level.lower())
        else:
            self._detection_level = detection_level

        self._redactor = Redactor(redaction_strategy)

        # Initialize patterns
        pattern_classes = get_patterns_for_region(self._region)
        if custom_patterns:
            pattern_classes = list(pattern_classes) + list(custom_patterns)

        # Sort by priority (higher first)
        pattern_classes = sorted(pattern_classes, key=lambda p: p.priority, reverse=True)

        # Instantiate patterns
        self._patterns = [cls() for cls in pattern_classes]

    @property
    def region(self) -> str:
        """Get the configured region."""
        return self._region

    @property
    def detection_level(self) -> DetectionLevel:
        """Get the configured detection level."""
        return self._detection_level

    @property
    def patterns(self) -> list[PIIPattern]:
        """Get the list of active patterns."""
        return self._patterns

    def detect(self, text: str) -> list[PIIItem]:
        """Detect all PII in the given text.

        Args:
            text: Text to scan for PII

        Returns:
            List of PIIItem objects for each detected PII
        """
        if not text:
            return []

        items: list[PIIItem] = []
        confidence_threshold = self.CONFIDENCE_THRESHOLDS[self._detection_level]

        # Track covered ranges to avoid overlapping detections
        covered_ranges: set[tuple[int, int]] = set()

        for pattern in self._patterns:
            matches = pattern.find_all(text)

            for value, start, end in matches:
                # Skip if overlapping with existing detection
                if any(
                    not (end <= cstart or start >= cend) for cstart, cend in covered_ranges
                ):
                    continue

                # Validate the match
                if not pattern.validate(value):
                    continue

                # Get confidence score
                confidence = pattern.get_confidence(value)

                # Skip low confidence matches based on detection level
                if confidence < confidence_threshold:
                    continue

                item = PIIItem(
                    type=pattern.name,
                    value=value,
                    start=start,
                    end=end,
                    confidence=confidence,
                )
                items.append(item)
                covered_ranges.add((start, end))

        # Sort by position
        return sorted(items, key=lambda x: x.start)

    def redact(self, text: str) -> RedactionResult:
        """Detect and redact all PII in the given text.

        Args:
            text: Text to scan and redact

        Returns:
            RedactionResult with redacted text, items, and mapping
        """
        pii_items = self.detect(text)
        redacted_text, mapping = self._redactor.redact(text, pii_items)

        # Calculate stats
        stats = self._calculate_stats(text, pii_items)

        return RedactionResult(
            redacted_text=redacted_text,
            pii_items=pii_items,
            mapping=mapping,
            stats=stats,
        )

    def process_for_rag(
        self,
        document: str,
        document_id: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Process a document for RAG ingestion.

        This method is designed for RAG pipelines where you need both
        the redacted text for indexing and metadata for audit trails.

        Args:
            document: Document text to process
            document_id: Optional document identifier

        Returns:
            Tuple of (redacted_text, metadata_dict)
            metadata_dict contains detection info suitable for audit logging
        """
        result = self.redact(document)

        metadata: dict[str, Any] = {
            "pii_detected": result.pii_count > 0,
            "pii_count": result.pii_count,
            "pii_types": list(result.pii_types),
            "detection_level": self._detection_level.value,
            "region": self._region,
        }

        if document_id:
            metadata["document_id"] = document_id

        # Add type-specific counts
        type_counts: dict[str, int] = {}
        for item in result.pii_items:
            type_counts[item.type] = type_counts.get(item.type, 0) + 1
        metadata["pii_type_counts"] = type_counts

        return result.redacted_text, metadata

    def restore(self, redacted_text: str, mapping: dict[str, str]) -> str:
        """Restore original text from redacted text.

        Args:
            redacted_text: Text with redaction tokens
            mapping: Mapping dictionary from redact() call

        Returns:
            Restored original text
        """
        return self._redactor.restore(redacted_text, mapping)

    def _calculate_stats(self, original: str, items: list[PIIItem]) -> dict[str, Any]:
        """Calculate statistics about the detection.

        Args:
            original: Original text
            items: Detected PII items

        Returns:
            Dictionary of statistics
        """
        stats: dict[str, Any] = {
            "original_length": len(original),
            "pii_count": len(items),
            "patterns_used": len(self._patterns),
        }

        if items:
            # Character coverage
            pii_chars = sum(item.end - item.start for item in items)
            stats["pii_character_coverage"] = pii_chars / len(original) if original else 0

            # Average confidence
            stats["average_confidence"] = sum(item.confidence for item in items) / len(items)

            # Type distribution
            type_counts: dict[str, int] = {}
            for item in items:
                type_counts[item.type] = type_counts.get(item.type, 0) + 1
            stats["type_distribution"] = type_counts

        return stats
