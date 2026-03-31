"""T046: Test that unified tokens.css exists and defines CSS custom properties."""
from pathlib import Path

STATIC_DIR = Path("/Users/benreich/MPGA/mpga-plugin/cli/src/mpga/web/static")
TOKENS_CSS = STATIC_DIR / "tokens.css"


def test_tokens_css_exists():
    """tokens.css must exist in the web static directory."""
    assert TOKENS_CSS.exists(), (
        f"Missing {TOKENS_CSS}. "
        "Create a unified tokens.css with CSS custom properties for colors, spacing, typography."
    )


def test_tokens_css_defines_custom_properties():
    """tokens.css must define CSS custom properties (--variable-name: value)."""
    content = TOKENS_CSS.read_text(encoding="utf-8")
    assert "--" in content, (
        "tokens.css must define CSS custom properties (e.g. --color-primary: #...). "
        "Found no CSS custom properties."
    )
    # Should have at least colors, spacing, and typography tokens
    assert "color" in content.lower() or "bg" in content.lower(), (
        "tokens.css must define color tokens."
    )
