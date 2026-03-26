from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, Optional


# Discriminated type representing the verification status of an evidence link.
# - 'valid'      -- link target exists and matches
# - 'unknown'    -- unverified placeholder with a description
# - 'stale'      -- link target could not be found, tagged with a date
# - 'deprecated' -- link target is explicitly marked as deprecated
EvidenceLinkType = Literal["valid", "unknown", "stale", "deprecated"]

# Symbol kinds supported by evidence links
SymbolType = Literal["function", "class", "method", "variable", "type"]


@dataclass
class EvidenceLink:
    """Parsed representation of an evidence link extracted from markdown content.

    Evidence links tie prose claims to specific code locations.
    """

    # The original raw text of the evidence link as it appeared in the source
    raw: str
    # The verification status of this link
    type: EvidenceLinkType
    # Confidence score from 0 to 1 indicating trust in this link's accuracy
    confidence: float
    # Relative file path the link points to
    filepath: Optional[str] = None
    # Start line number of the referenced code range
    start_line: Optional[int] = None
    # End line number of the referenced code range
    end_line: Optional[int] = None
    # Symbol name (function, class, etc.) referenced by this link
    symbol: Optional[str] = None
    # The kind of symbol referenced
    symbol_type: Optional[SymbolType] = None
    # Human-readable description (used for 'unknown' type links)
    description: Optional[str] = None
    # ISO date string indicating when the link was marked stale
    stale_date: Optional[str] = None
    # ISO date string of the last successful verification
    last_verified: Optional[str] = None


# ---------------------------------------------------------------------------
# Patterns (legacy range-based):
#   [E] src/foo.ts:10-20 :: symbolName()
#   [E] src/foo.ts:10-20
#   [E] src/foo.ts :: symbolName
#   [Unknown] description
#   [Stale:2026-03-20] src/foo.ts:10-20
#   [Deprecated] src/foo.ts:10-20
# ---------------------------------------------------------------------------
EVIDENCE_RE = re.compile(r"\[E\]\s+(\S+?)(?::(\d+)-(\d+))?\s*(?:::\s*(.+))?$")
UNKNOWN_RE = re.compile(r"\[Unknown\]\s+(.+)$")
STALE_RE = re.compile(
    r"\[Stale:(\d{4}-\d{2}-\d{2})\]\s+(\S+?)(?::(\d+)-(\d+))?\s*(?:::\s*(.+))?$"
)
DEPRECATED_RE = re.compile(
    r"\[Deprecated\]\s+(\S+?)(?::(\d+)-(\d+))?\s*(?:::\s*(.+))?$"
)

# ---------------------------------------------------------------------------
# Patterns (symbol-based):
#   [E] src/foo.ts#symbolName:170 -- description
#   [E] src/foo.ts#symbolName:170
#   [E] src/foo.ts#symbolName -- description
#   [E] src/foo.ts#symbolName
#   [Stale:2026-03-20] src/foo.ts#symbolName:170
#   [Deprecated] src/foo.ts#symbolName:170
# ---------------------------------------------------------------------------
EVIDENCE_SYMBOL_RE = re.compile(
    r"\[E\]\s+(\S+?)#(\w+)(?::(\d+))?\s*(?:\u2014\s*(.+))?$"
)
STALE_SYMBOL_RE = re.compile(
    r"\[Stale:(\d{4}-\d{2}-\d{2})\]\s+(\S+?)#(\w+)(?::(\d+))?\s*(?:\u2014\s*(.+))?$"
)
DEPRECATED_SYMBOL_RE = re.compile(
    r"\[Deprecated\]\s+(\S+?)#(\w+)(?::(\d+))?\s*(?:\u2014\s*(.+))?$"
)


def _clean_parsed(s: str) -> str:
    """Strip markdown artifacts (backticks, trailing table pipes) from parsed values."""
    s = s.replace("`", "")
    s = re.sub(r"\s*\|?\s*$", "", s)
    return s.strip()


def parse_evidence_link(line: str) -> Optional[EvidenceLink]:
    """Parse a single line of text to extract an evidence link, if present.

    Supports ``[E]``, ``[Unknown]``, ``[Stale:DATE]``, and ``[Deprecated]`` link formats.

    Returns the parsed :class:`EvidenceLink`, or ``None`` if the line does not
    contain a recognised evidence link.
    """
    raw = line.strip()
    # Strip backticks (markdown artifacts) before regex matching
    line = raw.replace("`", "")

    # Try symbol-based patterns first (they contain '#' which is more specific)
    m = EVIDENCE_SYMBOL_RE.search(line)
    if m:
        return EvidenceLink(
            raw=raw,
            type="valid",
            filepath=_clean_parsed(m.group(1)),
            symbol=_clean_parsed(m.group(2)),
            start_line=int(m.group(3)) if m.group(3) else None,
            description=m.group(4).strip() if m.group(4) else None,
            confidence=1.0,
        )

    m = STALE_SYMBOL_RE.search(line)
    if m:
        return EvidenceLink(
            raw=raw,
            type="stale",
            stale_date=m.group(1),
            filepath=_clean_parsed(m.group(2)),
            symbol=_clean_parsed(m.group(3)),
            start_line=int(m.group(4)) if m.group(4) else None,
            description=m.group(5).strip() if m.group(5) else None,
            confidence=0,
        )

    m = DEPRECATED_SYMBOL_RE.search(line)
    if m:
        return EvidenceLink(
            raw=raw,
            type="deprecated",
            filepath=_clean_parsed(m.group(1)),
            symbol=_clean_parsed(m.group(2)),
            start_line=int(m.group(3)) if m.group(3) else None,
            description=m.group(4).strip() if m.group(4) else None,
            confidence=0.5,
        )

    # Legacy range-based patterns
    m = EVIDENCE_RE.search(line)
    if m:
        symbol_raw = _clean_parsed(m.group(4)) if m.group(4) else None
        # Strip trailing "()" from symbol names
        if symbol_raw:
            symbol_raw = re.sub(r"\(\)$", "", symbol_raw)
        return EvidenceLink(
            raw=raw,
            type="valid",
            filepath=_clean_parsed(m.group(1)),
            start_line=int(m.group(2)) if m.group(2) else None,
            end_line=int(m.group(3)) if m.group(3) else None,
            symbol=symbol_raw,
            confidence=1.0,
        )

    m = UNKNOWN_RE.search(line)
    if m:
        return EvidenceLink(
            raw=raw,
            type="unknown",
            description=m.group(1),
            confidence=0,
        )

    m = STALE_RE.search(line)
    if m:
        symbol_raw = _clean_parsed(m.group(5)) if m.group(5) else None
        if symbol_raw:
            symbol_raw = re.sub(r"\(\)$", "", symbol_raw)
        return EvidenceLink(
            raw=raw,
            type="stale",
            stale_date=m.group(1),
            filepath=_clean_parsed(m.group(2)),
            start_line=int(m.group(3)) if m.group(3) else None,
            end_line=int(m.group(4)) if m.group(4) else None,
            symbol=symbol_raw,
            confidence=0,
        )

    m = DEPRECATED_RE.search(line)
    if m:
        symbol_raw = _clean_parsed(m.group(4)) if m.group(4) else None
        if symbol_raw:
            symbol_raw = re.sub(r"\(\)$", "", symbol_raw)
        return EvidenceLink(
            raw=raw,
            type="deprecated",
            filepath=_clean_parsed(m.group(1)),
            start_line=int(m.group(2)) if m.group(2) else None,
            end_line=int(m.group(3)) if m.group(3) else None,
            symbol=symbol_raw,
            confidence=0.5,
        )

    return None


def parse_evidence_links(content: str) -> list[EvidenceLink]:
    """Parse all evidence links from a block of markdown content.

    Splits the content into lines and extracts any recognised evidence link from
    each line.
    """
    results: list[EvidenceLink] = []
    for line in content.split("\n"):
        link = parse_evidence_link(line)
        if link is not None:
            results.append(link)
    return results


def is_symbol_based(link: EvidenceLink) -> bool:
    """Determine whether a link should use the symbol-based format.

    Symbol-based format is used when a symbol is present and there is no
    end_line (i.e., it has a line hint, not a line range).
    """
    return bool(link.symbol) and link.end_line is None


def _format_symbol_ref(link: EvidenceLink) -> str:
    """Format the symbol-based portion: ``file#symbol:lineHint \u2014 description``."""
    s = f"{link.filepath}#{link.symbol}"
    if link.start_line:
        s += f":{link.start_line}"
    if link.description:
        s += f" \u2014 {link.description}"
    return s


def _format_range_ref(link: EvidenceLink) -> str:
    """Format the legacy range-based portion: ``file:start-end :: symbol()``."""
    s = f"{link.filepath}"
    if link.start_line and link.end_line:
        s += f":{link.start_line}-{link.end_line}"
    if link.symbol:
        s += f" :: {link.symbol}()"
    return s


def format_evidence_link(link: EvidenceLink) -> str:
    """Format an EvidenceLink back into its canonical string representation.

    Uses symbol-based format (``file#symbol:lineHint``) when a symbol is present
    without an end_line. Falls back to legacy range format
    (``file:start-end :: symbol()``) for links with both start_line and end_line.
    """
    if link.type == "unknown":
        return f"[Unknown] {link.description or ''}"

    use_symbol = is_symbol_based(link)
    ref = _format_symbol_ref(link) if use_symbol else _format_range_ref(link)

    if link.type == "stale":
        return f"[Stale:{link.stale_date}] {ref}"
    if link.type == "deprecated":
        return f"[Deprecated] {ref}"
    return f"[E] {ref}"


@dataclass
class EvidenceStats:
    """Aggregate statistics for a collection of evidence links."""

    total: int = 0
    valid: int = 0
    stale: int = 0
    unknown: int = 0
    deprecated: int = 0
    health_pct: int = 100


def evidence_stats(links: list[EvidenceLink]) -> EvidenceStats:
    """Compute aggregate statistics for a collection of evidence links.

    Counts links by type and calculates the overall health percentage.
    """
    total = len(links)
    valid = sum(1 for l in links if l.type == "valid")
    stale = sum(1 for l in links if l.type == "stale")
    unknown = sum(1 for l in links if l.type == "unknown")
    deprecated = sum(1 for l in links if l.type == "deprecated")
    health_pct = 100 if total == 0 else round((valid / total) * 100)
    return EvidenceStats(
        total=total,
        valid=valid,
        stale=stale,
        unknown=unknown,
        deprecated=deprecated,
        health_pct=health_pct,
    )
