"""Failing tests for T003 — _generate_codex_agent_toml uses resolve_model(tier, "codex").

Coverage checklist for: T003 — codex.py uses resolve_model instead of agent.model
Evidence: [E] mpga-plugin/cli/src/mpga/commands/export/codex.py:91-111 :: _generate_codex_agent_toml()
Evidence: [E] mpga-plugin/cli/src/mpga/commands/export/agents.py:14-23 :: MODEL_TIERS, resolve_model()

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: high-tier agent generates TOML with model = "gpt-5.4"           → test_high_tier_toml_contains_gpt_5_4
[x] AC2: mid-tier agent generates TOML with model = "gpt-5.3-codex"      → test_mid_tier_toml_contains_gpt_5_3_codex
[x] AC3: small-tier agent generates TOML with model = "gpt-5.1-codex-mini"
    → test_small_tier_toml_contains_gpt_5_1_codex_mini
[x] AC4: high-tier agent TOML does NOT contain "claude-opus-4-6"
    → test_high_tier_toml_does_not_leak_claude_model

Untested branches / edge cases:
- [ ] agent.model is None (degenerate — tier-only agent, model field not set)
- [ ] provider="codex" is passed explicitly, not "claude"
"""

from mpga.commands.export.agents import AgentMeta
from mpga.commands.export.codex import _generate_codex_agent_toml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AGENT_DEFAULTS = dict(
    slug="test-agent",
    name="mpga-test-agent",
    description="A test agent for T003",
    readonly=False,
    is_background=False,
    sandbox_mode="workspace",
)


def _make_agent(**kwargs) -> AgentMeta:
    """Return an AgentMeta with sensible defaults, overriding via kwargs.
    Constructed with tier= only (no model=) to exercise the tier-based path."""
    return AgentMeta(**{**_AGENT_DEFAULTS, **kwargs})


# ---------------------------------------------------------------------------
# Degenerate: high-tier (most capable) agent → gpt-5.4
# ---------------------------------------------------------------------------


class TestCodexTomlHighTier:
    """_generate_codex_agent_toml uses codex model tier for high-tier agents."""

    def test_high_tier_toml_contains_gpt_5_4(self):
        # Arrange — tier-only agent; model field is intentionally absent
        agent = _make_agent(tier="high")

        # Act
        toml = _generate_codex_agent_toml(agent, plugin_root=None, cli_command="mpga")

        # Assert — codex high-tier model must appear in TOML
        assert 'model = "gpt-5.4"' in toml

    def test_high_tier_toml_does_not_leak_claude_model(self):
        # Arrange — simulate an agent whose legacy model field was pre-populated
        # with the claude model string (as agents.py lines 175-177 do for AGENTS list entries).
        # After the fix, the codex TOML must use the codex provider model, not this value.
        agent = _make_agent(tier="high", model="claude-opus-4-6")

        # Act
        toml = _generate_codex_agent_toml(agent, plugin_root=None, cli_command="mpga")

        # Assert — the claude model must NOT appear in a codex-targeted TOML
        assert "claude-opus-4-6" not in toml


# ---------------------------------------------------------------------------
# Simple: mid-tier agent → gpt-5.3-codex
# ---------------------------------------------------------------------------


class TestCodexTomlMidTier:
    """_generate_codex_agent_toml uses codex model tier for mid-tier agents."""

    def test_mid_tier_toml_contains_gpt_5_3_codex(self):
        # Arrange
        agent = _make_agent(tier="mid")

        # Act
        toml = _generate_codex_agent_toml(agent, plugin_root=None, cli_command="mpga")

        # Assert
        assert 'model = "gpt-5.3-codex"' in toml


# ---------------------------------------------------------------------------
# Simple: small-tier agent → gpt-5.1-codex-mini
# ---------------------------------------------------------------------------


class TestCodexTomlSmallTier:
    """_generate_codex_agent_toml uses codex model tier for small-tier agents."""

    def test_small_tier_toml_contains_gpt_5_1_codex_mini(self):
        # Arrange
        agent = _make_agent(tier="small")

        # Act
        toml = _generate_codex_agent_toml(agent, plugin_root=None, cli_command="mpga")

        # Assert
        assert 'model = "gpt-5.1-codex-mini"' in toml
