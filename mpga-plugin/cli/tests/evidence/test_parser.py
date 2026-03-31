"""Tests for mpga.evidence.parser -- converted from parser.test.ts."""


from mpga.evidence.parser import (
    EvidenceLink,
    evidence_stats,
    format_evidence_link,
    parse_evidence_link,
    parse_evidence_links,
)

# ---------------------------------------------------------------------------
# parse_evidence_link
# ---------------------------------------------------------------------------


class TestParseEvidenceLink:
    def test_parses_a_full_evidence_link_with_line_range_and_symbol(self):
        result = parse_evidence_link("[E] src/auth/jwt.ts:42-67 :: generateAccessToken()")
        assert result is not None
        assert result.raw == "[E] src/auth/jwt.ts:42-67 :: generateAccessToken()"
        assert result.type == "valid"
        assert result.filepath == "src/auth/jwt.ts"
        assert result.start_line == 42
        assert result.end_line == 67
        assert result.symbol == "generateAccessToken"
        assert result.confidence == 1.0

    def test_parses_an_evidence_link_with_line_range_only(self):
        result = parse_evidence_link("[E] src/foo.ts:10-20")
        assert result is not None
        assert result.type == "valid"
        assert result.filepath == "src/foo.ts"
        assert result.start_line == 10
        assert result.end_line == 20
        assert result.symbol is None

    def test_parses_an_ast_only_evidence_link(self):
        result = parse_evidence_link("[E] src/foo.ts :: validateToken")
        assert result is not None
        assert result.type == "valid"
        assert result.filepath == "src/foo.ts"
        assert result.start_line is None
        assert result.symbol == "validateToken"

    def test_parses_unknown_links(self):
        result = parse_evidence_link("[Unknown] token rotation logic")
        assert result is not None
        assert result.type == "unknown"
        assert result.description == "token rotation logic"
        assert result.confidence == 0

    def test_parses_stale_links(self):
        result = parse_evidence_link("[Stale:2026-03-20] src/auth/jwt.ts:42-67")
        assert result is not None
        assert result.type == "stale"
        assert result.stale_date == "2026-03-20"
        assert result.filepath == "src/auth/jwt.ts"
        assert result.start_line == 42
        assert result.end_line == 67

    def test_parses_deprecated_links(self):
        result = parse_evidence_link("[Deprecated] src/old.ts:1-10 :: oldFunc()")
        assert result is not None
        assert result.type == "deprecated"
        assert result.filepath == "src/old.ts"
        assert result.symbol == "oldFunc"
        assert result.confidence == 0.5

    def test_returns_none_for_non_evidence_lines(self):
        assert parse_evidence_link("just a comment") is None
        assert parse_evidence_link("## Heading") is None
        assert parse_evidence_link("") is None

    def test_strips_backticks_from_parsed_values(self):
        result = parse_evidence_link("[E] `src/foo.ts`:10-20 :: `bar()`")
        assert result is not None
        assert result.filepath == "src/foo.ts"
        assert result.symbol == "bar"

    # --- Symbol-based format: file#symbol:lineHint ---

    def test_parses_symbol_based_format_with_line_hint(self):
        result = parse_evidence_link("[E] src/board/board.ts#checkWipLimit:170")
        assert result is not None
        assert result.type == "valid"
        assert result.filepath == "src/board/board.ts"
        assert result.symbol == "checkWipLimit"
        assert result.start_line == 170
        assert result.confidence == 1.0
        assert result.end_line is None

    def test_parses_symbol_based_format_without_line_hint(self):
        result = parse_evidence_link("[E] src/board/board.ts#checkWipLimit")
        assert result is not None
        assert result.type == "valid"
        assert result.filepath == "src/board/board.ts"
        assert result.symbol == "checkWipLimit"
        assert result.confidence == 1.0
        assert result.start_line is None
        assert result.end_line is None

    def test_parses_symbol_based_format_with_description_after_dash_separator(self):
        result = parse_evidence_link(
            "[E] src/board/board.ts#checkWipLimit:170 \u2014 WIP limit validation"
        )
        assert result is not None
        assert result.type == "valid"
        assert result.filepath == "src/board/board.ts"
        assert result.symbol == "checkWipLimit"
        assert result.start_line == 170
        assert result.description == "WIP limit validation"

    def test_parses_symbol_based_stale_format(self):
        result = parse_evidence_link("[Stale:2026-03-20] src/foo.ts#myFunc:42")
        assert result is not None
        assert result.type == "stale"
        assert result.stale_date == "2026-03-20"
        assert result.filepath == "src/foo.ts"
        assert result.symbol == "myFunc"
        assert result.start_line == 42

    def test_parses_symbol_based_deprecated_format(self):
        result = parse_evidence_link("[Deprecated] src/old.ts#legacyInit:5")
        assert result is not None
        assert result.type == "deprecated"
        assert result.filepath == "src/old.ts"
        assert result.symbol == "legacyInit"
        assert result.start_line == 5

    def test_strips_backticks_from_symbol_based_format(self):
        result = parse_evidence_link("[E] `src/foo.ts`#`bar`:10")
        assert result is not None
        assert result.filepath == "src/foo.ts"
        assert result.symbol == "bar"
        assert result.start_line == 10


# ---------------------------------------------------------------------------
# parse_evidence_links
# ---------------------------------------------------------------------------


class TestParseEvidenceLinks:
    def test_extracts_all_evidence_links_from_multiline_content(self):
        content = """
## Evidence
[E] src/a.ts:1-10 :: funcA()
Some text
[Unknown] missing docs
[E] src/b.ts :: funcB
"""
        links = parse_evidence_links(content)
        assert len(links) == 3
        assert links[0].type == "valid"
        assert links[1].type == "unknown"
        assert links[2].type == "valid"

    def test_returns_empty_list_for_content_with_no_evidence(self):
        assert parse_evidence_links("# Just a heading\nSome text.") == []

    def test_extracts_mixed_old_format_and_symbol_based_links(self):
        content = """
## Evidence
[E] src/a.ts:1-10 :: funcA()
[E] src/b.ts#funcB:20
[Unknown] missing docs
[E] src/c.ts#funcC \u2014 description here
"""
        links = parse_evidence_links(content)
        assert len(links) == 4
        assert links[0].symbol == "funcA"
        assert links[0].start_line == 1
        assert links[0].end_line == 10
        assert links[1].symbol == "funcB"
        assert links[1].start_line == 20
        assert links[1].end_line is None
        assert links[2].type == "unknown"
        assert links[3].symbol == "funcC"
        assert links[3].description == "description here"


# ---------------------------------------------------------------------------
# format_evidence_link
# ---------------------------------------------------------------------------


class TestFormatEvidenceLink:
    def test_formats_a_valid_link_with_symbol(self):
        link = EvidenceLink(
            raw="",
            type="valid",
            filepath="src/a.ts",
            start_line=1,
            end_line=10,
            symbol="foo",
            confidence=1.0,
        )
        assert format_evidence_link(link) == "[E] src/a.ts:1-10 :: foo()"

    def test_formats_a_valid_link_without_line_range_symbol_based(self):
        link = EvidenceLink(
            raw="",
            type="valid",
            filepath="src/a.ts",
            symbol="foo",
            confidence=1.0,
        )
        assert format_evidence_link(link) == "[E] src/a.ts#foo"

    def test_formats_unknown_links(self):
        link = EvidenceLink(
            raw="",
            type="unknown",
            description="something",
            confidence=0,
        )
        assert format_evidence_link(link) == "[Unknown] something"

    def test_formats_stale_links(self):
        link = EvidenceLink(
            raw="",
            type="stale",
            stale_date="2026-03-20",
            filepath="src/a.ts",
            start_line=1,
            end_line=5,
            confidence=0,
        )
        assert format_evidence_link(link) == "[Stale:2026-03-20] src/a.ts:1-5"

    # --- Symbol-based format output ---

    def test_formats_symbol_based_valid_link_with_line_hint(self):
        link = EvidenceLink(
            raw="",
            type="valid",
            filepath="src/board/board.ts",
            symbol="checkWipLimit",
            start_line=170,
            confidence=1.0,
        )
        assert format_evidence_link(link) == "[E] src/board/board.ts#checkWipLimit:170"

    def test_formats_symbol_based_valid_link_without_line_hint(self):
        link = EvidenceLink(
            raw="",
            type="valid",
            filepath="src/board/board.ts",
            symbol="checkWipLimit",
            confidence=1.0,
        )
        assert format_evidence_link(link) == "[E] src/board/board.ts#checkWipLimit"

    def test_formats_symbol_based_valid_link_with_description(self):
        link = EvidenceLink(
            raw="",
            type="valid",
            filepath="src/board/board.ts",
            symbol="checkWipLimit",
            start_line=170,
            description="WIP limit validation",
            confidence=1.0,
        )
        assert format_evidence_link(link) == "[E] src/board/board.ts#checkWipLimit:170 \u2014 WIP limit validation"

    def test_formats_symbol_based_stale_link(self):
        link = EvidenceLink(
            raw="",
            type="stale",
            stale_date="2026-03-20",
            filepath="src/foo.ts",
            symbol="myFunc",
            start_line=42,
            confidence=0,
        )
        assert format_evidence_link(link) == "[Stale:2026-03-20] src/foo.ts#myFunc:42"


# ---------------------------------------------------------------------------
# evidence_stats
# ---------------------------------------------------------------------------


class TestEvidenceStats:
    def test_calculates_correct_statistics(self):
        links = [
            EvidenceLink(raw="", type="valid", filepath="a.ts", confidence=1),
            EvidenceLink(raw="", type="valid", filepath="b.ts", confidence=1),
            EvidenceLink(raw="", type="stale", filepath="c.ts", stale_date="2026-01-01", confidence=0),
            EvidenceLink(raw="", type="unknown", description="x", confidence=0),
        ]
        stats = evidence_stats(links)
        assert stats.total == 4
        assert stats.valid == 2
        assert stats.stale == 1
        assert stats.unknown == 1
        assert stats.health_pct == 50

    def test_returns_100_percent_for_empty_links(self):
        assert evidence_stats([]).health_pct == 100


# ---------------------------------------------------------------------------
# HTML comment filtering in parse_evidence_links
# ---------------------------------------------------------------------------


class TestHtmlCommentFiltering:
    def test_link_inside_single_line_comment_is_ignored(self):
        """[E] inside <!-- --> on a single line must NOT be returned."""
        content = "<!-- [E] src/foo.ts:1-10 -->"
        links = parse_evidence_links(content)
        assert links == [], f"Expected no links but got {links}"

    def test_link_outside_comment_is_found(self):
        """[E] outside any HTML comment must still be returned."""
        content = "[E] src/foo.ts:1-10"
        links = parse_evidence_links(content)
        assert len(links) == 1
        assert links[0].filepath == "src/foo.ts"

    def test_link_before_comment_is_found_link_inside_is_ignored(self):
        """Only the link before the comment open should be returned."""
        content = "[E] src/real.ts:5-10 <!-- [E] src/fake.ts:1-2 -->"
        links = parse_evidence_links(content)
        assert len(links) == 1
        assert links[0].filepath == "src/real.ts"

    def test_multiline_comment_links_all_ignored(self):
        """All [E] links within a multi-line HTML comment are ignored."""
        content = (
            "<!--\n"
            "[E] src/a.ts:1-5\n"
            "[E] src/b.ts:6-10\n"
            "-->"
        )
        links = parse_evidence_links(content)
        assert links == [], f"Expected no links but got {links}"

    def test_link_after_multiline_comment_is_found(self):
        """A link that appears after a closing --> is still parsed."""
        content = (
            "<!--\n"
            "[E] src/commented.ts:1-5\n"
            "-->\n"
            "[E] src/active.ts:20-30"
        )
        links = parse_evidence_links(content)
        assert len(links) == 1
        assert links[0].filepath == "src/active.ts"

    def test_link_straddling_comment_open_is_ignored(self):
        """A line that is inside the comment region is skipped even without a
        closing --> on the same line (multi-line comment scenario)."""
        content = (
            "<!-- start of comment\n"
            "[E] src/inside.ts:1-5\n"
            "[E] src/also_inside.ts:6-10 -->"
        )
        links = parse_evidence_links(content)
        assert links == [], f"Expected no links but got {links}"

    def test_mixed_commented_and_active_links(self):
        """Only active (uncommented) links appear in results."""
        content = (
            "[E] src/active1.ts:1-5\n"
            "<!-- [E] src/hidden.ts:10-20 -->\n"
            "[E] src/active2.ts:30-40"
        )
        links = parse_evidence_links(content)
        assert len(links) == 2
        filepaths = {lnk.filepath for lnk in links}
        assert filepaths == {"src/active1.ts", "src/active2.ts"}
