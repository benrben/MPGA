from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

from mpga.evidence.parser import EvidenceLink, is_symbol_based
from mpga.evidence.ast import find_symbol, verify_range

# Confidence when only the file exists (no symbol or line range).
CONFIDENCE_FILE_ONLY = 0.8
# Confidence when the exact line range is verified.
CONFIDENCE_EXACT_RANGE = 1.0
# Confidence when the symbol is found via AST lookup.
CONFIDENCE_AST_ANCHOR = 0.9
# Confidence when the symbol is found via fuzzy text search.
CONFIDENCE_FUZZY_MATCH = 0.6
# Number of lines to include after a fuzzy match for the end-line estimate.
FUZZY_MATCH_LINE_LOOKAHEAD = 20

ResolutionStatus = Literal["valid", "healed", "stale"]


@dataclass
class ResolvedEvidence:
    status: ResolutionStatus
    confidence: float
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    healed_from: Optional[str] = None  # description of what changed


def resolve_evidence(link: EvidenceLink, project_root: str) -> ResolvedEvidence:
    if not link.filepath:
        return ResolvedEvidence(status="stale", confidence=0)

    full_path = Path(project_root) / link.filepath
    if not full_path.exists():
        return ResolvedEvidence(status="stale", confidence=0)

    # Step 0: File-only link (no symbol, no line range) -- file exists is enough
    if not link.symbol and not link.start_line and not link.end_line:
        return ResolvedEvidence(status="valid", confidence=CONFIDENCE_FILE_ONLY)

    # Step 1: Try exact line range (only for legacy range-based links)
    if link.start_line and link.end_line:
        range_valid = verify_range(
            link.filepath,
            link.start_line,
            link.end_line,
            link.symbol,
            project_root,
        )
        if range_valid:
            return ResolvedEvidence(
                status="valid",
                confidence=CONFIDENCE_EXACT_RANGE,
                start_line=link.start_line,
                end_line=link.end_line,
            )

    # Step 2: Try AST anchor (find symbol by name)
    if link.symbol:
        location = find_symbol(link.filepath, link.symbol, project_root)
        if location:
            if is_symbol_based(link):
                # Symbol-based link: the symbol is the stable anchor.
                # The line hint is advisory -- if the symbol is found, it's valid.
                # Only mark as healed if the hint has drifted so the caller can update it.
                hint_drifted = (
                    link.start_line is not None
                    and link.start_line != location.start_line
                )
                return ResolvedEvidence(
                    status="healed" if hint_drifted else "valid",
                    confidence=CONFIDENCE_AST_ANCHOR,
                    start_line=location.start_line,
                    end_line=location.end_line,
                    healed_from=(
                        f"line hint drifted: was {link.start_line}, now {location.start_line}"
                        if hint_drifted
                        else None
                    ),
                )
            else:
                # Legacy range-based link: compare exact line range
                healed = (
                    link.start_line != location.start_line
                    or link.end_line != location.end_line
                )
                return ResolvedEvidence(
                    status="healed" if healed else "valid",
                    confidence=CONFIDENCE_AST_ANCHOR,
                    start_line=location.start_line,
                    end_line=location.end_line,
                    healed_from=(
                        f"line range changed: was {link.start_line}-{link.end_line}, "
                        f"now {location.start_line}-{location.end_line}"
                        if healed
                        else None
                    ),
                )

    # Step 3: Fuzzy search (symbol name anywhere in file)
    if link.symbol:
        try:
            content = full_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            for i, file_line in enumerate(lines):
                if link.symbol in file_line:
                    if is_symbol_based(link):
                        from_desc = (
                            f"fuzzy match at line {i + 1} "
                            f"(hint was {link.start_line if link.start_line is not None else 'none'})"
                        )
                    else:
                        from_desc = (
                            f"fuzzy match at line {i + 1} "
                            f"(was {link.start_line}-{link.end_line})"
                        )
                    return ResolvedEvidence(
                        status="healed",
                        confidence=CONFIDENCE_FUZZY_MATCH,
                        start_line=i + 1,
                        end_line=min(i + FUZZY_MATCH_LINE_LOOKAHEAD, len(lines)),
                        healed_from=from_desc,
                    )
        except OSError:
            pass

    # Step 4: File exists but symbol not found
    return ResolvedEvidence(status="stale", confidence=0)


@dataclass
class VerifyResult:
    link: EvidenceLink
    resolved: ResolvedEvidence


def verify_all_links(
    links: list[EvidenceLink], project_root: str
) -> list[VerifyResult]:
    return [
        VerifyResult(link=link, resolved=resolve_evidence(link, project_root))
        for link in links
        if link.type in ("valid", "stale")
    ]
