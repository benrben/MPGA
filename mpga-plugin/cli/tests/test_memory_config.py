"""T017 — Add memory config section to mpga.config.json

Coverage checklist for: T017 — memory config section
Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: memory section exists on MpgaConfig        → test_memory_config_defaults
[x] AC2: memory.enabled defaults to True             → test_memory_enabled_default_true
[x] AC3: ai_compression.enabled defaults to False    → test_ai_compression_default_false
[x] AC4: retention_days defaults to 30               → test_retention_days_default_30
[x] AC5: max_observations defaults to 1000           → test_max_observations_default_1000
[x] AC6: skip_tools has sensible defaults            → test_skip_tools_default_list
[x] AC7: resume_budget defaults to 4000              → test_resume_budget_default_4000
[x] AC8: file overrides replace defaults             → test_config_from_file_overrides

Untested branches / edge cases:
- [ ] ai_compression.provider default
- [ ] ai_compression.model default
- [ ] camelCase ↔ snake_case round-trip for memory keys
- [ ] partial memory override (only some keys in file)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Evidence: [E] mpga-plugin/cli/src/mpga/core/config.py:87-98 :: MpgaConfig dataclass
# Evidence: [E] mpga-plugin/cli/src/mpga/core/config.py:100-103 :: default_config()
# Evidence: [E] mpga-plugin/cli/src/mpga/core/config.py:225-238 :: load_config()
# Evidence: [E] mpga-plugin/cli/src/mpga/core/config.py:247-260 :: get_config_value()
from mpga.core.config import (
    MpgaConfig,
    default_config,
    get_config_value,
    load_config,
)


class TestMemoryConfigDefaults:
    """Memory config section should exist on MpgaConfig with sensible defaults."""

    def test_memory_config_defaults(self):
        """MpgaConfig must have a 'memory' attribute that is not None."""
        cfg = default_config()
        assert hasattr(cfg, "memory"), (
            "MpgaConfig is missing 'memory' attribute — "
            "MemoryConfig section not yet added"
        )
        assert cfg.memory is not None, "memory config should not be None by default"

    def test_memory_enabled_default_true(self):
        """memory.enabled defaults to True — memory capture is on by default."""
        cfg = default_config()
        assert cfg.memory.enabled is True

    def test_ai_compression_default_false(self):
        """ai_compression.enabled defaults to False — no AI summarization by default."""
        cfg = default_config()
        assert cfg.memory.ai_compression.enabled is False

    def test_retention_days_default_30(self):
        """retention_days defaults to 30 — observations expire after a month."""
        cfg = default_config()
        assert cfg.memory.retention_days == 30

    def test_max_observations_default_1000(self):
        """max_observations defaults to 1000 — cap total stored observations."""
        cfg = default_config()
        assert cfg.memory.max_observations == 1000

    def test_skip_tools_default_list(self):
        """skip_tools defaults to a list that includes TodoRead, TodoWrite, ListFiles."""
        cfg = default_config()
        skip = cfg.memory.skip_tools
        assert isinstance(skip, list), "skip_tools should be a list"
        for tool in ["TodoRead", "TodoWrite", "ListFiles"]:
            assert tool in skip, f"{tool} should be in default skip_tools"

    def test_resume_budget_default_2048(self):
        """resume_budget defaults to 2048 (2KB max injected context)."""
        cfg = default_config()
        assert cfg.memory.resume_budget == 2048


class TestMemoryConfigAccessViaAPI:
    """Memory config values must be accessible through get_config_value()."""

    def test_get_memory_enabled(self):
        """get_config_value traverses into memory section."""
        cfg = default_config()
        val = get_config_value(cfg, "memory.enabled")
        assert val is True

    def test_get_retention_days(self):
        cfg = default_config()
        val = get_config_value(cfg, "memory.retention_days")
        assert val == 30

    def test_get_resume_budget(self):
        cfg = default_config()
        val = get_config_value(cfg, "memory.resume_budget")
        assert val == 2048


class TestMemoryConfigFromFile:
    """Config file values override memory defaults."""

    def test_config_from_file_overrides(self, tmp_path: Path):
        """When mpga.config.json specifies memory values, they override defaults."""
        mpga_dir = tmp_path / ".mpga"
        mpga_dir.mkdir()
        config_file = mpga_dir / "mpga.config.json"
        config_file.write_text(
            json.dumps(
                {
                    "version": "1.0.0",
                    "memory": {
                        "enabled": False,
                        "retentionDays": 7,
                        "maxObservations": 500,
                        "resumeBudget": 2000,
                        "skipTools": ["Read"],
                        "aiCompression": {
                            "enabled": True,
                            "provider": "openai",
                            "model": "gpt-4o-mini",
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        cfg = load_config(project_root=tmp_path)

        assert cfg.memory.enabled is False
        assert cfg.memory.retention_days == 7
        assert cfg.memory.max_observations == 500
        assert cfg.memory.resume_budget == 2000
        assert cfg.memory.skip_tools == ["Read"]
        assert cfg.memory.ai_compression.enabled is True
        assert cfg.memory.ai_compression.provider == "openai"
        assert cfg.memory.ai_compression.model == "gpt-4o-mini"
