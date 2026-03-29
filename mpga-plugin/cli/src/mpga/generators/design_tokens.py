from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_COLOR_RE = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)",
    re.IGNORECASE,
)
_SPACING_RE = re.compile(r"(?<![-\w])-?\d+(?:\.\d+)?(?:px|rem|em)\b")
_FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*([^;}{]+);", re.IGNORECASE)
_BREAKPOINT_RE = re.compile(r"(?:min|max)-width\s*:\s*(\d+(?:\.\d+)?px)", re.IGNORECASE)

_UNSAFE_VALUE_MARKERS = ("url(", "expression(", "@import", "javascript:")
_CATEGORY_PREFIX = {
    "color": "color",
    "spacing": "spacing",
    "typography": "font",
    "breakpoint": "breakpoint",
}


def empty_token_set() -> dict[str, list[str]]:
    return {
        "color": [],
        "spacing": [],
        "typography": [],
        "breakpoint": [],
    }


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def extract_tokens_from_css(path: str | Path) -> dict[str, list[str]]:
    css_path = Path(path)
    if not css_path.exists():
        return empty_token_set()

    content = css_path.read_text(encoding="utf-8")
    fonts = [match.strip().strip('"').strip("'") for match in _FONT_FAMILY_RE.findall(content)]

    return {
        "color": _unique(_COLOR_RE.findall(content)),
        "spacing": _unique(_SPACING_RE.findall(content)),
        "typography": _unique([font for font in fonts if font]),
        "breakpoint": _unique(_BREAKPOINT_RE.findall(content)),
    }


def validate_token_value(value: str, category: str) -> bool:
    lowered = value.lower()
    if any(marker in lowered for marker in _UNSAFE_VALUE_MARKERS):
        return False

    validators = {
        "color": re.compile(r"^#[0-9a-fA-F]{3,8}$|^rgba?\([^)]*\)$|^hsla?\([^)]*\)$", re.IGNORECASE),
        "spacing": re.compile(r"^-?\d+(?:\.\d+)?(?:px|rem|em)$"),
        "typography": re.compile(r"^[A-Za-z0-9 ,'\-]+$"),
        "breakpoint": re.compile(r"^\d+(?:\.\d+)?(?:px|rem|em)$"),
    }

    validator = validators.get(category)
    if validator is None:
        return False
    return bool(validator.fullmatch(value.strip()))


def _normalize_category(category: str, values: Any) -> dict[str, str]:
    prefix = _CATEGORY_PREFIX[category]
    if isinstance(values, dict):
        return {str(name): str(value) for name, value in values.items()}

    if not isinstance(values, list):
        return {}

    return {f"{prefix}-{index:03d}": str(value) for index, value in enumerate(values, start=1)}


def normalize_tokens(tokens: dict[str, Any]) -> dict[str, dict[str, str]]:
    normalized: dict[str, dict[str, str]] = {}
    for category in ("color", "spacing", "typography", "breakpoint"):
        normalized[category] = _normalize_category(category, tokens.get(category, []))
    return normalized


def generate_tokens_json(tokens: dict[str, Any]) -> str:
    return json.dumps(normalize_tokens(tokens), indent=2) + "\n"


def _css_variable_name(category: str, token_name: str) -> str:
    prefix = _CATEGORY_PREFIX[category]
    if token_name.startswith(f"{prefix}-"):
        return f"--{token_name}"
    return f"--{prefix}-{token_name}"


def generate_tokens_css(tokens: dict[str, Any]) -> str:
    normalized = normalize_tokens(tokens)
    lines = [":root {"]
    for category in ("color", "spacing", "typography", "breakpoint"):
        for token_name, value in normalized[category].items():
            lines.append(f"  {_css_variable_name(category, token_name)}: {value};")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)
