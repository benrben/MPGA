"""Tests for the design-system command."""

import json
from pathlib import Path

from click.testing import CliRunner


def _seed_project(root: Path) -> Path:
    mpga_dir = root / "MPGA"
    mpga_dir.mkdir(parents=True, exist_ok=True)
    (mpga_dir / "mpga.config.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
    (root / "src" / "styles").mkdir(parents=True, exist_ok=True)
    return mpga_dir


class TestDesignSystemCommand:
    """design-system command tests."""

    def test_init_generates_tokens_json_and_tokens_css(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """init scans CSS and writes the design-system token files."""
        _seed_project(tmp_path)
        (tmp_path / "src" / "styles" / "app.css").write_text(
            ".card { color: #2563eb; margin: 16px; font-family: Georgia, serif; }\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("mpga.commands.design_system.find_project_root", lambda: tmp_path)

        from mpga.commands.design_system import design_system

        runner = CliRunner()
        result = runner.invoke(design_system, ["init"])

        assert result.exit_code == 0
        tokens_dir = tmp_path / ".mpga" / "design-system"
        assert (tokens_dir / "tokens.json").exists()
        assert (tokens_dir / "tokens.css").exists()

        payload = json.loads((tokens_dir / "tokens.json").read_text(encoding="utf-8"))
        assert payload["color"]
        assert payload["spacing"]
        assert payload["typography"]

    def test_audit_reports_hardcoded_values(self, tmp_path: Path, monkeypatch):
        """audit reports hardcoded values that should be tokenized."""
        _seed_project(tmp_path)
        (tmp_path / "src" / "styles" / "app.css").write_text(
            ".button { color: #123456; padding: 12px; }\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("mpga.commands.design_system.find_project_root", lambda: tmp_path)

        from mpga.commands.design_system import design_system

        runner = CliRunner()
        result = runner.invoke(design_system, ["audit"])

        assert result.exit_code == 0
        assert "#123456" in result.output
        assert "compliance" in result.output.lower()

    def test_audit_reports_full_compliance_for_tokenized_css(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """audit reports 100% compliance when the CSS uses custom properties."""
        _seed_project(tmp_path)
        design_dir = tmp_path / ".mpga" / "design-system"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "tokens.json").write_text(
            json.dumps(
                {
                    "color": {"primary": "#2563eb"},
                    "spacing": {"md": "16px"},
                    "typography": {},
                    "breakpoint": {},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (tmp_path / "src" / "styles" / "app.css").write_text(
            ".button { color: var(--color-primary); padding: var(--spacing-md); }\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("mpga.commands.design_system.find_project_root", lambda: tmp_path)

        from mpga.commands.design_system import design_system

        runner = CliRunner()
        result = runner.invoke(design_system, ["audit"])

        assert result.exit_code == 0
        assert "100%" in result.output

    def test_add_token_updates_json_and_css(self, tmp_path: Path, monkeypatch):
        """add-token updates both tokens.json and tokens.css."""
        _seed_project(tmp_path)
        design_dir = tmp_path / ".mpga" / "design-system"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "tokens.json").write_text(
            json.dumps(
                {
                    "color": {},
                    "spacing": {},
                    "typography": {},
                    "breakpoint": {},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (design_dir / "tokens.css").write_text(":root {\n}\n", encoding="utf-8")
        monkeypatch.setattr("mpga.commands.design_system.find_project_root", lambda: tmp_path)

        from mpga.commands.design_system import design_system

        runner = CliRunner()
        result = runner.invoke(
            design_system,
            ["add-token", "--name", "primary", "--value", "#2563eb", "--category", "color"],
        )

        assert result.exit_code == 0
        payload = json.loads((design_dir / "tokens.json").read_text(encoding="utf-8"))
        assert payload["color"]["primary"] == "#2563eb"
        assert "--color-primary: #2563eb;" in (design_dir / "tokens.css").read_text(
            encoding="utf-8"
        )

    def test_add_token_persists_sqlite_token(self, tmp_path: Path, monkeypatch):
        """add-token mirrors the token into SQLite when the DB exists."""
        _seed_project(tmp_path)
        design_dir = tmp_path / ".mpga" / "design-system"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "tokens.json").write_text(
            json.dumps(
                {
                    "color": {},
                    "spacing": {},
                    "typography": {},
                    "breakpoint": {},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (design_dir / "tokens.css").write_text(":root {\n}\n", encoding="utf-8")
        monkeypatch.setattr("mpga.commands.design_system.find_project_root", lambda: tmp_path)

        from mpga.commands.design_system import design_system
        from mpga.db.connection import get_connection
        from mpga.db.schema import create_schema

        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        create_schema(conn)
        conn.close()

        runner = CliRunner()
        result = runner.invoke(
            design_system,
            ["add-token", "--name", "primary", "--value", "#2563eb", "--category", "color"],
        )

        assert result.exit_code == 0
        conn = get_connection(str(tmp_path / ".mpga" / "mpga.db"))
        try:
            row = conn.execute(
                "SELECT category, name, value FROM design_tokens WHERE category = 'color' AND name = 'primary'"
            ).fetchone()
        finally:
            conn.close()

        assert row == ("color", "primary", "#2563eb")

    def test_audit_ignores_token_definitions_when_scoring_compliance(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """audit does not count custom-property token definitions as hardcoded drift."""
        _seed_project(tmp_path)
        (tmp_path / "src" / "styles" / "app.css").write_text(
            ":root { --color-primary: #2563eb; --spacing-md: 16px; }\n"
            ".button { color: var(--color-primary); padding: var(--spacing-md); }\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("mpga.commands.design_system.find_project_root", lambda: tmp_path)

        from mpga.commands.design_system import design_system

        runner = CliRunner()
        result = runner.invoke(design_system, ["audit"])

        assert result.exit_code == 0
        assert "100%" in result.output
        assert "No hardcoded values detected." in result.output
