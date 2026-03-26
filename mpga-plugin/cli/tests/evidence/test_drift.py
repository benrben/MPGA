"""Tests for mpga.evidence.drift -- converted from drift.test.ts."""

from pathlib import Path

import pytest

from mpga.evidence.drift import run_drift_check, heal_scope_file, ScopeDriftReport, HealedDriftItem
from mpga.evidence.parser import EvidenceLink


def _write_file(base: Path, relative_path: str, content: str) -> Path:
    """Helper to write a file relative to base, creating parent dirs."""
    full = base / relative_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return full


# ---------------------------------------------------------------------------
# run_drift_check
# ---------------------------------------------------------------------------


class TestRunDriftCheck:
    def test_returns_100_health_when_scopes_dir_does_not_exist(self, tmp_path: Path):
        report = run_drift_check(str(tmp_path), 80)
        assert report.overall_health_pct == 100
        assert report.scopes == []
        assert report.total_links == 0
        assert report.valid_links == 0
        assert report.ci_pass is True
        assert report.ci_threshold == 80
        assert report.project_root == str(tmp_path)
        assert report.timestamp

    def test_returns_100_health_when_scope_has_no_evidence_links(self, tmp_path: Path):
        _write_file(
            tmp_path,
            "MPGA/scopes/empty.md",
            "# Empty Scope\n\nThis scope has no evidence links at all.\n",
        )
        report = run_drift_check(str(tmp_path), 80)
        assert report.overall_health_pct == 100
        assert len(report.scopes) == 1
        assert report.scopes[0].scope == "empty"
        assert report.scopes[0].total_links == 0
        assert report.scopes[0].health_pct == 100
        assert report.total_links == 0
        assert report.ci_pass is True

    def test_reports_valid_links_when_files_and_symbols_exist(self, tmp_path: Path):
        _write_file(tmp_path, "src/foo.ts", "export function myFunction() {\n  return 42;\n}\n")
        _write_file(
            tmp_path,
            "MPGA/scopes/core.md",
            "# Core Scope\n\n[E] src/foo.ts:1-3 :: myFunction\n",
        )
        report = run_drift_check(str(tmp_path), 80)
        assert len(report.scopes) == 1
        scope = report.scopes[0]
        assert scope.scope == "core"
        assert scope.total_links == 1
        assert scope.valid_links == 1
        assert scope.stale_links == 0
        assert scope.healed_links == 0
        assert scope.health_pct == 100
        assert len(scope.stale_items) == 0
        assert report.overall_health_pct == 100
        assert report.ci_pass is True

    def test_reports_valid_for_file_only_evidence_link(self, tmp_path: Path):
        _write_file(tmp_path, "src/bar.ts", "export const x = 1;\n")
        _write_file(tmp_path, "MPGA/scopes/misc.md", "# Misc\n\n[E] src/bar.ts\n")
        report = run_drift_check(str(tmp_path), 80)
        scope = report.scopes[0]
        assert scope.total_links == 1
        assert scope.valid_links == 1
        assert scope.stale_links == 0
        assert scope.health_pct == 100

    def test_reports_stale_links_when_files_are_missing(self, tmp_path: Path):
        _write_file(
            tmp_path,
            "MPGA/scopes/broken.md",
            "# Broken Scope\n\n[E] src/nonexistent.ts:1-10 :: missingFunc\n",
        )
        report = run_drift_check(str(tmp_path), 80)
        assert len(report.scopes) == 1
        scope = report.scopes[0]
        assert scope.scope == "broken"
        assert scope.total_links == 1
        assert scope.stale_links == 1
        assert scope.valid_links == 0
        assert scope.health_pct == 0
        assert len(scope.stale_items) == 1
        assert "File not found" in scope.stale_items[0].reason
        assert scope.stale_items[0].link.filepath == "src/nonexistent.ts"
        assert report.overall_health_pct == 0

    def test_reports_stale_when_file_exists_but_symbol_not_found(self, tmp_path: Path):
        _write_file(tmp_path, "src/exists.ts", "export const unrelated = true;\n")
        _write_file(
            tmp_path,
            "MPGA/scopes/sym.md",
            "# Sym\n\n[E] src/exists.ts:1-5 :: noSuchSymbol\n",
        )
        report = run_drift_check(str(tmp_path), 80)
        scope = report.scopes[0]
        assert scope.stale_links == 1
        assert len(scope.stale_items) == 1
        assert scope.stale_items[0].reason == "Symbol not found in file"

    def test_reports_healed_links_when_symbol_moved(self, tmp_path: Path):
        _write_file(
            tmp_path,
            "src/moved.ts",
            "// some header\n// another line\nexport function movedFunc() {\n  return 1;\n}\n",
        )
        _write_file(
            tmp_path,
            "MPGA/scopes/heal.md",
            "# Heal\n\n[E] src/moved.ts:1-3 :: movedFunc\n",
        )
        report = run_drift_check(str(tmp_path), 80)
        scope = report.scopes[0]
        assert scope.total_links == 1
        assert scope.healed_links + scope.valid_links >= 1
        assert scope.stale_links == 0
        assert scope.health_pct == 100

    def test_scope_filter_limits_to_a_single_scope(self, tmp_path: Path):
        _write_file(tmp_path, "src/a.ts", "export function funcA() {}\n")
        _write_file(tmp_path, "src/b.ts", "export function funcB() {}\n")
        _write_file(
            tmp_path, "MPGA/scopes/alpha.md", "# Alpha\n\n[E] src/a.ts:1-1 :: funcA\n"
        )
        _write_file(
            tmp_path, "MPGA/scopes/beta.md", "# Beta\n\n[E] src/b.ts:1-1 :: funcB\n"
        )
        report = run_drift_check(str(tmp_path), 80, "alpha")
        assert len(report.scopes) == 1
        assert report.scopes[0].scope == "alpha"

    def test_scope_filter_returns_empty_scopes_when_filter_matches_nothing(self, tmp_path: Path):
        _write_file(tmp_path, "MPGA/scopes/alpha.md", "# Alpha\n\n[E] src/a.ts\n")
        report = run_drift_check(str(tmp_path), 80, "nonexistent")
        assert len(report.scopes) == 0
        assert report.overall_health_pct == 100
        assert report.total_links == 0

    def test_ci_pass_is_true_when_health_gte_threshold(self, tmp_path: Path):
        _write_file(tmp_path, "src/ok.ts", "export function okFunc() {}\n")
        _write_file(
            tmp_path, "MPGA/scopes/pass.md", "# Pass\n\n[E] src/ok.ts:1-1 :: okFunc\n"
        )
        report = run_drift_check(str(tmp_path), 100)
        assert report.ci_pass is True

    def test_ci_pass_is_false_when_health_lt_threshold(self, tmp_path: Path):
        _write_file(
            tmp_path,
            "MPGA/scopes/fail.md",
            "# Fail\n\n[E] src/missing.ts:1-10 :: gone\n",
        )
        report = run_drift_check(str(tmp_path), 50)
        assert report.overall_health_pct == 0
        assert report.ci_pass is False

    def test_computes_overall_health_pct_across_multiple_scopes(self, tmp_path: Path):
        _write_file(tmp_path, "src/good.ts", "export function goodFunc() {}\n")
        _write_file(
            tmp_path,
            "MPGA/scopes/good.md",
            "# Good\n\n[E] src/good.ts:1-1 :: goodFunc\n",
        )
        _write_file(
            tmp_path,
            "MPGA/scopes/bad.md",
            "# Bad\n\n[E] src/nope.ts:1-5 :: nope\n",
        )
        report = run_drift_check(str(tmp_path), 40)
        assert report.total_links == 2
        assert report.overall_health_pct == 50
        assert report.ci_pass is True  # 50 >= 40

    def test_ignores_non_md_files_in_scopes_directory(self, tmp_path: Path):
        _write_file(tmp_path, "MPGA/scopes/data.json", '{"not": "a scope"}')
        _write_file(tmp_path, "MPGA/scopes/readme.txt", "not a scope")
        report = run_drift_check(str(tmp_path), 80)
        assert len(report.scopes) == 0
        assert report.total_links == 0

    def test_filters_out_unknown_and_deprecated_link_types(self, tmp_path: Path):
        _write_file(
            tmp_path,
            "MPGA/scopes/mixed.md",
            "# Mixed\n[E] src/valid.ts\n[Unknown] some unknown thing\n[Deprecated] src/old.ts:1-5\n",
        )
        _write_file(tmp_path, "src/valid.ts", "export const v = 1;\n")
        report = run_drift_check(str(tmp_path), 80)
        scope = report.scopes[0]
        assert scope.total_links == 1
        assert scope.valid_links == 1


# ---------------------------------------------------------------------------
# heal_scope_file
# ---------------------------------------------------------------------------


class TestHealScopeFile:
    def test_replaces_evidence_link_line_ranges_with_healed_values(self, tmp_path: Path):
        scope_path = tmp_path / "MPGA" / "scopes" / "healable.md"
        scope_path.parent.mkdir(parents=True)
        original_content = (
            "# Healable Scope\n"
            "\n"
            "Some description here.\n"
            "\n"
            "[E] src/foo.ts:1-10 :: myFunction()\n"
            "[E] src/bar.ts:5-15 :: otherFunc()\n"
            "\n"
            "More text.\n"
        )
        scope_path.write_text(original_content, encoding="utf-8")

        report = ScopeDriftReport(
            scope="healable",
            scope_path=str(scope_path),
            total_links=2,
            valid_links=0,
            healed_links=2,
            stale_links=0,
            health_pct=100,
            stale_items=[],
            healed_items=[
                HealedDriftItem(
                    link=EvidenceLink(
                        raw="[E] src/foo.ts:1-10 :: myFunction()",
                        type="valid",
                        filepath="src/foo.ts",
                        start_line=1,
                        end_line=10,
                        symbol="myFunction",
                        confidence=1.0,
                    ),
                    new_start=20,
                    new_end=35,
                ),
                HealedDriftItem(
                    link=EvidenceLink(
                        raw="[E] src/bar.ts:5-15 :: otherFunc()",
                        type="valid",
                        filepath="src/bar.ts",
                        start_line=5,
                        end_line=15,
                        symbol="otherFunc",
                        confidence=1.0,
                    ),
                    new_start=50,
                    new_end=70,
                ),
            ],
        )

        result = heal_scope_file(report)
        assert result.healed == 2
        assert "[E] src/foo.ts:20-35 :: myFunction()" in result.content
        assert "[E] src/bar.ts:50-70 :: otherFunc()" in result.content
        assert ":1-10" not in result.content
        assert ":5-15" not in result.content

    def test_returns_healed_count(self, tmp_path: Path):
        scope_path = tmp_path / "MPGA" / "scopes" / "count.md"
        scope_path.parent.mkdir(parents=True)
        scope_path.write_text(
            "# Count\n\n[E] src/x.ts:1-5 :: alpha()\n[E] src/y.ts:10-20 :: beta()\n",
            encoding="utf-8",
        )

        report = ScopeDriftReport(
            scope="count",
            scope_path=str(scope_path),
            total_links=2,
            valid_links=0,
            healed_links=2,
            stale_links=0,
            health_pct=100,
            stale_items=[],
            healed_items=[
                HealedDriftItem(
                    link=EvidenceLink(
                        raw="[E] src/x.ts:1-5 :: alpha()",
                        type="valid",
                        filepath="src/x.ts",
                        start_line=1,
                        end_line=5,
                        symbol="alpha",
                        confidence=1.0,
                    ),
                    new_start=3,
                    new_end=8,
                ),
                HealedDriftItem(
                    link=EvidenceLink(
                        raw="[E] src/y.ts:10-20 :: beta()",
                        type="valid",
                        filepath="src/y.ts",
                        start_line=10,
                        end_line=20,
                        symbol="beta",
                        confidence=1.0,
                    ),
                    new_start=12,
                    new_end=25,
                ),
            ],
        )

        result = heal_scope_file(report)
        assert result.healed == 2

    def test_handles_scope_file_with_no_healable_links(self, tmp_path: Path):
        scope_path = tmp_path / "MPGA" / "scopes" / "noheal.md"
        scope_path.parent.mkdir(parents=True)
        content = "# No Heal\n\nJust some text, no evidence links.\n"
        scope_path.write_text(content, encoding="utf-8")

        report = ScopeDriftReport(
            scope="noheal",
            scope_path=str(scope_path),
            total_links=0,
            valid_links=0,
            healed_links=0,
            stale_links=0,
            health_pct=100,
            stale_items=[],
            healed_items=[],
        )

        result = heal_scope_file(report)
        assert result.healed == 0
        assert result.content == content

    def test_preserves_non_evidence_content_when_healing(self, tmp_path: Path):
        scope_path = tmp_path / "MPGA" / "scopes" / "preserve.md"
        scope_path.parent.mkdir(parents=True)
        content = (
            "# Preserve Scope\n"
            "\n"
            "Important description that must survive.\n"
            "\n"
            "## Evidence\n"
            "[E] src/keep.ts:1-5 :: keepFunc()\n"
            "\n"
            "## Notes\n"
            "These notes should not change.\n"
        )
        scope_path.write_text(content, encoding="utf-8")

        report = ScopeDriftReport(
            scope="preserve",
            scope_path=str(scope_path),
            total_links=1,
            valid_links=0,
            healed_links=1,
            stale_links=0,
            health_pct=100,
            stale_items=[],
            healed_items=[
                HealedDriftItem(
                    link=EvidenceLink(
                        raw="[E] src/keep.ts:1-5 :: keepFunc()",
                        type="valid",
                        filepath="src/keep.ts",
                        start_line=1,
                        end_line=5,
                        symbol="keepFunc",
                        confidence=1.0,
                    ),
                    new_start=10,
                    new_end=20,
                ),
            ],
        )

        result = heal_scope_file(report)
        assert result.healed == 1
        assert "Important description that must survive." in result.content
        assert "These notes should not change." in result.content
        assert "[E] src/keep.ts:10-20 :: keepFunc()" in result.content

    def test_skips_healed_items_with_no_filepath(self, tmp_path: Path):
        scope_path = tmp_path / "MPGA" / "scopes" / "nopath.md"
        scope_path.parent.mkdir(parents=True)
        content = "# No Path\n\nSome content.\n"
        scope_path.write_text(content, encoding="utf-8")

        report = ScopeDriftReport(
            scope="nopath",
            scope_path=str(scope_path),
            total_links=1,
            valid_links=0,
            healed_links=1,
            stale_links=0,
            health_pct=100,
            stale_items=[],
            healed_items=[
                HealedDriftItem(
                    link=EvidenceLink(
                        raw="[E] something",
                        type="valid",
                        confidence=0.5,
                        # no filepath
                    ),
                    new_start=1,
                    new_end=5,
                ),
            ],
        )

        result = heal_scope_file(report)
        assert result.healed == 0
        assert result.content == content

    def test_heals_evidence_link_without_symbol(self, tmp_path: Path):
        scope_path = tmp_path / "MPGA" / "scopes" / "nosym.md"
        scope_path.parent.mkdir(parents=True)
        content = "# No Symbol\n\n[E] src/plain.ts:1-10\n"
        scope_path.write_text(content, encoding="utf-8")

        report = ScopeDriftReport(
            scope="nosym",
            scope_path=str(scope_path),
            total_links=1,
            valid_links=0,
            healed_links=1,
            stale_links=0,
            health_pct=100,
            stale_items=[],
            healed_items=[
                HealedDriftItem(
                    link=EvidenceLink(
                        raw="[E] src/plain.ts:1-10",
                        type="valid",
                        filepath="src/plain.ts",
                        start_line=1,
                        end_line=10,
                        confidence=1.0,
                    ),
                    new_start=5,
                    new_end=15,
                ),
            ],
        )

        result = heal_scope_file(report)
        assert result.healed == 1
        assert "[E] src/plain.ts:5-15" in result.content
        assert ":1-10" not in result.content
