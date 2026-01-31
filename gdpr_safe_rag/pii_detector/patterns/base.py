"""Abstract base class for PII patterns."""

import re
from abc import ABC, abstractmethod
from typing import ClassVar


class PIIPattern(ABC):
    """Abstract base class for PII detection patterns.

    Subclasses must define:
        - name: Unique identifier for the pattern type
        - pattern: Compiled regex pattern for detection
        - priority: Higher priority patterns are matched first (default 0)

    Subclasses may override:
        - validate(): Additional validation beyond regex matching
        - confidence: Base confidence score for matches (default 1.0)
    """

    name: ClassVar[str]
    pattern: ClassVar[re.Pattern[str]]
    priority: ClassVar[int] = 0
    confidence: ClassVar[float] = 1.0

    @abstractmethod
    def validate(self, match: str) -> bool:
        """Validate a regex match with additional logic (checksums, etc.).

        Args:
            match: The string that matched the regex pattern

        Returns:
            True if the match is a valid instance of this PII type
        """
        ...

    def get_confidence(self, match: str) -> float:
        """Get confidence score for a match.

        Override this method to implement dynamic confidence scoring.

        Args:
            match: The matched string

        Returns:
            Confidence score between 0.0 and 1.0
        """
        return self.confidence

    @classmethod
    def find_all(cls, text: str) -> list[tuple[str, int, int]]:
        """Find all matches of this pattern in text.

        Args:
            text: The text to search

        Returns:
            List of tuples (matched_value, start_position, end_position)
        """
        matches = []
        for match in cls.pattern.finditer(text):
            matches.append((match.group(), match.start(), match.end()))
        return matches
