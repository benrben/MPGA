"""Tests for the wireframe command."""

from pathlib import Path

from click.testing import CliRunner


def _seed_project(root: Path, milestone: str = "M007-ui-ux-design-layer") -> Path:
    mpga_dir = root / "MPGA"
    (mpga_dir / "milestones" / milestone).mkdir(parents=True, exist_ok=True)
    (mpga_dir / "board" / "tasks").mkdir(parents=True, exist_ok=True)
    (mpga_dir / "scopes").mkdir(parents=True, exist_ok=True)
    (mpga_dir / "mpga.config.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
    (mpga_dir / "INDEX.md").write_text(
        "# Project: demo\n\n## Active milestone\n- M007-ui-ux-design-layer\n",
        encoding="utf-8",
    )
    return mpga_dir


class TestWireframeCommand:
    """wireframe command tests."""

    def test_generates_wireframe_artifacts_for_current_milestone(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Creates wireframe artifacts inside the active milestone design directory."""
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()
        result = runner.invoke(wireframe_cmd, ["login page", "--screens", "2"])

        assert result.exit_code == 0
        wireframes_dir = (
            tmp_path
            / "MPGA"
            / "milestones"
            / "M007-ui-ux-design-layer"
            / "design"
            / "wireframes"
        )
        assert wireframes_dir.is_dir()
        assert (wireframes_dir / "screen-1.html").exists()
        assert (wireframes_dir / "screen-1.svg").exists()
        assert (wireframes_dir / "screen-1.txt").exists()
        assert "Renderer" in result.output

    def test_help_shows_usage(self):
        """Shows usage help for the wireframe command."""
        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()
        result = runner.invoke(wireframe_cmd, ["--help"])

        assert result.exit_code == 0
        assert "wireframe" in result.output
        assert "--screens" in result.output

    def test_escapes_user_content_in_html_and_svg_outputs(
        self,
        tmp_path: Path,
        monkeypatch,
    ):
        """Escapes user-supplied content before writing HTML and SVG artifacts."""
        _seed_project(tmp_path)
        monkeypatch.setattr("mpga.commands.wireframe.find_project_root", lambda: tmp_path)

        from mpga.commands.wireframe import wireframe_cmd

        runner = CliRunner()
        payload = '<script>alert(1)</script>'
        result = runner.invoke(wireframe_cmd, [payload])

        assert result.exit_code == 0
        wireframes_dir = (
            tmp_path
            / "MPGA"
            / "milestones"
            / "M007-ui-ux-design-layer"
            / "design"
            / "wireframes"
        )
        html_output = (wireframes_dir / "screen-1.html").read_text(encoding="utf-8")
        svg_output = (wireframes_dir / "screen-1.svg").read_text(encoding="utf-8")

        assert payload not in html_output
        assert payload not in svg_output
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_output
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in svg_output
