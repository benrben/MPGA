"""Regression tests for M004 evidence layer correctness failure modes."""
from __future__ import annotations

from mpga.evidence.ast import extract_symbols
from mpga.evidence.parser import (
    parse_evidence_link,
    parse_evidence_links,
    parse_evidence_links_on_line,
)

# ---------------------------------------------------------------------------
# T024: multi-link per line
# ---------------------------------------------------------------------------

def test_multi_link_on_one_line():
    """Two [E] markers on one line → two EvidenceLinks."""
    line = "See [E] a.ts:1-5 and also [E] b.ts:10-20 for details."
    links = parse_evidence_links_on_line(line)
    assert len(links) == 2
    assert links[0].filepath == "a.ts"
    assert links[1].filepath == "b.ts"


def test_multi_link_mixed_types():
    """[E] + [Unknown] on one line → two links of different types."""
    line = "[E] a.ts:1-5 [Unknown] description of missing thing"
    links = parse_evidence_links_on_line(line)
    assert len(links) == 2
    types = {lnk.type for lnk in links}
    assert "valid" in types
    assert "unknown" in types


def test_mixed_prose_and_citations():
    """Prose text between citations → all links extracted."""
    line = "First [E] a.ts:1-5 then some prose then [E] b.ts:6-10 end."
    links = parse_evidence_links_on_line(line)
    assert len(links) == 2
    assert links[0].filepath == "a.ts"
    assert links[1].filepath == "b.ts"


def test_markdown_table_cell_multi():
    """Markdown table cell with two [E] markers → two links."""
    line = "| claim | [E] a.ts:1-5 [E] b.ts:10-15 |"
    links = parse_evidence_links_on_line(line)
    assert len(links) == 2


def test_single_link_line_no_regression():
    """Single [E] on a line still returns one link (no regression)."""
    line = "[E] file.ts:1-10"
    links = parse_evidence_links_on_line(line)
    assert len(links) == 1
    assert links[0].filepath == "file.ts"


def test_parse_evidence_links_multi_line_content():
    """parse_evidence_links extracts links from multiple lines, including multi-link lines."""
    content = "[E] a.ts:1-5\n[E] b.ts:1-5 [E] c.ts:10-20\n[Unknown] something"
    links = parse_evidence_links(content)
    assert len(links) == 4


def test_stale_preserves_symbol_in_multi_link_path():
    """[Stale:DATE] with :: symbol suffix → symbol captured via parse_evidence_links_on_line."""
    line = "[Stale:2026-01-01] src.ts:10-20 :: myFunc()"
    links = parse_evidence_links_on_line(line)
    assert len(links) == 1
    assert links[0].symbol == "myFunc"
    assert links[0].start_line == 10
    assert links[0].end_line == 20


def test_deprecated_preserves_symbol_in_multi_link_path():
    """[Deprecated] with :: symbol suffix → symbol captured via parse_evidence_links_on_line."""
    line = "[Deprecated] src.ts:5-15 :: oldHelper()"
    links = parse_evidence_links_on_line(line)
    assert len(links) == 1
    assert links[0].symbol == "oldHelper"
    assert links[0].type == "deprecated"


# ---------------------------------------------------------------------------
# T025: file:line single-line anchor
# ---------------------------------------------------------------------------

def test_plain_file_colon_line():
    """[E] file.ts:42 → start_line=42, end_line=42."""
    link = parse_evidence_link("[E] file.ts:42")
    assert link is not None
    assert link.start_line == 42
    assert link.end_line == 42


def test_plain_file_colon_line_range_no_regression():
    """[E] file.ts:1-20 → start_line=1, end_line=20 (no regression)."""
    link = parse_evidence_link("[E] file.ts:1-20")
    assert link is not None
    assert link.start_line == 1
    assert link.end_line == 20


def test_file_only_no_regression():
    """[E] file.ts → start_line=None, end_line=None (no regression)."""
    link = parse_evidence_link("[E] file.ts")
    assert link is not None
    assert link.start_line is None
    assert link.end_line is None


def test_stale_single_line_anchor():
    """[Stale:2026-01-01] file.ts:42 → start_line=42, end_line=42."""
    link = parse_evidence_link("[Stale:2026-01-01] file.ts:42")
    assert link is not None
    assert link.start_line == 42
    assert link.end_line == 42


def test_deprecated_single_line_anchor():
    """[Deprecated] file.ts:99 → start_line=99, end_line=99."""
    link = parse_evidence_link("[Deprecated] file.ts:99")
    assert link is not None
    assert link.start_line == 99
    assert link.end_line == 99


# ---------------------------------------------------------------------------
# T026: AST file-type router
# ---------------------------------------------------------------------------

def test_yaml_file_returns_no_symbols(tmp_path):
    """.yaml file → extract_symbols() returns []."""
    f = tmp_path / "config.yaml"
    f.write_text("key: value\nother: 123\n")
    symbols = extract_symbols("config.yaml", str(tmp_path))
    assert symbols == []


def test_json_file_returns_no_symbols(tmp_path):
    """.json file → extract_symbols() returns []."""
    f = tmp_path / "package.json"
    f.write_text('{"name": "test", "version": "1.0.0"}\n')
    symbols = extract_symbols("package.json", str(tmp_path))
    assert symbols == []


def test_md_file_returns_no_symbols(tmp_path):
    """.md file → extract_symbols() returns []."""
    f = tmp_path / "README.md"
    f.write_text("# Title\n\nSome content.\n")
    symbols = extract_symbols("README.md", str(tmp_path))
    assert symbols == []


def test_python_ast_extracts_function(tmp_path):
    """Python file → function extracted at correct lineno."""
    f = tmp_path / "foo.py"
    f.write_text("def my_function():\n    pass\n")
    symbols = extract_symbols("foo.py", str(tmp_path))
    names = [s.name for s in symbols]
    assert "my_function" in names


def test_python_ast_extracts_decorated_function(tmp_path):
    """Python file with @decorator → function extracted at the def line (not decorator)."""
    f = tmp_path / "bar.py"
    f.write_text("@some_decorator\ndef decorated():\n    pass\n")
    symbols = extract_symbols("bar.py", str(tmp_path))
    names = [s.name for s in symbols]
    assert "decorated" in names
    # lineno should be at the def line (2), not the decorator (1)
    sym = next(s for s in symbols if s.name == "decorated")
    assert sym.start_line == 2


def test_python_ast_extracts_class(tmp_path):
    """Python file with class → class extracted."""
    f = tmp_path / "cls.py"
    f.write_text("class MyClass:\n    def method(self):\n        pass\n")
    symbols = extract_symbols("cls.py", str(tmp_path))
    names = [s.name for s in symbols]
    assert "MyClass" in names


# ---------------------------------------------------------------------------
# T029: stale-item downgrade
# ---------------------------------------------------------------------------

def test_stale_symbol_downgrades_to_range(tmp_path):
    """try_downgrade_stale: stale item with valid start_line → [E] file:N-N."""
    from mpga.evidence.drift import StaleDriftItem, try_downgrade_stale
    from mpga.evidence.parser import EvidenceLink

    target = tmp_path / "src.py"
    target.write_text("\n".join(f"line {i}" for i in range(1, 201)))  # 200 lines

    link = EvidenceLink(raw="[Stale:2026-01-01] src.py#old_func:50", type="stale",
                        confidence=0, filepath="src.py", start_line=50, stale_date="2026-01-01")
    item = StaleDriftItem(link=link, reason="symbol not found")
    result = try_downgrade_stale(item, str(tmp_path))
    assert result == "[E] src.py:50-50"


def test_stale_no_downgrade_when_file_missing(tmp_path):
    """try_downgrade_stale: file does not exist → None."""
    from mpga.evidence.drift import StaleDriftItem, try_downgrade_stale
    from mpga.evidence.parser import EvidenceLink

    link = EvidenceLink(raw="[Stale:2026-01-01] missing.py#func:10", type="stale",
                        confidence=0, filepath="missing.py", start_line=10, stale_date="2026-01-01")
    item = StaleDriftItem(link=link, reason="file not found")
    result = try_downgrade_stale(item, str(tmp_path))
    assert result is None


def test_stale_no_downgrade_when_line_out_of_range(tmp_path):
    """try_downgrade_stale: start_line beyond file length → None."""
    from mpga.evidence.drift import StaleDriftItem, try_downgrade_stale
    from mpga.evidence.parser import EvidenceLink

    target = tmp_path / "short.py"
    target.write_text("line1\nline2\nline3\n")  # 3 lines

    link = EvidenceLink(raw="[Stale:2026-01-01] short.py#func:999", type="stale",
                        confidence=0, filepath="short.py", start_line=999, stale_date="2026-01-01")
    item = StaleDriftItem(link=link, reason="symbol not found")
    result = try_downgrade_stale(item, str(tmp_path))
    assert result is None
