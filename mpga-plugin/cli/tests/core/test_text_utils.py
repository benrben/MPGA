"""Tests for mpga.core.text_utils :: truncate_string.

Coverage checklist for: truncate_string(s, max_len) -> str
──────────────────────────────────────────────────────────
Acceptance criteria → Test status
[x] AC1: max_len < 3 raises ValueError            → TestTruncateStringGuards::test_raises_for_max_len_below_3
[x] AC2: max_len == 3 (minimum valid)             → TestTruncateStringGuards::test_accepts_max_len_of_3
[x] AC3: empty string returns unchanged           → TestTruncateStringShortCircuit::test_returns_empty_string_unchanged
[x] AC4: string shorter than max_len returns unchanged
                                                  → TestTruncateStringShortCircuit::test_returns_string_shorter_than_limit_unchanged
[x] AC5: string exactly equal to max_len returns unchanged
                                                  → TestTruncateStringShortCircuit::test_returns_string_at_exact_limit_unchanged
[x] AC6: string longer than max_len is truncated with ellipsis
                                                  → TestTruncateStringTruncation::test_truncates_string_exceeding_limit
[x] AC7: off-by-one — string of length max_len+1  → TestTruncateStringTruncation::test_truncates_string_one_over_limit

Untested branches / edge cases:
- [ ] single-character string with max_len=3 (minimal valid truncation scenario)
- [ ] string containing unicode multi-byte characters (len() counts code points, not bytes)
- [ ] max_len exactly 3 truncating a longer string (result would be "...")

Evidence: [Unknown] src/mpga/core/text_utils.py — file does not exist yet (red phase)
"""

import pytest

from mpga.core.text_utils import truncate_string


# ---------------------------------------------------------------------------
# Guard conditions
# ---------------------------------------------------------------------------


class TestTruncateStringGuards:
    def test_raises_for_max_len_below_3(self):
        # Arrange
        s = "hello"
        max_len = 2

        # Act / Assert
        with pytest.raises(ValueError):
            truncate_string(s, max_len)

    def test_raises_for_max_len_of_zero(self):
        # Arrange
        s = "hello"
        max_len = 0

        # Act / Assert
        with pytest.raises(ValueError):
            truncate_string(s, max_len)

    def test_raises_for_negative_max_len(self):
        # Arrange
        s = "hello"
        max_len = -1

        # Act / Assert
        with pytest.raises(ValueError):
            truncate_string(s, max_len)

    def test_accepts_max_len_of_3(self):
        # Arrange — minimum legal value must not raise
        s = "hi"
        max_len = 3

        # Act
        result = truncate_string(s, max_len)

        # Assert — no exception, short string returned unchanged
        assert result == "hi"


# ---------------------------------------------------------------------------
# Short-circuit: strings that do not need truncation
# ---------------------------------------------------------------------------


class TestTruncateStringShortCircuit:
    def test_returns_empty_string_unchanged(self):
        # Arrange — degenerate: empty input
        s = ""
        max_len = 10

        # Act
        result = truncate_string(s, max_len)

        # Assert
        assert result == ""

    def test_returns_string_shorter_than_limit_unchanged(self):
        # Arrange
        s = "hello"
        max_len = 10

        # Act
        result = truncate_string(s, max_len)

        # Assert
        assert result == "hello"

    def test_returns_string_at_exact_limit_unchanged(self):
        # Arrange — boundary: len(s) == max_len must NOT truncate
        s = "hello"
        max_len = 5

        # Act
        result = truncate_string(s, max_len)

        # Assert
        assert result == "hello"


# ---------------------------------------------------------------------------
# Truncation: strings that exceed max_len
# ---------------------------------------------------------------------------


class TestTruncateStringTruncation:
    def test_truncates_string_exceeding_limit(self):
        # Arrange — typical case: long string
        s = "hello world"
        max_len = 8

        # Act
        result = truncate_string(s, max_len)

        # Assert — s[:5] + "..."
        assert result == "hello..."

    def test_truncates_string_one_over_limit(self):
        # Arrange — off-by-one: len(s) == max_len + 1
        s = "abcdef"
        max_len = 5

        # Act
        result = truncate_string(s, max_len)

        # Assert — s[:2] + "..."
        assert result == "ab..."

    def test_truncated_result_has_length_equal_to_max_len(self):
        # Arrange
        s = "the quick brown fox"
        max_len = 10

        # Act
        result = truncate_string(s, max_len)

        # Assert — output is exactly max_len characters
        assert len(result) == max_len
        assert result.endswith("...")
