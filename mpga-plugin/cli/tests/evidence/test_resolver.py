"""Tests for mpga.evidence.resolver -- converted from resolver.test.ts."""

from pathlib import Path

from mpga.evidence.parser import EvidenceLink
from mpga.evidence.resolver import resolve_evidence, verify_all_links


def _write_file(base: Path, relative_path: str, content: str) -> Path:
    """Helper to write a file relative to base, creating parent dirs."""
    full = base / relative_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return full


def _make_link(**overrides) -> EvidenceLink:
    """Helper to build an EvidenceLink with defaults."""
    defaults = {
        "raw": "[E] test",
        "type": "valid",
        "confidence": 1.0,
    }
    defaults.update(overrides)
    return EvidenceLink(**defaults)


# ---------------------------------------------------------------------------
# resolve_evidence
# ---------------------------------------------------------------------------


class TestResolveEvidence:
    def test_returns_stale_with_confidence_0_when_no_filepath(self, tmp_path: Path):
        link = _make_link(filepath=None)
        result = resolve_evidence(link, str(tmp_path))
        assert result.status == "stale"
        assert result.confidence == 0

    def test_returns_stale_with_confidence_0_when_file_does_not_exist(self, tmp_path: Path):
        link = _make_link(filepath="nonexistent/file.ts")
        result = resolve_evidence(link, str(tmp_path))
        assert result.status == "stale"
        assert result.confidence == 0

    def test_returns_valid_with_confidence_0_8_for_file_only_link(self, tmp_path: Path):
        _write_file(tmp_path, "src/utils.ts", "export const x = 1;\n")
        link = _make_link(filepath="src/utils.ts")
        result = resolve_evidence(link, str(tmp_path))
        assert result.status == "valid"
        assert result.confidence == 0.8

    def test_returns_valid_with_confidence_1_0_when_line_range_matches_symbol(self, tmp_path: Path):
        source = (
            "const a = 1;\n"
            "export function greet(name: string) {\n"
            "  return `Hello, ${name}`;\n"
            "}\n"
            "const b = 2;\n"
        )
        _write_file(tmp_path, "src/greet.ts", source)
        link = _make_link(
            filepath="src/greet.ts",
            start_line=2,
            end_line=4,
            symbol="greet",
        )
        result = resolve_evidence(link, str(tmp_path))
        assert result.status == "valid"
        assert result.confidence == 1.0
        assert result.start_line == 2
        assert result.end_line == 4

    def test_returns_healed_with_confidence_0_9_when_lines_shifted(self, tmp_path: Path):
        source = (
            "// comment line 1\n"
            "// comment line 2\n"
            "// comment line 3\n"
            "\n"
            "export function greet(name: string) {\n"
            "  return `Hello, ${name}`;\n"
            "}\n"
        )
        _write_file(tmp_path, "src/greet.ts", source)
        link = _make_link(
            filepath="src/greet.ts",
            start_line=2,
            end_line=4,
            symbol="greet",
        )
        result = resolve_evidence(link, str(tmp_path))
        assert result.status == "healed"
        assert result.confidence == 0.9
        assert result.start_line == 5
        assert "line range changed" in result.healed_from
        assert "was 2-4" in result.healed_from

    def test_returns_healed_with_confidence_0_6_via_fuzzy_text_match(self, tmp_path: Path):
        source = (
            "// This file has some logic\n"
            "const obj = {\n"
            "  mySpecialHandler: (x: number) => x * 2,\n"
            "};\n"
            "export default obj;\n"
        )
        _write_file(tmp_path, "src/handler.ts", source)
        link = _make_link(
            filepath="src/handler.ts",
            start_line=10,
            end_line=15,
            symbol="mySpecialHandler",
        )
        result = resolve_evidence(link, str(tmp_path))
        assert result.status == "healed"
        assert result.confidence == 0.6
        assert result.start_line == 3
        assert "fuzzy match at line 3" in result.healed_from
        assert "was 10-15" in result.healed_from

    def test_returns_stale_when_symbol_is_completely_gone(self, tmp_path: Path):
        source = "export function unrelatedFunction() {\n  return 42;\n}\n"
        _write_file(tmp_path, "src/other.ts", source)
        link = _make_link(
            filepath="src/other.ts",
            start_line=1,
            end_line=3,
            symbol="totallyMissingSymbol",
        )
        result = resolve_evidence(link, str(tmp_path))
        assert result.status == "stale"
        assert result.confidence == 0

    def test_returns_valid_with_confidence_1_0_for_line_range_without_symbol(self, tmp_path: Path):
        source = "const a = 1;\nconst b = 2;\nconst c = 3;\n"
        _write_file(tmp_path, "src/constants.ts", source)
        link = _make_link(
            filepath="src/constants.ts",
            start_line=1,
            end_line=3,
        )
        result = resolve_evidence(link, str(tmp_path))
        assert result.status == "valid"
        assert result.confidence == 1.0

    def test_returns_valid_not_healed_when_ast_finds_symbol_at_same_lines(self, tmp_path: Path):
        source = "export function doWork() {\n  return true;\n}\n"
        _write_file(tmp_path, "src/work.ts", source)
        link = _make_link(
            filepath="src/work.ts",
            start_line=1,
            end_line=3,
            symbol="doWork",
        )
        result = resolve_evidence(link, str(tmp_path))
        assert result.status == "valid"
        assert result.confidence == 1.0

    def test_handles_file_with_only_symbol_and_no_line_range(self, tmp_path: Path):
        source = "export function compute(x: number) {\n  return x * x;\n}\n"
        _write_file(tmp_path, "src/compute.ts", source)
        link = _make_link(
            filepath="src/compute.ts",
            symbol="compute",
        )
        result = resolve_evidence(link, str(tmp_path))
        assert result.status == "valid"
        assert result.confidence == 0.9
        assert result.start_line == 1


# ---------------------------------------------------------------------------
# verify_all_links
# ---------------------------------------------------------------------------


class TestVerifyAllLinks:
    def test_filters_out_links_that_are_not_valid_or_stale(self, tmp_path: Path):
        _write_file(tmp_path, "src/a.ts", "export const a = 1;\n")
        _write_file(tmp_path, "src/b.ts", "export const b = 2;\n")

        links = [
            _make_link(type="valid", filepath="src/a.ts"),
            _make_link(type="unknown", description="some unknown thing"),
            _make_link(type="deprecated", filepath="src/b.ts"),
            _make_link(type="stale", filepath="src/b.ts", stale_date="2026-01-01"),
        ]

        results = verify_all_links(links, str(tmp_path))
        assert len(results) == 2
        assert results[0].link.type == "valid"
        assert results[1].link.type == "stale"

    def test_returns_resolved_evidence_for_each_processed_link(self, tmp_path: Path):
        _write_file(tmp_path, "src/exists.ts", "export const x = 1;\n")

        links = [
            _make_link(type="valid", filepath="src/exists.ts"),
            _make_link(type="valid", filepath="src/missing.ts"),
        ]

        results = verify_all_links(links, str(tmp_path))
        assert len(results) == 2
        assert results[0].resolved.status == "valid"
        assert results[0].resolved.confidence == 0.8
        assert results[1].resolved.status == "stale"
        assert results[1].resolved.confidence == 0

    def test_returns_empty_list_when_given_no_links(self, tmp_path: Path):
        results = verify_all_links([], str(tmp_path))
        assert results == []

    def test_processes_a_batch_of_mixed_links_correctly(self, tmp_path: Path):
        source = (
            "export function alpha() {\n"
            "  return 1;\n"
            "}\n"
            "\n"
            "export function beta() {\n"
            "  return 2;\n"
            "}\n"
        )
        _write_file(tmp_path, "src/funcs.ts", source)

        links = [
            # valid type, file-only -> resolved valid 0.8
            _make_link(type="valid", filepath="src/funcs.ts"),
            # valid type, correct range and symbol -> resolved valid 1.0
            _make_link(
                type="valid",
                filepath="src/funcs.ts",
                start_line=1,
                end_line=3,
                symbol="alpha",
            ),
            # stale type, symbol completely missing -> resolved stale
            _make_link(
                type="stale",
                filepath="src/funcs.ts",
                start_line=1,
                end_line=3,
                symbol="gamma",
                stale_date="2026-01-01",
            ),
            # unknown type -> filtered out
            _make_link(type="unknown", description="not checked"),
            # deprecated type -> filtered out
            _make_link(type="deprecated", filepath="src/funcs.ts"),
        ]

        results = verify_all_links(links, str(tmp_path))
        assert len(results) == 3

        assert results[0].resolved.status == "valid"
        assert results[0].resolved.confidence == 0.8

        assert results[1].resolved.status == "valid"
        assert results[1].resolved.confidence == 1.0

        assert results[2].resolved.status == "stale"
        assert results[2].resolved.confidence == 0

    def test_preserves_the_original_link_object_in_each_result(self, tmp_path: Path):
        _write_file(tmp_path, "src/x.ts", "const x = 1;\n")

        link = _make_link(type="valid", filepath="src/x.ts", raw="[E] src/x.ts")
        results = verify_all_links([link], str(tmp_path))

        assert results[0].link is link  # same reference
        assert results[0].link.raw == "[E] src/x.ts"


# ---------------------------------------------------------------------------
# resolve_evidence -- symbol-based format
# ---------------------------------------------------------------------------


class TestResolveEvidenceSymbolBased:
    def test_resolves_when_symbol_is_at_hinted_line(self, tmp_path: Path):
        source = (
            "const a = 1;\n"
            "export function greet(name: string) {\n"
            "  return `Hello, ${name}`;\n"
            "}\n"
        )
        _write_file(tmp_path, "src/greet.ts", source)
        link = _make_link(
            filepath="src/greet.ts",
            symbol="greet",
            start_line=2,
        )
        result = resolve_evidence(link, str(tmp_path))
        assert result.status == "valid"
        assert result.confidence >= 0.9
        assert result.start_line == 2

    def test_resolves_when_line_hint_has_drifted(self, tmp_path: Path):
        source = (
            "// comment 1\n"
            "// comment 2\n"
            "// comment 3\n"
            "\n"
            "export function greet(name: string) {\n"
            "  return `Hello, ${name}`;\n"
            "}\n"
        )
        _write_file(tmp_path, "src/greet.ts", source)
        link = _make_link(
            filepath="src/greet.ts",
            symbol="greet",
            start_line=2,  # drifted hint -- actual is line 5
        )
        result = resolve_evidence(link, str(tmp_path))
        assert result.status == "healed"
        assert result.confidence >= 0.6
        assert result.start_line == 5
        assert result.healed_from is not None

    def test_resolves_with_no_line_hint_at_all(self, tmp_path: Path):
        source = "export function compute(x: number) {\n  return x * x;\n}\n"
        _write_file(tmp_path, "src/compute.ts", source)
        link = _make_link(
            filepath="src/compute.ts",
            symbol="compute",
        )
        result = resolve_evidence(link, str(tmp_path))
        assert result.confidence >= 0.6
        assert result.start_line == 1

    def test_falls_back_to_fuzzy_match_when_symbol_not_found_via_ast(self, tmp_path: Path):
        source = (
            "// logic module\n"
            "const handlers = {\n"
            "  specialHandler: (x: number) => x * 2,\n"
            "};\n"
            "export default handlers;\n"
        )
        _write_file(tmp_path, "src/handler.ts", source)
        link = _make_link(
            filepath="src/handler.ts",
            symbol="specialHandler",
            start_line=10,  # drifted hint
        )
        result = resolve_evidence(link, str(tmp_path))
        assert result.status == "healed"
        assert result.confidence == 0.6
        assert result.start_line == 3

    def test_returns_stale_when_symbol_is_gone_and_line_hint_useless(self, tmp_path: Path):
        source = "export function unrelated() {\n  return 1;\n}\n"
        _write_file(tmp_path, "src/gone.ts", source)
        link = _make_link(
            filepath="src/gone.ts",
            symbol="vanishedSymbol",
            start_line=5,
        )
        result = resolve_evidence(link, str(tmp_path))
        assert result.status == "stale"
        assert result.confidence == 0
