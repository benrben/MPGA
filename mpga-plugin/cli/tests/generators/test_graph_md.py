from pathlib import Path

import pytest

from mpga.generators.graph_md import build_graph
from mpga.core.scanner import ScanResult, FileInfo


def _scan_fixture(files):
    total_lines = sum(f.lines for f in files)
    return ScanResult(
        root="/proj",
        files=files,
        total_files=len(files),
        total_lines=total_lines,
        languages={"typescript": {"files": len(files), "lines": total_lines}},
        entry_points=[],
        top_level_dirs=["src"],
    )


def test_does_not_mark_files_in_imported_modules_as_orphans(tmp_path: Path):
    scan = _scan_fixture(
        [
            FileInfo(filepath="src/api/handler.ts", lines=10, language="typescript", size=100),
            FileInfo(filepath="src/core/util.ts", lines=5, language="typescript", size=50),
        ]
    )

    (tmp_path / "src" / "api").mkdir(parents=True)
    (tmp_path / "src" / "core").mkdir(parents=True)
    (tmp_path / "src" / "api" / "handler.ts").write_text(
        "import { help } from '../core/util';\nexport const x = help;\n"
    )
    (tmp_path / "src" / "core" / "util.ts").write_text(
        "export function help() { return 1; }\n"
    )

    local_scan = ScanResult(
        root=str(tmp_path),
        files=scan.files,
        total_files=scan.total_files,
        total_lines=scan.total_lines,
        languages=scan.languages,
        entry_points=scan.entry_points,
        top_level_dirs=scan.top_level_dirs,
    )

    graph = build_graph(local_scan)

    assert "src/core/util.ts" not in graph.orphans


def test_lists_files_only_in_modules_with_no_graph_edges_as_orphans(tmp_path: Path):
    (tmp_path / "src" / "island").mkdir(parents=True)
    (tmp_path / "src" / "island" / "alone.ts").write_text("export const solo = 1;\n")

    local_scan = _scan_fixture(
        [FileInfo(filepath="src/island/alone.ts", lines=2, language="typescript", size=20)]
    )
    full_scan = ScanResult(
        root=str(tmp_path),
        files=local_scan.files,
        total_files=local_scan.total_files,
        total_lines=local_scan.total_lines,
        languages=local_scan.languages,
        entry_points=local_scan.entry_points,
        top_level_dirs=local_scan.top_level_dirs,
    )

    graph = build_graph(full_scan)

    assert "src/island/alone.ts" in graph.orphans
