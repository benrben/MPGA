"""Failing tests for T001 — tier field on AgentMeta and resolve_model helper.

Coverage checklist for: T001 — Add tier field + MODEL_TIERS + resolve_model to agents.py
Evidence: [E] mpga-plugin/cli/src/mpga/commands/export/agents.py:14-22 :: AgentMeta dataclass

Acceptance criteria → Test status
──────────────────────────────────
[ ] AC1: AgentMeta accepts tier="high" (no model field)   → test_agent_meta_constructed_with_tier_field
[ ] AC2: resolve_model("high", "claude") → "claude-opus-4-6"   → test_resolve_high_claude
[ ] AC3: resolve_model("mid", "claude") → "claude-sonnet-4-6"  → test_resolve_mid_claude
[ ] AC4: resolve_model("small", "claude") → "claude-haiku-4-5" → test_resolve_small_claude
[ ] AC5: resolve_model("high", "codex") → "gpt-5.4"           → test_resolve_high_codex
[ ] AC6: resolve_model("mid", "codex") → "gpt-5.3-codex"      → test_resolve_mid_codex
[ ] AC7: resolve_model("small", "codex") → "gpt-5.1-codex-mini" → test_resolve_small_codex
[ ] AC8: resolve_model("high", "antigravity") → "gemini-2.5-pro" → test_resolve_high_antigravity
[ ] AC9: unknown provider falls back to claude tier            → test_resolve_unknown_provider_falls_back
[ ] AC10: tier="invalid" is rejected                           → test_agent_meta_rejects_invalid_tier

"""

import pytest

from mpga.commands.export.agents import AgentMeta, resolve_model

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AGENT_DEFAULTS = dict(
    slug="test-agent",
    name="Test Agent",
    description="A test agent",
    readonly=False,
    is_background=False,
    sandbox_mode="workspace",
)


def _make_agent(**kwargs) -> AgentMeta:
    """Return an AgentMeta with sensible defaults, overriding via kwargs."""
    return AgentMeta(**{**_AGENT_DEFAULTS, **kwargs})


# ---------------------------------------------------------------------------
# AgentMeta tier field
# ---------------------------------------------------------------------------


class TestAgentMetaTierField:
    """AgentMeta dataclass with tier replacing model field."""

    def test_agent_meta_constructed_with_tier_field(self):
        agent = _make_agent(tier="high")
        assert agent.tier == "high"

    def test_agent_meta_rejects_invalid_tier(self):
        # Invalid value must raise ValueError at runtime (Literal is not enforced
        # by Python itself, so __post_init__ guards this explicitly).
        with pytest.raises(ValueError):
            _make_agent(tier="invalid")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# resolve_model — per-provider tier lookup
# ---------------------------------------------------------------------------


class TestResolveModelClaude:
    """resolve_model returns correct model string for claude provider."""

    def test_resolve_high_claude(self):
        assert resolve_model("high", "claude") == "claude-opus-4-6"

    def test_resolve_mid_claude(self):
        assert resolve_model("mid", "claude") == "claude-sonnet-4-6"

    def test_resolve_small_claude(self):
        assert resolve_model("small", "claude") == "claude-haiku-4-5"


class TestResolveModelCodex:
    """resolve_model returns correct model string for codex provider."""

    def test_resolve_high_codex(self):
        assert resolve_model("high", "codex") == "gpt-5.4"

    def test_resolve_mid_codex(self):
        assert resolve_model("mid", "codex") == "gpt-5.3-codex"

    def test_resolve_small_codex(self):
        assert resolve_model("small", "codex") == "gpt-5.1-codex-mini"


class TestResolveModelAntigravity:
    """resolve_model returns correct model string for antigravity provider."""

    def test_resolve_high_antigravity(self):
        assert resolve_model("high", "antigravity") == "gemini-2.5-pro"


class TestResolveModelCursor:
    """resolve_model returns correct model string for cursor provider."""

    def test_resolve_high_cursor(self):
        assert resolve_model("high", "cursor") == "claude-opus-4-6"

    def test_resolve_mid_cursor(self):
        assert resolve_model("mid", "cursor") == "claude-sonnet-4-6"


class TestResolveModelFallback:
    """resolve_model falls back to claude tier for unknown providers."""

    def test_resolve_unknown_provider_falls_back_to_claude(self):
        # Unknown provider must fall back to the claude tier map.
        assert resolve_model("high", "unknown-provider") == "claude-opus-4-6"

    def test_resolve_mid_fallback(self):
        assert resolve_model("mid", "unknown-provider") == "claude-sonnet-4-6"

    def test_resolve_small_fallback(self):
        assert resolve_model("small", "unknown-provider") == "claude-haiku-4-5"
