from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

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
    filepath: str | None = None
    # Start line number of the referenced code range
    start_line: int | None = None
    # End line number of the referenced code range
    end_line: int | None = None
    # Symbol name (function, class, etc.) referenced by this link
    symbol: str | None = None
    # The kind of symbol referenced
    symbol_type: SymbolType | None = None
    # Human-readable description (used for 'unknown' type links)
    description: str | None = None
    # ISO date string indicating when the link was marked stale
    stale_date: str | None = None
    # ISO date string of the last successful verification
    last_verified: str | None = None


# ---------------------------------------------------------------------------
# Patterns (legacy range-based):
#   [E] src/foo.ts:10-20 :: symbolName()
#   [E] src/foo.ts:10-20
#   [E] src/foo.ts :: symbolName
#   [Unknown] description
#   [Stale:2026-03-20] src/foo.ts:10-20
#   [Deprecated] src/foo.ts:10-20
# ---------------------------------------------------------------------------
# Marker regex: matches the opening bracket of any evidence marker type
MARKER_RE = re.compile(r"\[(E|Unknown|Stale:\d{4}-\d{2}-\d{2}|Deprecated)\]")

# ---------------------------------------------------------------------------
# Token-based multi-link extraction helpers.
# Each evidence link consists of a marker followed by a single non-space token
# (the filepath, optionally with :N-N range or #symbol:hint appended).
# The optional ":: symbol" suffix is captured separately.
# ---------------------------------------------------------------------------

# Parses a raw link token of the form:
#   filepath:start-end       → groups (filepath, start, end, None, None)
#   filepath:start           → groups (filepath, start, None, None, None)
#   filepath#symbol:hint     → groups (filepath, None, None, symbol, hint)
#   filepath#symbol          → groups (filepath, None, None, symbol, None)
#   filepath                 → groups (filepath, None, None, None, None)
_TOKEN_RE = re.compile(
    r"^(\S+?)(?:#(\w+)(?::(\d+))?|(?::(\d+)(?:-(\d+))?))?$"
)


def _parse_link_token(token: str) -> tuple[str, int | None, int | None, str | None]:
    """Parse a raw link token into (filepath, start_line, end_line, symbol)."""
    token = _clean_parsed(token)
    # Strip trailing prose punctuation that leaks from sentences (e.g. "see [E] file.ts:10-20;")
    token = re.sub(r"[;,)]+$", "", token)
    m = _TOKEN_RE.match(token)
    if not m:
        return token, None, None, None
    filepath = _clean_parsed(m.group(1))
    symbol = m.group(2)
    if symbol:
        hint = int(m.group(3)) if m.group(3) else None
        return filepath, hint, None, symbol
    start = int(m.group(4)) if m.group(4) else None
    end = int(m.group(5)) if m.group(5) else None
    if start is not None and end is None:
        end = start
    return filepath, start, end, None

EVIDENCE_RE = re.compile(r"\[E\]\s+(\S+?)(?::(\d+)(?:-(\d+))?)?\s*(?:::\s*(.+))?$")
UNKNOWN_RE = re.compile(r"\[Unknown\]\s+(.+)$")
STALE_RE = re.compile(
    r"\[Stale:(\d{4}-\d{2}-\d{2})\]\s+(\S+?)(?::(\d+)(?:-(\d+))?)?\s*(?:::\s*(.+))?$"
)
DEPRECATED_RE = re.compile(
    r"\[Deprecated\]\s+(\S+?)(?::(\d+)(?:-(\d+))?)?\s*(?:::\s*(.+))?$"
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


def parse_evidence_link(line: str) -> EvidenceLink | None:
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
        start_line = int(m.group(2)) if m.group(2) else None
        end_line = int(m.group(3)) if m.group(3) else None
        # Single-line anchor: [E] file:42 → start=42, end=42
        if start_line is not None and end_line is None:
            end_line = start_line
        return EvidenceLink(
            raw=raw,
            type="valid",
            filepath=_clean_parsed(m.group(1)),
            start_line=start_line,
            end_line=end_line,
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
        start_line = int(m.group(3)) if m.group(3) else None
        end_line = int(m.group(4)) if m.group(4) else None
        if start_line is not None and end_line is None:
            end_line = start_line
        return EvidenceLink(
            raw=raw,
            type="stale",
            stale_date=m.group(1),
            filepath=_clean_parsed(m.group(2)),
            start_line=start_line,
            end_line=end_line,
            symbol=symbol_raw,
            confidence=0,
        )

    m = DEPRECATED_RE.search(line)
    if m:
        symbol_raw = _clean_parsed(m.group(4)) if m.group(4) else None
        if symbol_raw:
            symbol_raw = re.sub(r"\(\)$", "", symbol_raw)
        start_line = int(m.group(2)) if m.group(2) else None
        end_line = int(m.group(3)) if m.group(3) else None
        if start_line is not None and end_line is None:
            end_line = start_line
        return EvidenceLink(
            raw=raw,
            type="deprecated",
            filepath=_clean_parsed(m.group(1)),
            start_line=start_line,
            end_line=end_line,
            symbol=symbol_raw,
            confidence=0.5,
        )

    return None


def parse_evidence_links_on_line(line: str) -> list[EvidenceLink]:
    """Extract all evidence links from a single line (may contain multiple markers).

    Finds every ``[E]``, ``[Unknown]``, ``[Stale:DATE]``, or ``[Deprecated]``
    marker on the line using token-based parsing: each marker is followed by a
    single non-space token representing the link target.
    """
    # Strip backticks (markdown artifacts) before matching
    clean = line.replace("`", "")
    results: list[EvidenceLink] = []

    for m in re.finditer(MARKER_RE, clean):
        marker_text = m.group(0)  # e.g. "[E]" or "[Unknown]" or "[Stale:2026-01-01]"
        pos_after_marker = m.end()

        # Skip whitespace after marker
        rest = clean[pos_after_marker:]
        if not rest.lstrip():
            continue
        stripped = rest.lstrip()

        if marker_text == "[E]":
            # Read first non-space token, then optional ":: symbol" suffix
            token_m = re.match(r"(\S+)(?:\s*::\s*(\S+?)(?:\(\))?)?(?=\s|$)", stripped)
            if not token_m:
                continue
            token = token_m.group(1)
            inline_symbol = _clean_parsed(token_m.group(2)) if token_m.group(2) else None
            # Check for em dash description after the token match
            rest_after = stripped[token_m.end():]
            em_m = re.match(r"\s*\u2014\s*(.+?)(?=\s*\[(?:E\]|Unknown\]|Stale:|Deprecated\])|$)", rest_after)
            inline_desc = em_m.group(1).strip() if em_m else None
            raw_text = f"{marker_text} {token_m.group(0).strip()}"
            filepath, start_line, end_line, token_symbol = _parse_link_token(token)
            # Prefer inline_symbol from ":: sym" over token-embedded symbol
            symbol = token_symbol or inline_symbol
            # If there's an inline symbol override, use it
            if inline_symbol:
                symbol = inline_symbol
            results.append(EvidenceLink(
                raw=raw_text,
                type="valid",
                filepath=filepath,
                start_line=start_line,
                end_line=end_line,
                symbol=symbol,
                description=inline_desc,
                confidence=1.0,
            ))

        elif marker_text.startswith("[Unknown]"):
            # [Unknown] description text until next marker or end of line
            next_marker = re.search(r"\[(?:E\]|Unknown\]|Stale:\d{4}-\d{2}-\d{2}\]|Deprecated\])", stripped)
            desc_text = stripped[:next_marker.start()].strip() if next_marker else stripped.strip()
            if not desc_text:
                continue
            results.append(EvidenceLink(
                raw=f"[Unknown] {desc_text}",
                type="unknown",
                description=desc_text,
                confidence=0,
            ))

        elif marker_text.startswith("[Stale:"):
            stale_date_m = re.match(r"\[Stale:(\d{4}-\d{2}-\d{2})\]", marker_text)
            if not stale_date_m:
                continue
            stale_date = stale_date_m.group(1)
            token_m = re.match(r"(\S+)(?:\s*::\s*(\S+?)(?:\(\))?)?(?=\s|$)", stripped)
            if not token_m:
                continue
            token = token_m.group(1)
            inline_symbol = _clean_parsed(token_m.group(2)) if token_m.group(2) else None
            raw_text = f"{marker_text} {token_m.group(0).strip()}"
            filepath, start_line, end_line, token_symbol = _parse_link_token(token)
            symbol = token_symbol or inline_symbol
            results.append(EvidenceLink(
                raw=raw_text,
                type="stale",
                stale_date=stale_date,
                filepath=filepath,
                start_line=start_line,
                end_line=end_line,
                symbol=symbol,
                confidence=0,
            ))

        elif marker_text == "[Deprecated]":
            token_m = re.match(r"(\S+)(?:\s*::\s*(\S+?)(?:\(\))?)?(?=\s|$)", stripped)
            if not token_m:
                continue
            token = token_m.group(1)
            inline_symbol = _clean_parsed(token_m.group(2)) if token_m.group(2) else None
            raw_text = f"{marker_text} {token_m.group(0).strip()}"
            filepath, start_line, end_line, token_symbol = _parse_link_token(token)
            symbol = token_symbol or inline_symbol
            results.append(EvidenceLink(
                raw=raw_text,
                type="deprecated",
                filepath=filepath,
                start_line=start_line,
                end_line=end_line,
                symbol=symbol,
                confidence=0.5,
            ))

    return results


# Matches HTML comments including multi-line ones: <!-- ... -->
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def _strip_html_comments(content: str) -> str:
    """Remove all HTML comment blocks (<!-- ... -->) from *content*.

    Multi-line comments are handled via the DOTALL flag.  Line structure is
    preserved by replacing each comment span with the same number of newlines it
    contained so that non-commented lines retain their original line numbers.
    """
    def _replace_with_newlines(m: re.Match) -> str:  # type: ignore[type-arg]
        # Preserve the newlines so surrounding line numbers are stable
        return "\n" * m.group(0).count("\n")

    return _HTML_COMMENT_RE.sub(_replace_with_newlines, content)


def parse_evidence_links(content: str) -> list[EvidenceLink]:
    """Parse all evidence links from a block of markdown content.

    Splits the content into lines and extracts all recognised evidence links from
    each line (a line may contain multiple markers).  HTML comment blocks
    (``<!-- ... -->``) are stripped first so that commented-out evidence links
    are not counted as active.
    """
    results: list[EvidenceLink] = []
    for line in _strip_html_comments(content).split("\n"):
        results.extend(parse_evidence_links_on_line(line))
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
    valid = sum(1 for lnk in links if lnk.type == "valid")
    stale = sum(1 for lnk in links if lnk.type == "stale")
    unknown = sum(1 for lnk in links if lnk.type == "unknown")
    deprecated = sum(1 for lnk in links if lnk.type == "deprecated")
    health_pct = 100 if total == 0 else round((valid / total) * 100)
    return EvidenceStats(
        total=total,
        valid=valid,
        stale=stale,
        unknown=unknown,
        deprecated=deprecated,
        health_pct=health_pct,
    )
