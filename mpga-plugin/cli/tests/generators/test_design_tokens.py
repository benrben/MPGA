"""Tests for the design token generator."""

import json
from pathlib import Path


class TestDesignTokens:
    """design token generator tests."""

    def test_extracts_tokens_from_css(self, tmp_path: Path):
        """Extracts color, spacing, and typography tokens from CSS."""
        css_path = tmp_path / "app.css"
        css_path.write_text(
            ".card { color: #2563eb; margin: 16px; font-family: Georgia, serif; }\n",
            encoding="utf-8",
        )

        from mpga.generators.design_tokens import extract_tokens_from_css

        tokens = extract_tokens_from_css(css_path)

        assert "#2563eb" in tokens["color"]
        assert "16px" in tokens["spacing"]
        assert "Georgia, serif" in tokens["typography"]

    def test_handles_missing_css_gracefully(self, tmp_path: Path):
        """Returns an empty token set when the CSS file is missing."""
        from mpga.generators.design_tokens import extract_tokens_from_css

        tokens = extract_tokens_from_css(tmp_path / "missing.css")

        assert tokens == {
            "color": [],
            "spacing": [],
            "typography": [],
            "breakpoint": [],
        }

    def test_generates_json_and_css_outputs(self):
        """Generates structured JSON and CSS custom properties from tokens."""
        tokens = {
            "color": ["#2563eb"],
            "spacing": ["16px"],
            "typography": ["Georgia, serif"],
            "breakpoint": [],
        }

        from mpga.generators.design_tokens import generate_tokens_css, generate_tokens_json

        json_payload = json.loads(generate_tokens_json(tokens))
        css_payload = generate_tokens_css(tokens)

        assert json_payload["color"]
        assert "--color-" in css_payload
        assert "--spacing-" in css_payload

    def test_rejects_unsafe_token_values(self):
        """Rejects unsafe design token values."""
        from mpga.generators.design_tokens import validate_token_value

        assert not validate_token_value("url(https://example.com)", "color")
        assert not validate_token_value("expression(alert(1))", "spacing")
        assert not validate_token_value("@import 'bad.css'", "typography")
