"""AI compression pipeline — opt-in, falls back to heuristic."""

from __future__ import annotations

import logging
import re

from mpga.core.config import MpgaConfig

logger = logging.getLogger(__name__)

_COMPRESSED_TAG_RE = re.compile(r"<compressed>(.*?)</compressed>", re.DOTALL)


def _heuristic_compress(text: str) -> str:
    """Simple heuristic: keep first 3 non-empty lines, truncate to 500 chars."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return text[:500] if text else ""
    kept = "\n".join(lines[:3])
    return kept[:500]


def compress_with_llm(text: str, config: MpgaConfig) -> str:
    """Compress text using AI if enabled, otherwise fall back to heuristic.

    When ai_compression.enabled is False (the default), returns heuristic result
    immediately. When enabled, attempts the configured provider and falls back
    to heuristic on any error.
    """
    ai_cfg = config.memory.ai_compression

    if not ai_cfg.enabled:
        return _heuristic_compress(text)

    try:
        return _call_provider(text, ai_cfg.provider, ai_cfg.model)
    except Exception:
        logger.warning("AI compression failed, falling back to heuristic")
        return _heuristic_compress(text)


def _call_provider(text: str, provider: str, model: str) -> str:
    """Placeholder — will dispatch to real providers when implemented."""
    raise NotImplementedError(f"Provider '{provider}' is not yet implemented")


def parse_xml_response(raw: str) -> str:
    """Extract content from <compressed>...</compressed> tags, or return raw."""
    match = _COMPRESSED_TAG_RE.search(raw)
    if match:
        return match.group(1)
    return raw
