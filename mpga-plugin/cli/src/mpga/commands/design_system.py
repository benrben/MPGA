from __future__ import annotations

import json
from pathlib import Path
import re

import click

from mpga.core.config import find_project_root
from mpga.core.logger import log
from mpga.db.connection import get_connection
from mpga.db.repos.design_tokens import DesignTokenRepo
from mpga.db.schema import create_schema
from mpga.generators.design_tokens import (
    empty_token_set,
    extract_tokens_from_css,
    generate_tokens_css,
    generate_tokens_json,
    normalize_tokens,
    validate_token_value,
)

_STYLE_EXTENSIONS = {".css", ".scss", ".sass", ".less"}
_IGNORED_DIRS = {"MPGA", ".git", "node_modules", "dist", "build", ".venv", "venv"}
_COLOR_RE = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)",
    re.IGNORECASE,
)
_SPACING_RE = re.compile(r"(?<![-\w])-?\d+(?:\.\d+)?(?:px|rem|em)\b")
_CUSTOM_PROPERTY_DECL_RE = re.compile(r"^\s*--[-\w]+\s*:")


def _project_root() -> Path:
    return find_project_root() or Path.cwd()


def _design_system_dir(project_root: Path) -> Path:
    return project_root / ".mpga" / "design-system"


def _tokens_paths(project_root: Path) -> tuple[Path, Path]:
    design_dir = _design_system_dir(project_root)
    design_dir.mkdir(parents=True, exist_ok=True)
    return design_dir / "tokens.json", design_dir / "tokens.css"


def _iter_style_files(project_root: Path) -> list[Path]:
    style_files: list[Path] = []
    for path in project_root.rglob("*"):
        if path.is_dir():
            if path.name in _IGNORED_DIRS:
                continue
            continue
        if path.suffix in _STYLE_EXTENSIONS and not any(part in _IGNORED_DIRS for part in path.parts):
            style_files.append(path)
    return sorted(style_files)


def _merge_tokens(target: dict[str, list[str]], source: dict[str, list[str]]) -> None:
    for category, values in source.items():
        for value in values:
            if value not in target[category]:
                target[category].append(value)


def _load_tokens(project_root: Path) -> dict[str, dict[str, str]]:
    tokens_path, _ = _tokens_paths(project_root)
    if not tokens_path.exists():
        return normalize_tokens(empty_token_set())
    return normalize_tokens(json.loads(tokens_path.read_text(encoding="utf-8")))


def _write_tokens(project_root: Path, tokens: dict[str, dict[str, str]]) -> None:
    tokens_path, css_path = _tokens_paths(project_root)
    tokens_path.write_text(generate_tokens_json(tokens), encoding="utf-8")
    css_path.write_text(generate_tokens_css(tokens), encoding="utf-8")

    components_path = _design_system_dir(project_root) / "COMPONENTS.md"
    if not components_path.exists():
        components_path.write_text(
            "# Component Catalog\n\n- header\n- sidebar\n- card\n- form\n- table\n- modal\n",
            encoding="utf-8",
        )


def _sync_tokens_to_db(project_root: Path, tokens: dict[str, dict[str, str]]) -> None:
    db_path = project_root / ".mpga" / "mpga.db"
    if not db_path.exists():
        return

    conn = get_connection(str(db_path))
    try:
        create_schema(conn)
        repo = DesignTokenRepo(conn)
        conn.execute("DELETE FROM design_tokens")
        for category, entries in tokens.items():
            for name, value in entries.items():
                repo.upsert(category, name, value, source_file=".mpga/design-system/tokens.json")
        conn.commit()
    finally:
        conn.close()


def _is_custom_property_value(line: str, match_start: int) -> bool:
    segment_start = max(
        line.rfind("{", 0, match_start),
        line.rfind("}", 0, match_start),
        line.rfind(";", 0, match_start),
    ) + 1
    declaration_segment = line[segment_start:match_start]
    return bool(_CUSTOM_PROPERTY_DECL_RE.match(declaration_segment))


def _audit_style_file(style_path: Path) -> tuple[list[str], int, int]:
    content = style_path.read_text(encoding="utf-8")
    compliant = content.count("var(--")
    total_candidates = compliant
    findings: list[str] = []

    for line_number, line in enumerate(content.splitlines(), start=1):
        for pattern in (_COLOR_RE, _SPACING_RE):
            for match in pattern.finditer(line):
                if _is_custom_property_value(line, match.start()):
                    continue
                total_candidates += 1
                findings.append(f"{style_path}:{line_number} -> {match.group(0)}")

    if total_candidates == 0:
        return findings, 0, 0
    return findings, total_candidates, compliant


@click.group("design-system", help="Generate and audit design tokens")
def design_system() -> None:
    pass


@design_system.command("init", help="Scan style files and create the MPGA design system token files")
def design_system_init() -> None:
    project_root = _project_root()
    tokens = empty_token_set()
    for style_path in _iter_style_files(project_root):
        _merge_tokens(tokens, extract_tokens_from_css(style_path))

    normalized = normalize_tokens(tokens)
    _write_tokens(project_root, normalized)
    _sync_tokens_to_db(project_root, normalized)
    log.success(f"Generated design tokens in {_design_system_dir(project_root)}")


@design_system.command("add-token", help="Add a validated token to tokens.json and tokens.css")
@click.option("--name", required=True)
@click.option("--value", required=True)
@click.option(
    "--category",
    type=click.Choice(["color", "spacing", "typography", "breakpoint"], case_sensitive=False),
    required=True,
)
def design_system_add_token(name: str, value: str, category: str) -> None:
    project_root = _project_root()
    if not validate_token_value(value, category):
        raise click.ClickException(f"Unsafe or invalid token value for {category}: {value}")

    tokens = _load_tokens(project_root)
    tokens[category][name] = value
    _write_tokens(project_root, tokens)
    _sync_tokens_to_db(project_root, tokens)
    log.success(f"Added {category} token '{name}'")


@design_system.command("catalog", help="Show the component catalog")
def design_system_catalog() -> None:
    project_root = _project_root()
    components_path = _design_system_dir(project_root) / "COMPONENTS.md"
    if not components_path.exists():
        raise click.ClickException("No component catalog found. Run 'mpga design-system init' first.")
    click.echo(components_path.read_text(encoding="utf-8"))


@design_system.command("audit", help="Report token compliance and hardcoded style values")
def design_system_audit() -> None:
    project_root = _project_root()
    findings: list[str] = []
    total_candidates = 0
    compliant = 0

    for style_path in _iter_style_files(project_root):
        file_findings, file_total, file_compliant = _audit_style_file(style_path)
        findings.extend(file_findings)
        total_candidates += file_total
        compliant += file_compliant

    if total_candidates == 0:
        compliance = 100
    else:
        compliance = round((compliant / total_candidates) * 100)

    click.echo(f"Design-system compliance: {compliance}%")
    if findings:
        click.echo("Hardcoded values:")
        for finding in findings:
            click.echo(f"  - {finding}")
    else:
        click.echo("No hardcoded values detected.")
