from mpga.core.config import DEFAULT_CONFIG, KnowledgeLayerConfig
from mpga.core.scanner import FileInfo, ScanResult
from mpga.generators.index_md import render_index_md
from mpga.generators.scope_md import ExportedSymbol, ScopeInfo

_minimal_scope = ScopeInfo(
    name="alpha",
    files=[],
    exports=[ExportedSymbol(symbol="x", filepath="a.ts", kind="function")],
    dependencies=[],
    reverse_deps=[],
    entry_points=[],
    all_scope_names=["alpha"],
    module_summaries=[],
    detected_frameworks=[],
    export_descriptions=[],
    rules_and_constraints=[],
)

_scan_two_files = ScanResult(
    root="/proj",
    files=[
        FileInfo(filepath="src/heavy.ts", lines=200, language="typescript", size=4000),
        FileInfo(filepath="src/light.ts", lines=20, language="typescript", size=400),
    ],
    total_files=2,
    total_lines=220,
    languages={"typescript": {"files": 2, "lines": 220}},
    entry_points=[],
    top_level_dirs=["src"],
)


def test_uses_knowledge_layer_conventions_when_provided():
    from dataclasses import replace
    config = replace(
        DEFAULT_CONFIG,
        knowledge_layer=KnowledgeLayerConfig(
            conventions=[
                "Always read INDEX before large changes.",
                "Cite [E] evidence when describing behavior.",
            ],
        ),
    )
    md = render_index_md(_scan_two_files, config, [_minimal_scope], None, 0)
    assert "Always read INDEX before large changes." in md
    assert "Cite [E] evidence when describing behavior." in md
    assert "(Add your project conventions here)" not in md


def test_uses_knowledge_layer_key_file_roles_for_matching_key_files():
    from dataclasses import replace
    config = replace(
        DEFAULT_CONFIG,
        knowledge_layer=KnowledgeLayerConfig(
            key_file_roles={
                "src/heavy.ts": "Primary module \u2014 orchestrates sync.",
            },
        ),
    )
    md = render_index_md(_scan_two_files, config, [_minimal_scope], None, 0)
    assert "| src/heavy.ts | Primary module \u2014 orchestrates sync. |" in md
    assert "| src/light.ts | (describe role) |" in md


def test_falls_back_to_placeholders_when_knowledge_layer_is_absent():
    md = render_index_md(_scan_two_files, DEFAULT_CONFIG, [_minimal_scope], None, 0)
    assert "(Add your project conventions here)" in md
    assert "| src/heavy.ts | (describe role) |" in md


def test_shows_evidence_coverage_percentage_from_sync_drift_ratio():
    md = render_index_md(_scan_two_files, DEFAULT_CONFIG, [_minimal_scope], None, 0.73)
    assert "- **Evidence coverage:** 73%" in md
