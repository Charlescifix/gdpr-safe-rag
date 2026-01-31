"""Common PII patterns (email, phone, credit card) used across regions."""

import re

from gdpr_safe_rag.pii_detector.patterns.base import PIIPattern
from gdpr_safe_rag.pii_detector.validators import validate_luhn


class EmailPattern(PIIPattern):
    """Pattern for detecting email addresses.

    Uses a practical pattern that covers most valid email formats
    while avoiding excessive false positives.
    """

    name = "email"
    pattern = re.compile(
        r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        re.IGNORECASE,
    )
    priority = 10
    confidence = 0.95

    def validate(self, match: str) -> bool:
        """Validate email format.

        Basic validation - the regex already handles most cases.
        """
        # Check for consecutive dots in local part
        local_part = match.split("@")[0]
        if ".." in local_part:
            return False

        # Check domain has at least one dot
        domain = match.split("@")[1]
        if "." not in domain:
            return False

        return True


class CreditCardPattern(PIIPattern):
    """Pattern for detecting credit card numbers.

    Detects common credit card formats (Visa, MasterCard, Amex, etc.)
    and validates using the Luhn algorithm.
    """

    name = "credit_card"
    pattern = re.compile(
        r"\b(?:\d[ -]*?){13,19}\b",
    )
    priority = 5
    confidence = 0.9

    def validate(self, match: str) -> bool:
        """Validate credit card using Luhn algorithm."""
        return validate_luhn(match)

    def get_confidence(self, match: str) -> float:
        """Higher confidence if Luhn validates."""
        if validate_luhn(match):
            return 0.95
        return 0.3  # Low confidence if Luhn fails but pattern matches


class PhonePattern(PIIPattern):
    """Pattern for detecting phone numbers.

    Supports various formats including:
    - International format with country code
    - UK mobile and landline numbers
    - Numbers with spaces, dashes, or dots as separators
    """

    name = "phone"
    pattern = re.compile(
        r"\b(?:"
        # International format with +
        r"\+?[1-9]\d{0,2}[\s.-]?"
        # Main number groups
        r"(?:\(?\d{2,4}\)?[\s.-]?)?"
        r"\d{3,4}[\s.-]?"
        r"\d{3,4}"
        r")\b",
    )
    priority = 3
    confidence = 0.7  # Lower base confidence due to potential false positives

    def validate(self, match: str) -> bool:
        """Validate phone number format."""
        # Extract just digits
        digits = re.sub(r"\D", "", match)

        # Phone numbers should be between 7 and 15 digits
        if len(digits) < 7 or len(digits) > 15:
            return False

        # Avoid matching things like years or other numbers
        # A phone number shouldn't be just 4 digits (like a year)
        if len(digits) <= 4:
            return False

        return True

    def get_confidence(self, match: str) -> float:
        """Adjust confidence based on format indicators."""
        # Higher confidence for numbers with country codes
        if match.startswith("+"):
            return 0.9

        # Higher confidence for formatted numbers
        if re.search(r"[\s.-]", match):
            return 0.8

        digits = re.sub(r"\D", "", match)

        # UK mobile numbers (starting with 07)
        if digits.startswith("07") and len(digits) == 11:
            return 0.9

        # UK landlines (starting with 01 or 02)
        if digits.startswith(("01", "02")) and len(digits) in (10, 11):
            return 0.85

        return self.confidence
