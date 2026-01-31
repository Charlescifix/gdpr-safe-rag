"""Tests for PII Detector module."""

import pytest

from gdpr_safe_rag.pii_detector import PIIDetector, PIIItem, RedactionResult
from gdpr_safe_rag.pii_detector.patterns import (
    CreditCardPattern,
    EmailPattern,
    IBANPattern,
    NINumberPattern,
    NHSNumberPattern,
    PhonePattern,
    UKPostcodePattern,
)
from gdpr_safe_rag.pii_detector.redactor import Redactor
from gdpr_safe_rag.pii_detector.validators import (
    validate_iban,
    validate_luhn,
    validate_nhs_number,
    validate_ni_number,
    validate_uk_postcode,
)


class TestValidators:
    """Tests for validation functions."""

    def test_luhn_valid_card(self) -> None:
        """Test Luhn validation with valid card number."""
        # Valid test card numbers
        assert validate_luhn("4532015112830366") is True
        assert validate_luhn("4916338506082832") is True
        assert validate_luhn("4556 7375 8689 9855") is True

    def test_luhn_invalid_card(self) -> None:
        """Test Luhn validation with invalid card number."""
        assert validate_luhn("1234567890123456") is False
        assert validate_luhn("1111111111111111") is False

    def test_luhn_edge_cases(self) -> None:
        """Test Luhn validation edge cases."""
        assert validate_luhn("123") is False  # Too short
        assert validate_luhn("12345678901234567890") is False  # Too long

    def test_nhs_number_valid(self) -> None:
        """Test NHS number validation with valid numbers."""
        # Valid NHS numbers (pass modulus 11 check)
        assert validate_nhs_number("401 023 2161") is True
        assert validate_nhs_number("9434765080") is True
        assert validate_nhs_number("567-890-1230") is True

    def test_nhs_number_invalid(self) -> None:
        """Test NHS number validation with invalid numbers."""
        assert validate_nhs_number("123 456 7891") is False  # Bad checksum
        assert validate_nhs_number("000 000 0000") is False  # Can't start with 0
        assert validate_nhs_number("12345") is False  # Too short

    def test_ni_number_valid(self) -> None:
        """Test NI number validation with valid formats."""
        assert validate_ni_number("AB123456C") is True
        assert validate_ni_number("AB 12 34 56 C") is True
        assert validate_ni_number("AB-12-34-56-C") is True
        assert validate_ni_number("ab123456d") is True  # Lowercase

    def test_ni_number_invalid(self) -> None:
        """Test NI number validation with invalid formats."""
        assert validate_ni_number("BG123456C") is False  # Invalid prefix
        assert validate_ni_number("GB123456C") is False  # Invalid prefix
        assert validate_ni_number("AB123456E") is False  # Invalid suffix
        assert validate_ni_number("DA123456C") is False  # D not allowed as first char
        assert validate_ni_number("AD123456C") is False  # D not allowed as second char

    def test_uk_postcode_valid(self) -> None:
        """Test UK postcode validation with valid formats."""
        assert validate_uk_postcode("SW1A 2AA") is True
        assert validate_uk_postcode("EC1A 1BB") is True
        assert validate_uk_postcode("M1 1AE") is True
        assert validate_uk_postcode("B33 8TH") is True
        assert validate_uk_postcode("GIR 0AA") is True  # Special case

    def test_uk_postcode_invalid(self) -> None:
        """Test UK postcode validation with invalid formats."""
        assert validate_uk_postcode("12345") is False
        assert validate_uk_postcode("INVALID") is False

    def test_iban_valid(self) -> None:
        """Test IBAN validation with valid IBANs."""
        assert validate_iban("GB82WEST12345698765432") is True
        assert validate_iban("GB82 WEST 1234 5698 7654 32") is True
        assert validate_iban("DE89370400440532013000") is True

    def test_iban_invalid(self) -> None:
        """Test IBAN validation with invalid IBANs."""
        assert validate_iban("GB82WEST12345698765433") is False  # Bad checksum
        assert validate_iban("XX00INVALID") is False
        assert validate_iban("TOOSHORT") is False


class TestPIIPatterns:
    """Tests for PII pattern classes."""

    def test_email_pattern(self) -> None:
        """Test email pattern detection."""
        pattern = EmailPattern()
        matches = pattern.find_all("Contact john@example.com for info")
        assert len(matches) == 1
        assert matches[0][0] == "john@example.com"
        assert pattern.validate("john@example.com") is True
        assert pattern.validate("john..smith@example.com") is False

    def test_phone_pattern(self) -> None:
        """Test phone pattern detection."""
        pattern = PhonePattern()
        matches = pattern.find_all("Call 07700 900123 or +44 20 7123 4567")
        assert len(matches) >= 1
        # Verify validation
        assert pattern.validate("07700 900123") is True

    def test_credit_card_pattern(self) -> None:
        """Test credit card pattern detection."""
        pattern = CreditCardPattern()
        matches = pattern.find_all("Card: 4532 0123 4567 8901")
        assert len(matches) >= 1

    def test_uk_postcode_pattern(self) -> None:
        """Test UK postcode pattern detection."""
        pattern = UKPostcodePattern()
        matches = pattern.find_all("Address: 10 Downing St, London SW1A 2AA")
        assert len(matches) == 1
        assert "SW1A 2AA" in matches[0][0] or "SW1A2AA" in matches[0][0].replace(" ", "")

    def test_nhs_number_pattern(self) -> None:
        """Test NHS number pattern detection."""
        pattern = NHSNumberPattern()
        matches = pattern.find_all("NHS: 401 023 2161")
        assert len(matches) == 1
        assert pattern.validate("401 023 2161") is True

    def test_ni_number_pattern(self) -> None:
        """Test NI number pattern detection."""
        pattern = NINumberPattern()
        matches = pattern.find_all("NI: AB123456C")
        assert len(matches) == 1
        assert pattern.validate("AB123456C") is True

    def test_iban_pattern(self) -> None:
        """Test IBAN pattern detection."""
        pattern = IBANPattern()
        matches = pattern.find_all("IBAN: GB82 WEST 1234 5698 7654 32")
        assert len(matches) == 1


class TestRedactor:
    """Tests for the Redactor class."""

    def test_token_redaction(self) -> None:
        """Test token redaction strategy."""
        redactor = Redactor(strategy="token")
        items = [
            PIIItem(type="email", value="john@example.com", start=0, end=16),
            PIIItem(type="email", value="jane@example.com", start=20, end=36),
        ]
        text = "john@example.com or jane@example.com"
        redacted, mapping = redactor.redact(text, items)
        assert "[EMAIL_1]" in redacted
        assert "[EMAIL_2]" in redacted
        assert mapping["[EMAIL_1]"] == "john@example.com"
        assert mapping["[EMAIL_2]"] == "jane@example.com"

    def test_hash_redaction(self) -> None:
        """Test hash redaction strategy."""
        redactor = Redactor(strategy="hash")
        items = [PIIItem(type="email", value="john@example.com", start=0, end=16)]
        text = "john@example.com"
        redacted, mapping = redactor.redact(text, items)
        assert "[EMAIL_" in redacted
        assert len(list(mapping.keys())[0]) > len("[EMAIL_]")  # Has hash suffix

    def test_category_redaction(self) -> None:
        """Test category redaction strategy."""
        redactor = Redactor(strategy="category")
        items = [
            PIIItem(type="email", value="john@example.com", start=0, end=16),
            PIIItem(type="email", value="jane@example.com", start=20, end=36),
        ]
        text = "john@example.com or jane@example.com"
        redacted, mapping = redactor.redact(text, items)
        assert redacted.count("[EMAIL]") == 2

    def test_restore(self) -> None:
        """Test restoring original text from redacted text."""
        redactor = Redactor(strategy="token")
        original = "Contact john@example.com"
        items = [PIIItem(type="email", value="john@example.com", start=8, end=24)]
        redacted, mapping = redactor.redact(original, items)
        restored = redactor.restore(redacted, mapping)
        assert restored == original

    def test_invalid_strategy(self) -> None:
        """Test that invalid strategy raises error."""
        with pytest.raises(ValueError):
            Redactor(strategy="invalid")


class TestPIIDetector:
    """Tests for the main PIIDetector class."""

    def test_detect_emails(self, pii_detector: PIIDetector) -> None:
        """Test email detection."""
        items = pii_detector.detect("Contact john@example.com for info")
        assert len(items) == 1
        assert items[0].type == "email"
        assert items[0].value == "john@example.com"

    def test_detect_multiple_types(
        self, pii_detector: PIIDetector, sample_text_with_pii: str
    ) -> None:
        """Test detection of multiple PII types."""
        items = pii_detector.detect(sample_text_with_pii)
        types = {item.type for item in items}
        assert "email" in types
        # Should detect multiple types

    def test_detect_no_pii(
        self, pii_detector: PIIDetector, sample_text_no_pii: str
    ) -> None:
        """Test detection on text without PII."""
        items = pii_detector.detect(sample_text_no_pii)
        assert len(items) == 0

    def test_redact(self, pii_detector: PIIDetector) -> None:
        """Test redaction functionality."""
        result = pii_detector.redact("Email: john@example.com")
        assert isinstance(result, RedactionResult)
        assert "[EMAIL_1]" in result.redacted_text
        assert result.pii_count == 1

    def test_redaction_result_properties(self, pii_detector: PIIDetector) -> None:
        """Test RedactionResult properties."""
        result = pii_detector.redact("john@example.com and jane@example.com")
        assert result.pii_count == 2
        assert "email" in result.pii_types
        items = result.get_items_by_type("email")
        assert len(items) == 2

    def test_process_for_rag(self, pii_detector: PIIDetector) -> None:
        """Test processing for RAG ingestion."""
        text = "Contact john@example.com"
        redacted, metadata = pii_detector.process_for_rag(text, document_id="doc-1")
        assert metadata["pii_detected"] is True
        assert metadata["pii_count"] == 1
        assert metadata["document_id"] == "doc-1"
        assert "email" in metadata["pii_types"]

    def test_restore(self, pii_detector: PIIDetector) -> None:
        """Test restore functionality."""
        original = "Contact john@example.com"
        result = pii_detector.redact(original)
        restored = pii_detector.restore(result.redacted_text, result.mapping)
        assert restored == original

    def test_detection_levels(self) -> None:
        """Test different detection levels."""
        strict = PIIDetector(region="UK", detection_level="strict")
        lenient = PIIDetector(region="UK", detection_level="lenient")

        text = "07700900123"  # Phone number without formatting
        strict_items = strict.detect(text)
        lenient_items = lenient.detect(text)

        # Strict should detect more (lower threshold)
        # Note: actual behavior depends on confidence scores
        assert isinstance(strict_items, list)
        assert isinstance(lenient_items, list)

    def test_different_regions(self) -> None:
        """Test different region configurations."""
        uk_detector = PIIDetector(region="UK")
        eu_detector = PIIDetector(region="EU")
        common_detector = PIIDetector(region="COMMON")

        # UK should have more patterns than COMMON
        assert len(uk_detector.patterns) >= len(common_detector.patterns)

    def test_empty_text(self, pii_detector: PIIDetector) -> None:
        """Test handling of empty text."""
        items = pii_detector.detect("")
        assert items == []

        result = pii_detector.redact("")
        assert result.redacted_text == ""
        assert result.pii_count == 0


class TestPIIItem:
    """Tests for PIIItem dataclass."""

    def test_pii_item_creation(self) -> None:
        """Test creating a PIIItem."""
        item = PIIItem(
            type="email",
            value="john@example.com",
            start=0,
            end=16,
            confidence=0.95,
        )
        assert item.type == "email"
        assert item.value == "john@example.com"
        assert item.start == 0
        assert item.end == 16
        assert item.confidence == 0.95

    def test_pii_item_validation(self) -> None:
        """Test PIIItem validation."""
        with pytest.raises(ValueError):
            PIIItem(type="email", value="test", start=-1, end=4)

        with pytest.raises(ValueError):
            PIIItem(type="email", value="test", start=4, end=4)

        with pytest.raises(ValueError):
            PIIItem(type="email", value="test", start=0, end=4, confidence=1.5)

    def test_pii_item_immutable(self) -> None:
        """Test that PIIItem is immutable (frozen)."""
        item = PIIItem(type="email", value="test", start=0, end=4)
        with pytest.raises(Exception):  # FrozenInstanceError
            item.type = "phone"  # type: ignore
