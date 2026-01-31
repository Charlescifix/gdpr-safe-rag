"""UK-specific PII patterns with validation."""

import re

from gdpr_safe_rag.pii_detector.patterns.base import PIIPattern
from gdpr_safe_rag.pii_detector.validators import (
    validate_nhs_number,
    validate_ni_number,
    validate_uk_postcode,
)


class UKPostcodePattern(PIIPattern):
    """Pattern for detecting UK postcodes.

    Handles all valid UK postcode formats including:
    - GIR 0AA (special case)
    - A9 9AA, A99 9AA (single letter area)
    - AA9 9AA, AA99 9AA (two letter area)
    - A9A 9AA (single letter area with letter in district)
    - AA9A 9AA (two letter area with letter in district)
    """

    name = "uk_postcode"
    pattern = re.compile(
        r"\b"
        r"(?:"
        # GIR 0AA (special postcode)
        r"GIR\s?0AA|"
        # Standard formats
        r"(?:"
        # Area: 1-2 letters
        r"[A-Z]{1,2}"
        # District: digit(s) optionally followed by letter
        r"[0-9][0-9A-Z]?"
        r")"
        # Space (optional)
        r"\s?"
        # Sector and unit: digit + 2 letters
        r"[0-9][A-Z]{2}"
        r")"
        r"\b",
        re.IGNORECASE,
    )
    priority = 8
    confidence = 0.9

    def validate(self, match: str) -> bool:
        """Validate UK postcode format."""
        return validate_uk_postcode(match)


class NHSNumberPattern(PIIPattern):
    """Pattern for detecting NHS numbers.

    NHS numbers are 10-digit numbers with a checksum.
    They may be formatted with spaces or dashes (e.g., 123 456 7890).
    """

    name = "nhs_number"
    pattern = re.compile(
        r"\b[1-9]\d{2}[\s-]?\d{3}[\s-]?\d{4}\b",
    )
    priority = 9
    confidence = 0.85

    def validate(self, match: str) -> bool:
        """Validate NHS number using modulus 11 checksum."""
        return validate_nhs_number(match)

    def get_confidence(self, match: str) -> float:
        """Higher confidence if checksum validates."""
        if validate_nhs_number(match):
            return 0.98
        return 0.3


class NINumberPattern(PIIPattern):
    """Pattern for detecting UK National Insurance numbers.

    Format: 2 letters + 6 digits + 1 letter (A-D)
    Example: AB123456C

    Invalid prefix combinations are excluded:
    BG, GB, NK, KN, TN, NT, ZZ
    """

    name = "ni_number"
    pattern = re.compile(
        r"\b"
        r"(?![DFIQUV])"  # First letter not D, F, I, Q, U, V
        r"(?![A-Z][DFIOQUV])"  # Second letter not D, F, I, O, Q, U, V
        r"(?!BG|GB|NK|KN|TN|NT|ZZ)"  # Invalid prefixes
        r"[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z]"  # Valid prefix letters
        r"[\s-]?"
        r"\d{2}[\s-]?\d{2}[\s-]?\d{2}"
        r"[\s-]?"
        r"[A-D]"
        r"\b",
        re.IGNORECASE,
    )
    priority = 9
    confidence = 0.9

    def validate(self, match: str) -> bool:
        """Validate NI number format."""
        return validate_ni_number(match)
