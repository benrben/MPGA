"""T033: Assert DEFAULT_CONFIG mutations do not bleed through to subsequent accesses."""
from mpga.core.config import get_default_config


def test_default_config_is_isolated():
    """Mutating one copy must not affect the next call."""
    cfg1 = get_default_config()
    cfg2 = get_default_config()

    # Mutate cfg1
    cfg1.project.languages = ["rust"]
    cfg1.project.name = "mutated"

    # cfg2 must be unaffected
    assert "rust" not in cfg2.project.languages, (
        "Mutation of cfg1.project.languages bled into cfg2 — DEFAULT_CONFIG is shared"
    )
    assert cfg2.project.name != "mutated", (
        "Mutation of cfg1.project.name bled into cfg2 — DEFAULT_CONFIG is shared"
    )


def test_default_config_languages_is_python():
    """Default language list should be python, not typescript."""
    cfg = get_default_config()
    assert "python" in cfg.project.languages, (
        f"Expected 'python' in default languages, got {cfg.project.languages}"
    )
