"""EU-specific PII patterns."""

import re

from gdpr_safe_rag.pii_detector.patterns.base import PIIPattern
from gdpr_safe_rag.pii_detector.validators import validate_iban


class IBANPattern(PIIPattern):
    """Pattern for detecting International Bank Account Numbers (IBAN).

    IBAN format:
    - 2 letter country code
    - 2 check digits
    - Up to 30 alphanumeric characters (BBAN)

    Example: GB82 WEST 1234 5698 7654 32
    """

    name = "iban"
    pattern = re.compile(
        r"\b[A-Z]{2}\d{2}[\s-]?(?:[A-Z0-9]{4}[\s-]?){2,7}[A-Z0-9]{1,4}\b",
        re.IGNORECASE,
    )
    priority = 7
    confidence = 0.85

    def validate(self, match: str) -> bool:
        """Validate IBAN using modulo 97 check."""
        return validate_iban(match)

    def get_confidence(self, match: str) -> float:
        """Higher confidence if modulo 97 validates."""
        if validate_iban(match):
            return 0.98
        return 0.3
