"""T016: Assert project.languages is updated from typescript-only to include python."""
import json
from pathlib import Path


CONFIG_PATH = Path("/Users/benreich/MPGA/.mpga/mpga.config.json")


def test_languages_not_typescript_only():
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    languages = data["project"]["languages"]
    assert languages != ["typescript"], (
        "project.languages is still ['typescript'] — must be updated to include python"
    )


def test_python_in_languages():
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    languages = data["project"]["languages"]
    assert "python" in languages, f"Expected 'python' in languages, got: {languages}"
