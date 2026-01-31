"""Basic PII detection example.

This example demonstrates:
- Detecting PII in text
- Redacting PII with different strategies
- Processing documents for RAG ingestion
"""

from gdpr_safe_rag.pii_detector import PIIDetector


def main() -> None:
    # Sample text with various UK PII
    sample_text = """
    Dear Customer Service,

    My name is John Smith and I'm writing about my account.

    Contact details:
    - Email: john.smith@example.com
    - Phone: 07700 900123
    - Address: 10 Downing Street, London SW1A 2AA

    For verification, my NHS number is 123 456 7890 and my
    National Insurance number is AB123456C.

    My credit card ending in 4532 0123 4567 8901 was charged incorrectly.
    Please transfer the refund to my account:
    IBAN: GB82 WEST 1234 5698 7654 32

    Best regards,
    John Smith
    """

    print("=" * 60)
    print("GDPR Safe RAG - PII Detection Example")
    print("=" * 60)

    # Initialize detector with UK patterns
    detector = PIIDetector(region="UK", detection_level="strict")

    # Detect PII
    print("\n1. PII DETECTION")
    print("-" * 40)
    items = detector.detect(sample_text)

    print(f"Found {len(items)} PII items:\n")
    for item in items:
        print(f"  Type: {item.type}")
        print(f"  Value: {item.value}")
        print(f"  Position: {item.start}-{item.end}")
        print(f"  Confidence: {item.confidence:.2f}")
        print()

    # Redact with token strategy (default)
    print("\n2. REDACTION (Token Strategy)")
    print("-" * 40)
    result = detector.redact(sample_text)
    print("Redacted text:")
    print(result.redacted_text)
    print(f"\nRedaction mapping ({len(result.mapping)} items):")
    for token, value in result.mapping.items():
        print(f"  {token} -> {value}")

    # Demonstrate different redaction strategies
    print("\n3. REDACTION STRATEGIES")
    print("-" * 40)

    strategies = ["token", "hash", "category"]
    test_text = "Contact: john@example.com or 07700 900123"

    for strategy in strategies:
        detector_s = PIIDetector(region="UK", redaction_strategy=strategy)
        result_s = detector_s.redact(test_text)
        print(f"\n{strategy.upper()} strategy:")
        print(f"  {result_s.redacted_text}")

    # Process for RAG
    print("\n4. RAG PROCESSING")
    print("-" * 40)
    redacted, metadata = detector.process_for_rag(sample_text, document_id="doc-001")
    print("Metadata for audit logging:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")

    # Detection statistics
    print("\n5. DETECTION STATISTICS")
    print("-" * 40)
    result = detector.redact(sample_text)
    print(f"Original length: {result.stats['original_length']} chars")
    print(f"PII count: {result.stats['pii_count']}")
    print(f"PII coverage: {result.stats.get('pii_character_coverage', 0):.2%}")
    print(f"Average confidence: {result.stats.get('average_confidence', 0):.2f}")
    print(f"Type distribution: {result.stats.get('type_distribution', {})}")


if __name__ == "__main__":
    main()
