"""Failing tests for T004 — cursor export uses resolve_model(tier, "cursor").

Coverage checklist for: T004 — _generate_cursor_agent_md uses resolve_model(agent.tier, "cursor")
Evidence: [E] mpga-plugin/cli/src/mpga/commands/export/cursor.py:100-108 :: _generate_cursor_agent_md()
Evidence: [E] mpga-plugin/cli/src/mpga/commands/export/agents.py:14-23 :: resolve_model()

Acceptance criteria → Test status
──────────────────────────────────
[ ] AC1: high-tier agent MD contains "model: claude-opus-4-6"    → test_high_tier_agent_uses_opus_model
[ ] AC2: mid-tier agent MD contains "model: claude-sonnet-4-6"   → test_mid_tier_agent_uses_sonnet_model
[ ] AC3: small-tier agent MD contains "model: claude-haiku-4-5"  → test_small_tier_agent_uses_haiku_model
[ ] AC4: high-tier agent MD does NOT contain "model: None"        → test_high_tier_agent_does_not_leak_none

Untested branches / edge cases:
- [ ] agent with both tier AND legacy model set — cursor should prefer tier
- [ ] agent with tier=None and model=None — undefined, out of scope for T004

TPP ladder position: constant → selection (each tier forces a different branch in resolve_model)
"""

from mpga.commands.export.agents import AgentMeta
from mpga.commands.export.cursor import _generate_cursor_agent_md

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AGENT_DEFAULTS = dict(
    slug="test-agent",
    name="Test Agent",
    description="A test agent for cursor export",
    readonly=False,
    is_background=False,
    sandbox_mode="workspace",
)


def _make_agent(**kwargs) -> AgentMeta:
    """Return a tier-only AgentMeta (no model=) with sensible defaults."""
    return AgentMeta(**{**_AGENT_DEFAULTS, **kwargs})


def _frontmatter_model_line(md: str) -> str:
    """Extract the 'model: ...' line from the YAML frontmatter block."""
    for line in md.splitlines():
        if line.startswith("model:"):
            return line
    return ""


# ---------------------------------------------------------------------------
# Degenerate: high tier (opus) — first because it is the most capable tier
# and the simplest representative case to establish the behaviour exists at all.
# ---------------------------------------------------------------------------


class TestCursorAgentMdUsesResolvedModel:
    """_generate_cursor_agent_md should embed the cursor-resolved model name."""

    def test_high_tier_agent_uses_opus_model(self):
        # Arrange — tier-only agent, no legacy model field set
        agent = _make_agent(tier="high")

        # Act
        md = _generate_cursor_agent_md(agent, plugin_root=None, cli_command="mpga")

        # Assert — cursor high tier resolves to claude-opus-4-6
        assert "model: claude-opus-4-6" in md, (
            f"Expected 'model: claude-opus-4-6' in frontmatter but got: "
            f"{_frontmatter_model_line(md)!r}"
        )

    def test_mid_tier_agent_uses_sonnet_model(self):
        # Arrange
        agent = _make_agent(tier="mid")

        # Act
        md = _generate_cursor_agent_md(agent, plugin_root=None, cli_command="mpga")

        # Assert — cursor mid tier resolves to claude-sonnet-4-6
        assert "model: claude-sonnet-4-6" in md, (
            f"Expected 'model: claude-sonnet-4-6' in frontmatter but got: "
            f"{_frontmatter_model_line(md)!r}"
        )

    def test_small_tier_agent_uses_haiku_model(self):
        # Arrange
        agent = _make_agent(tier="small")

        # Act
        md = _generate_cursor_agent_md(agent, plugin_root=None, cli_command="mpga")

        # Assert — cursor small tier resolves to claude-haiku-4-5
        assert "model: claude-haiku-4-5" in md, (
            f"Expected 'model: claude-haiku-4-5' in frontmatter but got: "
            f"{_frontmatter_model_line(md)!r}"
        )

    def test_high_tier_agent_does_not_leak_none(self):
        # Arrange — tier-only agent; cursor export must never emit "model: None"
        # regardless of whether the legacy model field is populated
        agent = _make_agent(tier="high")

        # Act
        md = _generate_cursor_agent_md(agent, plugin_root=None, cli_command="mpga")

        # Assert — "model: None" must never appear in the output
        assert "model: None" not in md, (
            "Frontmatter must not contain 'model: None'; "
            f"got model line: {_frontmatter_model_line(md)!r}"
        )
