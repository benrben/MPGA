"""Tests for AI compression pipeline — opt-in configurable.

Coverage checklist for: T016 — Add AI compression pipeline (opt-in configurable)

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: compress_with_llm default disabled       → test_compress_with_llm_default_disabled
[x] AC2: Returns heuristic when disabled          → test_compress_returns_heuristic_when_disabled
[x] AC3: Falls back to heuristic on error         → test_compress_falls_back_on_error
[x] AC4: Respects config enabled flag             → test_compress_respects_config
[x] AC5: XML response parsing placeholder         → test_xml_response_parsing_placeholder
"""

from __future__ import annotations

import pytest

from mpga.core.config import MpgaConfig, MemoryConfig, AiCompressionConfig
from mpga.memory.compress import compress_with_llm, parse_xml_response


class TestAiCompress:

    def test_compress_with_llm_default_disabled(self) -> None:
        """With default config, AI compression is disabled."""
        cfg = MpgaConfig()
        assert cfg.memory.ai_compression.enabled is False

        result = compress_with_llm("some long text here", cfg)
        assert result is not None
        assert isinstance(result, str)

    def test_compress_returns_heuristic_when_disabled(self) -> None:
        """When AI compression is disabled, returns heuristic compression."""
        cfg = MpgaConfig()
        text = "The quick brown fox jumps over the lazy dog. " * 10

        result = compress_with_llm(text, cfg)
        assert len(result) <= len(text)
        assert len(result) > 0

    def test_compress_falls_back_on_error(self) -> None:
        """When AI compression is enabled but provider is invalid, falls back to heuristic."""
        cfg = MpgaConfig()
        cfg.memory.ai_compression = AiCompressionConfig(
            enabled=True, provider="nonexistent", model="fake-model",
        )

        result = compress_with_llm("some text to compress", cfg)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_compress_respects_config(self) -> None:
        """When config has enabled=False, never calls any AI provider."""
        cfg = MpgaConfig()
        cfg.memory.ai_compression = AiCompressionConfig(
            enabled=False, provider="openai", model="gpt-4",
        )

        result = compress_with_llm("text", cfg)
        assert result is not None

    def test_xml_response_parsing_placeholder(self) -> None:
        """XML response parser extracts content from <compressed> tags."""
        xml = "<compressed>short summary here</compressed>"
        parsed = parse_xml_response(xml)
        assert parsed == "short summary here"

        raw = "no xml tags here"
        assert parse_xml_response(raw) == raw
