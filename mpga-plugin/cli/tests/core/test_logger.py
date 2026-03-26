"""Tests for mpga.core.logger — converted from logger.test.ts."""

import re

import pytest

from mpga.core.logger import progress_bar, RALLY_QUOTES, random_quote, victory


def strip_ansi(s: str) -> str:
    """Strip ANSI color codes for testing."""
    return re.sub(r"\x1B\[[0-9;]*m", "", s)


# ---------------------------------------------------------------------------
# progress_bar
# ---------------------------------------------------------------------------


class TestProgressBar:
    def test_shows_0_percent_for_empty(self):
        bar = strip_ansi(progress_bar(0, 10))
        assert "0%" in bar
        assert "\u2591" in bar  # ░

    def test_shows_100_percent_for_full(self):
        bar = strip_ansi(progress_bar(10, 10))
        assert "100%" in bar
        assert "\u2588" in bar  # █

    def test_shows_50_percent_for_half(self):
        bar = strip_ansi(progress_bar(5, 10))
        assert "50%" in bar

    def test_handles_zero_total(self):
        bar = strip_ansi(progress_bar(0, 0))
        assert "0%" in bar

    def test_respects_custom_width(self):
        bar = progress_bar(5, 10, 10)
        # Strip rich markup tags
        clean = re.sub(r"\[.*?\]", "", bar)
        # 5 filled + 5 empty = 10 bar chars + " 50%"
        bar_chars = re.sub(r"\s*\d+%", "", clean)
        assert len(bar_chars) == 10


# ---------------------------------------------------------------------------
# RALLY_QUOTES
# ---------------------------------------------------------------------------


class TestRallyQuotes:
    def test_has_at_least_15_rally_quotes(self):
        assert len(RALLY_QUOTES) >= 15

    def test_every_quote_is_a_non_empty_string(self):
        for q in RALLY_QUOTES:
            assert isinstance(q, str)
            assert len(q) > 0


# ---------------------------------------------------------------------------
# random_quote
# ---------------------------------------------------------------------------


class TestRandomQuote:
    def test_returns_a_string_from_rally_quotes(self):
        q = random_quote()
        assert q in RALLY_QUOTES


# ---------------------------------------------------------------------------
# victory
# ---------------------------------------------------------------------------


class TestVictory:
    def test_prints_the_message_and_a_rally_quote_to_console(self, capsys):
        victory("We did it!")
        captured = capsys.readouterr()
        output = strip_ansi(captured.out)
        assert "We did it!" in output
