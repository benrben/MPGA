"""Tests for shortcut commands (diagnose, secure, simplify)."""


from click.testing import CliRunner


class TestDiagnoseShortcut:
    """diagnose shortcut tests."""

    def test_prints_skill_instruction(self):
        """Prints instruction to use /mpga:diagnose skill."""
        from mpga.commands.shortcuts import diagnose_cmd

        runner = CliRunner()
        result = runner.invoke(diagnose_cmd, [])
        assert result.exit_code == 0
        assert "/mpga:diagnose" in result.output
        assert "bug-hunter" in result.output

    def test_accepts_optional_file_arguments(self):
        """Accepts optional file arguments."""
        from mpga.commands.shortcuts import diagnose_cmd

        runner = CliRunner()
        result = runner.invoke(diagnose_cmd, ["src/foo.ts", "src/bar.ts"])
        assert result.exit_code == 0
        assert "/mpga:diagnose" in result.output
        assert "src/foo.ts" in result.output
        assert "src/bar.ts" in result.output


class TestSecureShortcut:
    """secure shortcut tests."""

    def test_prints_skill_instruction(self):
        """Prints instruction to use /mpga:secure skill."""
        from mpga.commands.shortcuts import secure_cmd

        runner = CliRunner()
        result = runner.invoke(secure_cmd, [])
        assert result.exit_code == 0
        assert "/mpga:secure" in result.output
        assert "security" in result.output.lower()


class TestSimplifyShortcut:
    """simplify shortcut tests."""

    def test_prints_skill_instruction(self):
        """Prints instruction to use /mpga:simplify skill."""
        from mpga.commands.shortcuts import simplify_cmd

        runner = CliRunner()
        result = runner.invoke(simplify_cmd, [])
        assert result.exit_code == 0
        assert "/mpga:simplify" in result.output
        assert "elegance" in result.output

    def test_accepts_optional_file_arguments(self):
        """Accepts optional file arguments."""
        from mpga.commands.shortcuts import simplify_cmd

        runner = CliRunner()
        result = runner.invoke(simplify_cmd, ["src/utils.ts"])
        assert result.exit_code == 0
        assert "/mpga:simplify" in result.output
        assert "src/utils.ts" in result.output
