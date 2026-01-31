"""PII pattern definitions for different regions and types."""

from gdpr_safe_rag.pii_detector.patterns.base import PIIPattern
from gdpr_safe_rag.pii_detector.patterns.common import (
    CreditCardPattern,
    EmailPattern,
    PhonePattern,
)
from gdpr_safe_rag.pii_detector.patterns.eu_patterns import IBANPattern
from gdpr_safe_rag.pii_detector.patterns.uk_patterns import (
    NINumberPattern,
    NHSNumberPattern,
    UKPostcodePattern,
)

__all__ = [
    "PIIPattern",
    "EmailPattern",
    "PhonePattern",
    "CreditCardPattern",
    "UKPostcodePattern",
    "NHSNumberPattern",
    "NINumberPattern",
    "IBANPattern",
]

# Registry of all available patterns by region
PATTERNS_BY_REGION: dict[str, list[type[PIIPattern]]] = {
    "UK": [
        EmailPattern,
        PhonePattern,
        CreditCardPattern,
        UKPostcodePattern,
        NHSNumberPattern,
        NINumberPattern,
        IBANPattern,
    ],
    "EU": [
        EmailPattern,
        PhonePattern,
        CreditCardPattern,
        IBANPattern,
    ],
    "COMMON": [
        EmailPattern,
        PhonePattern,
        CreditCardPattern,
    ],
}


def get_patterns_for_region(region: str) -> list[type[PIIPattern]]:
    """Get all pattern classes for a specific region.

    Args:
        region: Region code (UK, EU, COMMON)

    Returns:
        List of pattern classes for the region
    """
    return PATTERNS_BY_REGION.get(region.upper(), PATTERNS_BY_REGION["COMMON"])
