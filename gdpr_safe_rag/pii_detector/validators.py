"""Validation functions for PII patterns (checksums, format validation, etc.)."""

import re


def validate_luhn(number: str) -> bool:
    """Validate a number using the Luhn algorithm (credit cards, etc.).

    Args:
        number: String of digits to validate

    Returns:
        True if the number passes Luhn validation
    """
    digits = re.sub(r"\D", "", number)
    if len(digits) < 13 or len(digits) > 19:
        return False

    total = 0
    for i, digit in enumerate(reversed(digits)):
        d = int(digit)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def validate_nhs_number(number: str) -> bool:
    """Validate NHS number using modulus 11 checksum.

    NHS numbers are 10 digits with a check digit calculated using
    weights 10, 9, 8, 7, 6, 5, 4, 3, 2 applied to the first 9 digits.

    Args:
        number: String containing the NHS number (may include spaces/dashes)

    Returns:
        True if the NHS number is valid
    """
    digits = re.sub(r"\D", "", number)
    if len(digits) != 10:
        return False

    # NHS numbers cannot start with 0
    if digits[0] == "0":
        return False

    weights = [10, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(d) * w for d, w in zip(digits[:9], weights))
    remainder = total % 11
    check_digit = 11 - remainder

    # If check digit is 11, it becomes 0
    if check_digit == 11:
        check_digit = 0

    # Check digit of 10 is invalid
    if check_digit == 10:
        return False

    return check_digit == int(digits[9])


def validate_iban(iban: str) -> bool:
    """Validate IBAN using modulo 97 check.

    Args:
        iban: String containing the IBAN

    Returns:
        True if the IBAN is valid
    """
    iban = iban.upper().replace(" ", "").replace("-", "")

    # Check minimum length and format
    if len(iban) < 15 or len(iban) > 34:
        return False

    # First two chars must be letters (country code)
    if not iban[:2].isalpha():
        return False

    # Next two must be digits (check digits)
    if not iban[2:4].isdigit():
        return False

    # Move first 4 chars to end
    rearranged = iban[4:] + iban[:4]

    # Convert letters to numbers (A=10, B=11, etc.)
    numeric = ""
    for char in rearranged:
        if char.isalpha():
            numeric += str(ord(char) - 55)
        else:
            numeric += char

    # Validate using modulo 97
    return int(numeric) % 97 == 1


def validate_ni_number(ni_number: str) -> bool:
    """Validate UK National Insurance number format.

    NI numbers consist of:
    - 2 prefix letters (excluding certain combinations)
    - 6 digits
    - 1 suffix letter (A, B, C, or D)

    Args:
        ni_number: String containing the NI number

    Returns:
        True if the NI number format is valid
    """
    # Remove spaces and dashes, convert to uppercase
    ni = re.sub(r"[\s-]", "", ni_number.upper())

    if len(ni) != 9:
        return False

    # Check format: 2 letters, 6 digits, 1 letter
    if not re.match(r"^[A-Z]{2}\d{6}[A-D]$", ni):
        return False

    # Invalid prefix combinations
    invalid_prefixes = {"BG", "GB", "NK", "KN", "TN", "NT", "ZZ"}
    prefix = ni[:2]
    if prefix in invalid_prefixes:
        return False

    # First letter cannot be D, F, I, Q, U, V
    if ni[0] in "DFIQUV":
        return False

    # Second letter cannot be D, F, I, O, Q, U, V
    if ni[1] in "DFIOQUV":
        return False

    return True


def validate_uk_postcode(postcode: str) -> bool:
    """Validate UK postcode format.

    Args:
        postcode: String containing the UK postcode

    Returns:
        True if the postcode format is valid
    """
    # Normalize: uppercase and single space
    postcode = " ".join(postcode.upper().split())

    # UK postcode regex pattern
    pattern = re.compile(
        r"^(GIR 0AA|"  # Special case: GIR 0AA
        r"[A-Z]{1,2}[0-9][0-9A-Z]? ?[0-9][A-Z]{2})$"  # Standard formats
    )

    return bool(pattern.match(postcode))
