"""Tests for mpga.evidence.drift -- converted from drift.test.ts."""

import pytest
from pathlib import Path

from mpga.db.connection import get_connection
from mpga.db.repos.evidence import EvidenceRepo
from mpga.db.repos.scopes import Scope, ScopeRepo
from mpga.db.repos.symbols import SymbolRepo
from mpga.db.schema import create_schema
from mpga.evidence.drift import HealedDriftItem, ScopeDriftReport, heal_scope_file, run_drift_check
from mpga.evidence.parser import EvidenceLink


def _write_file(base: Path, relative_path: str, content: str) -> Path:
    """Helper to write a file relative to base, creating parent dirs."""
    full = base / relative_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return full


def _setup_db(tmp_path: Path) -> tuple:
    """Create .mpga/mpga.db with schema, return (conn, scope_repo, evidence_repo)."""
    db_path = tmp_path / ".mpga" / "mpga.db"
    conn = get_connection(str(db_path))
    create_schema(conn)
    return conn, ScopeRepo(conn), EvidenceRepo(conn)


def _insert_scope(scope_repo: ScopeRepo, scope_id: str, content: str = "") -> None:
    scope_repo.create(Scope(id=scope_id, name=scope_id, summary="", content=content))


def _insert_evidence(evidence_repo: EvidenceRepo, scope_id: str, link: EvidenceLink) -> None:
    evidence_repo.create(link, scope_id, None)


# ---------------------------------------------------------------------------
# run_drift_check
# ---------------------------------------------------------------------------


class TestRunDriftCheck:
    def test_raises_when_no_db_exists(self, tmp_path: Path):
        """When no DB exists at all, run_drift_check raises RuntimeError."""
        with pytest.raises(RuntimeError, match="No scope data in DB"):
            run_drift_check(str(tmp_path), 80)

    def test_returns_100_health_when_scope_has_no_evidence_links(self, tmp_path: Path):
        conn, scope_repo, _ = _setup_db(tmp_path)
        _insert_scope(scope_repo, "empty", "# Empty Scope\n\nThis scope has no evidence links at all.\n")
        conn.close()

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
        conn, scope_repo, evidence_repo = _setup_db(tmp_path)
        _insert_scope(scope_repo, "core", "# Core Scope\n\n[E] src/foo.ts:1-3 :: myFunction\n")
        _insert_evidence(
            evidence_repo,
            "core",
            EvidenceLink(
                raw="[E] src/foo.ts:1-3 :: myFunction",
                type="valid",
                filepath="src/foo.ts",
                start_line=1,
                end_line=3,
                symbol="myFunction",
                confidence=1.0,
            ),
        )
        conn.close()

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
        conn, scope_repo, evidence_repo = _setup_db(tmp_path)
        _insert_scope(scope_repo, "misc", "# Misc\n\n[E] src/bar.ts\n")
        _insert_evidence(
            evidence_repo,
            "misc",
            EvidenceLink(
                raw="[E] src/bar.ts",
                type="valid",
                filepath="src/bar.ts",
                confidence=1.0,
            ),
        )
        conn.close()

        report = run_drift_check(str(tmp_path), 80)
        scope = report.scopes[0]
        assert scope.total_links == 1
        assert scope.valid_links == 1
        assert scope.stale_links == 0
        assert scope.health_pct == 100

    def test_reports_stale_links_when_files_are_missing(self, tmp_path: Path):
        conn, scope_repo, evidence_repo = _setup_db(tmp_path)
        _insert_scope(scope_repo, "broken", "# Broken Scope\n\n[E] src/nonexistent.ts:1-10 :: missingFunc\n")
        _insert_evidence(
            evidence_repo,
            "broken",
            EvidenceLink(
                raw="[E] src/nonexistent.ts:1-10 :: missingFunc",
                type="valid",
                filepath="src/nonexistent.ts",
                start_line=1,
                end_line=10,
                symbol="missingFunc",
                confidence=1.0,
            ),
        )
        conn.close()

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
        conn, scope_repo, evidence_repo = _setup_db(tmp_path)
        _insert_scope(scope_repo, "sym", "# Sym\n\n[E] src/exists.ts:1-5 :: noSuchSymbol\n")
        _insert_evidence(
            evidence_repo,
            "sym",
            EvidenceLink(
                raw="[E] src/exists.ts:1-5 :: noSuchSymbol",
                type="valid",
                filepath="src/exists.ts",
                start_line=1,
                end_line=5,
                symbol="noSuchSymbol",
                confidence=1.0,
            ),
        )
        conn.close()

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
        conn, scope_repo, evidence_repo = _setup_db(tmp_path)
        _insert_scope(scope_repo, "heal", "# Heal\n\n[E] src/moved.ts:1-3 :: movedFunc\n")
        _insert_evidence(
            evidence_repo,
            "heal",
            EvidenceLink(
                raw="[E] src/moved.ts:1-3 :: movedFunc",
                type="valid",
                filepath="src/moved.ts",
                start_line=1,
                end_line=3,
                symbol="movedFunc",
                confidence=1.0,
            ),
        )
        conn.close()

        report = run_drift_check(str(tmp_path), 80)
        scope = report.scopes[0]
        assert scope.total_links == 1
        assert scope.healed_links + scope.valid_links >= 1
        assert scope.stale_links == 0
        assert scope.health_pct == 100

    def test_scope_filter_limits_to_a_single_scope(self, tmp_path: Path):
        _write_file(tmp_path, "src/a.ts", "export function funcA() {}\n")
        _write_file(tmp_path, "src/b.ts", "export function funcB() {}\n")
        conn, scope_repo, evidence_repo = _setup_db(tmp_path)
        _insert_scope(scope_repo, "alpha", "# Alpha\n\n[E] src/a.ts:1-1 :: funcA\n")
        _insert_evidence(
            evidence_repo,
            "alpha",
            EvidenceLink(
                raw="[E] src/a.ts:1-1 :: funcA",
                type="valid",
                filepath="src/a.ts",
                start_line=1,
                end_line=1,
                symbol="funcA",
                confidence=1.0,
            ),
        )
        _insert_scope(scope_repo, "beta", "# Beta\n\n[E] src/b.ts:1-1 :: funcB\n")
        _insert_evidence(
            evidence_repo,
            "beta",
            EvidenceLink(
                raw="[E] src/b.ts:1-1 :: funcB",
                type="valid",
                filepath="src/b.ts",
                start_line=1,
                end_line=1,
                symbol="funcB",
                confidence=1.0,
            ),
        )
        conn.close()

        report = run_drift_check(str(tmp_path), 80, "alpha")
        assert len(report.scopes) == 1
        assert report.scopes[0].scope == "alpha"

    def test_scope_filter_returns_empty_scopes_when_filter_matches_nothing(self, tmp_path: Path):
        conn, scope_repo, evidence_repo = _setup_db(tmp_path)
        _insert_scope(scope_repo, "alpha", "# Alpha\n\n[E] src/a.ts\n")
        _insert_evidence(
            evidence_repo,
            "alpha",
            EvidenceLink(
                raw="[E] src/a.ts",
                type="valid",
                filepath="src/a.ts",
                confidence=1.0,
            ),
        )
        conn.close()

        report = run_drift_check(str(tmp_path), 80, "nonexistent")
        assert len(report.scopes) == 0
        assert report.overall_health_pct == 100
        assert report.total_links == 0

    def test_ci_pass_is_true_when_health_gte_threshold(self, tmp_path: Path):
        _write_file(tmp_path, "src/ok.ts", "export function okFunc() {}\n")
        conn, scope_repo, evidence_repo = _setup_db(tmp_path)
        _insert_scope(scope_repo, "pass", "# Pass\n\n[E] src/ok.ts:1-1 :: okFunc\n")
        _insert_evidence(
            evidence_repo,
            "pass",
            EvidenceLink(
                raw="[E] src/ok.ts:1-1 :: okFunc",
                type="valid",
                filepath="src/ok.ts",
                start_line=1,
                end_line=1,
                symbol="okFunc",
                confidence=1.0,
            ),
        )
        conn.close()

        report = run_drift_check(str(tmp_path), 100)
        assert report.ci_pass is True

    def test_ci_pass_is_false_when_health_lt_threshold(self, tmp_path: Path):
        conn, scope_repo, evidence_repo = _setup_db(tmp_path)
        _insert_scope(scope_repo, "fail", "# Fail\n\n[E] src/missing.ts:1-10 :: gone\n")
        _insert_evidence(
            evidence_repo,
            "fail",
            EvidenceLink(
                raw="[E] src/missing.ts:1-10 :: gone",
                type="valid",
                filepath="src/missing.ts",
                start_line=1,
                end_line=10,
                symbol="gone",
                confidence=1.0,
            ),
        )
        conn.close()

        report = run_drift_check(str(tmp_path), 50)
        assert report.overall_health_pct == 0
        assert report.ci_pass is False

    def test_computes_overall_health_pct_across_multiple_scopes(self, tmp_path: Path):
        _write_file(tmp_path, "src/good.ts", "export function goodFunc() {}\n")
        conn, scope_repo, evidence_repo = _setup_db(tmp_path)
        _insert_scope(scope_repo, "good", "# Good\n\n[E] src/good.ts:1-1 :: goodFunc\n")
        _insert_evidence(
            evidence_repo,
            "good",
            EvidenceLink(
                raw="[E] src/good.ts:1-1 :: goodFunc",
                type="valid",
                filepath="src/good.ts",
                start_line=1,
                end_line=1,
                symbol="goodFunc",
                confidence=1.0,
            ),
        )
        _insert_scope(scope_repo, "bad", "# Bad\n\n[E] src/nope.ts:1-5 :: nope\n")
        _insert_evidence(
            evidence_repo,
            "bad",
            EvidenceLink(
                raw="[E] src/nope.ts:1-5 :: nope",
                type="valid",
                filepath="src/nope.ts",
                start_line=1,
                end_line=5,
                symbol="nope",
                confidence=1.0,
            ),
        )
        conn.close()

        report = run_drift_check(str(tmp_path), 40)
        assert report.total_links == 2
        assert report.overall_health_pct == 50
        assert report.ci_pass is True  # 50 >= 40

    def test_scope_with_no_evidence_links_in_db_is_handled_correctly(self, tmp_path: Path):
        """Scopes with no evidence rows in DB should show 0 links and 100% health."""
        conn, scope_repo, _ = _setup_db(tmp_path)
        # Insert scope with no associated evidence rows
        _insert_scope(scope_repo, "empty_scope", "# No Evidence\n\nNo links here.\n")
        conn.close()

        report = run_drift_check(str(tmp_path), 80)
        assert len(report.scopes) == 1
        assert report.scopes[0].total_links == 0
        assert report.scopes[0].health_pct == 100
        assert report.total_links == 0

    def test_filters_out_unknown_and_deprecated_link_types(self, tmp_path: Path):
        _write_file(tmp_path, "src/valid.ts", "export const v = 1;\n")
        conn, scope_repo, evidence_repo = _setup_db(tmp_path)
        _insert_scope(
            scope_repo,
            "mixed",
            "# Mixed\n[E] src/valid.ts\n[Unknown] some unknown thing\n[Deprecated] src/old.ts:1-5\n",
        )
        # Only insert valid-typed link; unknown/deprecated are filtered by run_drift_check
        _insert_evidence(
            evidence_repo,
            "mixed",
            EvidenceLink(
                raw="[E] src/valid.ts",
                type="valid",
                filepath="src/valid.ts",
                confidence=1.0,
            ),
        )
        _insert_evidence(
            evidence_repo,
            "mixed",
            EvidenceLink(
                raw="[Unknown] some unknown thing",
                type="unknown",
                confidence=0.5,
            ),
        )
        _insert_evidence(
            evidence_repo,
            "mixed",
            EvidenceLink(
                raw="[Deprecated] src/old.ts:1-5",
                type="deprecated",
                filepath="src/old.ts",
                start_line=1,
                end_line=5,
                confidence=1.0,
            ),
        )
        conn.close()

        report = run_drift_check(str(tmp_path), 80)
        scope = report.scopes[0]
        assert scope.total_links == 1
        assert scope.valid_links == 1

    def test_reads_db_scopes_and_symbols_when_scope_files_are_missing(self, tmp_path: Path):
        _write_file(
            tmp_path,
            "src/db.ts",
            "// header\n// moved\nexport function dbFunc() {\n  return 1;\n}\n",
        )
        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        conn.execute(
            "INSERT INTO file_info (filepath, language, lines, size, content_hash, last_scanned) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            ("src/db.ts", "typescript", 5, 64, "hash",),
        )
        ScopeRepo(conn).create(
            Scope(id="core", name="core", summary="db scope", content="# Scope: core")
        )
        EvidenceRepo(conn).create(
            EvidenceLink(
                raw="[E] src/db.ts:1-2 :: dbFunc()",
                type="valid",
                filepath="src/db.ts",
                start_line=1,
                end_line=2,
                symbol="dbFunc",
                confidence=1.0,
            ),
            "core",
            None,
        )
        SymbolRepo(conn).create(
            filepath="src/db.ts",
            name="dbFunc",
            type="function",
            start_line=3,
            end_line=5,
        )
        conn.close()

        report = run_drift_check(str(tmp_path), 80)
        assert len(report.scopes) == 1
        scope = report.scopes[0]
        assert scope.scope == "core"
        assert scope.healed_links == 1
        assert scope.stale_links == 0


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
