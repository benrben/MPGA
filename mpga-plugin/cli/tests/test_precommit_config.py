"""T035: Assert .pre-commit-config.yaml exists with ruff and mpga drift hooks."""
from pathlib import Path

import yaml


PROJECT_ROOT = Path("/Users/benreich/MPGA")
PRE_COMMIT_PATH = PROJECT_ROOT / ".pre-commit-config.yaml"


def test_precommit_config_exists():
    assert PRE_COMMIT_PATH.exists(), (
        f".pre-commit-config.yaml not found at {PRE_COMMIT_PATH}"
    )


def _load_config() -> dict:
    return yaml.safe_load(PRE_COMMIT_PATH.read_text(encoding="utf-8"))


def test_ruff_hook_present():
    cfg = _load_config()
    repos = cfg.get("repos", [])
    all_hook_ids = [
        hook.get("id", "")
        for repo in repos
        for hook in repo.get("hooks", [])
    ]
    assert any("ruff" in hid for hid in all_hook_ids), (
        f"No ruff hook found. Hook IDs present: {all_hook_ids}"
    )


def test_mpga_drift_hook_present():
    cfg = _load_config()
    repos = cfg.get("repos", [])
    all_entries = [
        hook.get("entry", "") or hook.get("id", "")
        for repo in repos
        for hook in repo.get("hooks", [])
    ]
    assert any("mpga" in e or "drift" in e for e in all_entries), (
        f"No mpga drift hook found. Entries present: {all_entries}"
    )
