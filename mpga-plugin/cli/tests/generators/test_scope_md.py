import re

from mpga.core.scanner import FileInfo
from mpga.generators.scope_md import (
    ExportDescription,
    ExportedSymbol,
    ModuleSummary,
    RuleConstraint,
    ScopeInfo,
    detect_frameworks,
    extract_annotations,
    extract_jsdoc_for_export,
    extract_module_summary,
    render_scope_md,
)

# -- extract_module_summary --


def test_extract_module_summary_extracts_leading_jsdoc_block():
    content = "/** This module handles authentication. */\nimport express from 'express';"
    assert extract_module_summary(content) == "This module handles authentication."


def test_extract_module_summary_extracts_multiline_jsdoc_skipping_tags():
    content = (
        "/**\n * Board management utilities.\n * Handles task lifecycle.\n"
        " * @module board\n */\nimport fs from 'fs';"
    )
    assert extract_module_summary(content) == (
        "Board management utilities. Handles task lifecycle."
    )


def test_extract_module_summary_extracts_leading_line_comments():
    content = (
        "// Scanner module\n// Walks the filesystem and collects file info\nimport path from 'path';"
    )
    assert extract_module_summary(content) == (
        "Scanner module Walks the filesystem and collects file info"
    )


def test_extract_module_summary_returns_none_when_no_leading_comment():
    content = "import fs from 'fs';\nconst x = 1;"
    assert extract_module_summary(content) is None


def test_extract_module_summary_ignores_jsdoc_not_at_top():
    content = "import fs from 'fs';\n/** This is a function doc */\nexport function foo() {}"
    assert extract_module_summary(content) is None


# -- detect_frameworks --


def test_detect_frameworks_detects_known_frameworks():
    content = "import express from 'express';\nimport { z } from 'zod';"
    result = detect_frameworks(content)
    assert "Express" in result
    assert "Zod" in result


def test_detect_frameworks_ignores_relative_imports():
    content = "import { foo } from './foo';\nimport bar from '../bar';"
    assert detect_frameworks(content) == []


def test_detect_frameworks_detects_require_style_imports():
    content = "const express = require('express');"
    assert "Express" in detect_frameworks(content)


def test_detect_frameworks_handles_scoped_packages():
    content = "import { Client } from '@prisma/client';"
    assert detect_frameworks(content) == []


def test_detect_frameworks_deduplicates_results():
    content = "import express from 'express';\nimport { Router } from 'express';"
    result = detect_frameworks(content)
    assert len([f for f in result if f == "Express"]) == 1


# -- extract_jsdoc_for_export --


def test_extract_jsdoc_for_export_extracts_description():
    content = "/** Load the board state from disk. */\nexport function loadBoard() {}"
    assert extract_jsdoc_for_export(content, "loadBoard") == (
        "Load the board state from disk."
    )


def test_extract_jsdoc_for_export_extracts_first_non_tag_lines():
    content = (
        "/**\n * Save the board to disk.\n * Writes JSON format.\n"
        " * @param board - the board state\n */\nexport function saveBoard(board: any) {}"
    )
    assert extract_jsdoc_for_export(content, "saveBoard") == (
        "Save the board to disk. Writes JSON format."
    )


def test_extract_jsdoc_for_export_returns_none_when_no_jsdoc():
    content = "export function noDoc() {}"
    assert extract_jsdoc_for_export(content, "noDoc") is None


def test_extract_jsdoc_for_export_returns_none_for_nonexistent_symbol():
    content = "/** Docs */\nexport function exists() {}"
    assert extract_jsdoc_for_export(content, "doesNotExist") is None


def test_extract_jsdoc_for_export_handles_async_functions():
    content = "/** Scan the filesystem. */\nexport async function scan() {}"
    assert extract_jsdoc_for_export(content, "scan") == "Scan the filesystem."


# -- extract_annotations --


def test_extract_annotations_extracts_throws():
    content = (
        "/**\n * Do something.\n * @throws Error if config is missing\n"
        " */\nexport function doThing() {}"
    )
    result = extract_annotations(content, "doThing")
    assert result == ["@throws Error if config is missing"]


def test_extract_annotations_extracts_deprecated():
    content = (
        "/**\n * Old function.\n * @deprecated Use newFunc instead\n"
        " */\nexport function oldFunc() {}"
    )
    result = extract_annotations(content, "oldFunc")
    assert result == ["@deprecated Use newFunc instead"]


def test_extract_annotations_returns_empty_when_no_annotations():
    content = "/** Simple doc. */\nexport function simple() {}"
    assert extract_annotations(content, "simple") == []


def test_extract_annotations_returns_empty_when_symbol_not_found():
    content = "/** @throws Error */\nexport function foo() {}"
    assert extract_annotations(content, "bar") == []


# -- render_scope_md integration --


_base_scope = ScopeInfo(
    name="auth",
    files=[FileInfo(filepath="src/auth/index.ts", lines=100, language="typescript", size=2000)],
    exports=[ExportedSymbol(symbol="login", filepath="src/auth/index.ts", kind="function")],
    dependencies=["db"],
    reverse_deps=["api"],
    entry_points=["src/auth/index.ts"],
    all_scope_names=["auth", "db", "api"],
    module_summaries=[],
    detected_frameworks=[],
    export_descriptions=[],
    rules_and_constraints=[],
)


def test_render_scope_md_emits_health_line():
    md = render_scope_md(_base_scope, "/proj")
    assert re.search(r"\*\*Health:\*\*", md)


def test_render_scope_md_shows_todo_when_no_module_summary():
    md = render_scope_md(_base_scope, "/proj")
    assert "<!-- TODO: Tell the people what this GREAT module does" in md


def test_render_scope_md_shows_module_summary_when_available():
    scope = ScopeInfo(
        **{
            **_base_scope.__dict__,
            "module_summaries": [
                ModuleSummary(filepath="src/auth/index.ts", summary="Authentication and session management."),
            ],
        }
    )
    md = render_scope_md(scope, "/proj")
    assert "Authentication and session management." in md
    assert "<!-- TODO: Tell the people what this GREAT module does" not in md


def test_render_scope_md_shows_todo_when_no_frameworks_detected():
    md = render_scope_md(_base_scope, "/proj")
    assert "<!-- TODO: List the frameworks. We use only the BEST." in md


def test_render_scope_md_shows_detected_frameworks():
    scope = ScopeInfo(
        **{**_base_scope.__dict__, "detected_frameworks": ["Express", "Zod"]}
    )
    md = render_scope_md(scope, "/proj")
    assert "**Frameworks:** Express, Zod" in md
    assert "<!-- TODO: List the frameworks. We use only the BEST." not in md


def test_render_scope_md_shows_todo_when_no_export_descriptions():
    md = render_scope_md(_base_scope, "/proj")
    assert "<!-- TODO: What happens here? Inputs, steps, outputs." in md


def test_render_scope_md_shows_export_descriptions():
    scope = ScopeInfo(
        **{
            **_base_scope.__dict__,
            "export_descriptions": [
                ExportDescription(
                    symbol="login",
                    filepath="src/auth/index.ts",
                    kind="function",
                    description="Authenticate a user with credentials.",
                ),
            ],
        }
    )
    md = render_scope_md(scope, "/proj")
    assert "**login** (function) \u2014 Authenticate a user with credentials." in md
    assert "<!-- TODO: What happens here? Inputs, steps, outputs." not in md


def test_render_scope_md_shows_todo_when_no_rules_constraints():
    md = render_scope_md(_base_scope, "/proj")
    assert "<!-- TODO: The guardrails. Validation, permissions, error handling" in md


def test_render_scope_md_shows_rules_and_constraints():
    scope = ScopeInfo(
        **{
            **_base_scope.__dict__,
            "rules_and_constraints": [
                RuleConstraint(
                    filepath="src/auth/index.ts",
                    symbol="login",
                    annotation="@throws Error if credentials are invalid",
                ),
            ],
        }
    )
    md = render_scope_md(scope, "/proj")
    assert "`login`: @throws Error if credentials are invalid" in md
    assert "<!-- TODO: The guardrails. Validation, permissions, error handling" not in md


def test_render_scope_md_includes_trump_style_flavor_in_summary():
    md = render_scope_md(_base_scope, "/proj")
    assert "TREMENDOUS" in md
    assert "Believe me" in md


def test_render_scope_md_includes_trump_style_flavor_in_confidence():
    md = render_scope_md(_base_scope, "/proj")
    assert "PERFECT" in md
    assert "LOW (for now)" in md


def test_render_scope_md_preserves_evidence_format():
    md = render_scope_md(_base_scope, "/proj")
    assert "[E]" in md
    assert "`src/auth/index.ts`" in md
