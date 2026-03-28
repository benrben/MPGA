"""Failing tests for T005 — rewrite_agent_frontmatter_model helper.

Coverage checklist for: T005 — Rewrite `model:` frontmatter in agent .md files on export
Evidence: [E] mpga-plugin/cli/src/mpga/commands/export/claude.py:87-99 :: _deploy_claude_plugin agent copy loop
Evidence: [E] mpga-plugin/cli/src/mpga/commands/export/agents.py:13-16 :: MODEL_TIERS ("mid" → claude-sonnet-4-6, "high" → claude-opus-4-6, "small" → claude-haiku-4-5)

Acceptance criteria → Test status
──────────────────────────────────
[ ] AC1: "model: sonnet" → "model: claude-sonnet-4-6" for tier "mid"   → test_rewrites_sonnet_alias_for_mid_tier
[ ] AC2: "model: opus"   → "model: claude-opus-4-6"   for tier "high"  → test_rewrites_opus_alias_for_high_tier
[ ] AC3: "model: haiku"  → "model: claude-haiku-4-5"  for tier "small" → test_rewrites_haiku_alias_for_small_tier
[ ] AC4: Non-model frontmatter lines are unchanged                      → test_preserves_non_model_frontmatter_lines
[ ] AC5: Body content after closing --- is unchanged                    → test_preserves_body_after_closing_fence
[ ] AC6: Running the function twice produces the same result (idempotent) → test_rewrite_is_idempotent

Untested branches / edge cases:
- [ ] frontmatter with no model: line (should pass through unchanged)
- [ ] content with no YAML frontmatter at all
- [ ] model: line already contains the fully-resolved ID
"""

import pytest

from mpga.commands.export.claude import rewrite_agent_frontmatter_model


# ---------------------------------------------------------------------------
# Degenerate case — minimal frontmatter, single model line
# ---------------------------------------------------------------------------


class TestRewriteAgentFrontmatterModelDegenerate:
    """Degenerate: minimal frontmatter with only a model: line."""

    def test_rewrites_sonnet_alias_for_mid_tier(self):
        # Arrange
        content = "---\nmodel: sonnet\n---\n"

        # Act
        result = rewrite_agent_frontmatter_model(content, "mid")

        # Assert
        assert "model: claude-sonnet-4-6" in result


# ---------------------------------------------------------------------------
# Simple cases — other aliases and tiers
# ---------------------------------------------------------------------------


class TestRewriteAgentFrontmatterModelSimple:
    """Simple: each supported alias maps to the correct resolved model ID."""

    def test_rewrites_opus_alias_for_high_tier(self):
        # Arrange
        content = "---\nmodel: opus\n---\n"

        # Act
        result = rewrite_agent_frontmatter_model(content, "high")

        # Assert
        assert "model: claude-opus-4-6" in result

    def test_rewrites_haiku_alias_for_small_tier(self):
        # Arrange
        content = "---\nmodel: haiku\n---\n"

        # Act
        result = rewrite_agent_frontmatter_model(content, "small")

        # Assert
        assert "model: claude-haiku-4-5" in result


# ---------------------------------------------------------------------------
# Preservation tests — surrounding content must be untouched
# ---------------------------------------------------------------------------


class TestRewriteAgentFrontmatterModelPreservation:
    """Surrounding frontmatter lines and body content must survive unchanged."""

    def test_preserves_non_model_frontmatter_lines(self):
        # Arrange — frontmatter with multiple fields alongside model:
        content = (
            "---\n"
            "name: red-dev\n"
            "model: sonnet\n"
            "description: TDD red phase\n"
            "---\n"
        )

        # Act
        result = rewrite_agent_frontmatter_model(content, "mid")

        # Assert — unrelated lines untouched
        assert "name: red-dev" in result
        assert "description: TDD red phase" in result

    def test_preserves_body_after_closing_fence(self):
        # Arrange — realistic agent .md with a prose body
        content = (
            "---\n"
            "model: sonnet\n"
            "---\n"
            "\n"
            "## Purpose\n"
            "Write failing tests first. Never write implementation.\n"
        )

        # Act
        result = rewrite_agent_frontmatter_model(content, "mid")

        # Assert — body completely unchanged
        assert "## Purpose\n" in result
        assert "Write failing tests first. Never write implementation.\n" in result


# ---------------------------------------------------------------------------
# Idempotency test
# ---------------------------------------------------------------------------


class TestRewriteAgentFrontmatterModelIdempotent:
    """Running the rewrite twice must yield the same result as running it once."""

    def test_rewrite_is_idempotent(self):
        # Arrange
        content = (
            "---\n"
            "name: green-dev\n"
            "model: sonnet\n"
            "---\n"
            "Body text.\n"
        )

        # Act
        once = rewrite_agent_frontmatter_model(content, "mid")
        twice = rewrite_agent_frontmatter_model(once, "mid")

        # Assert — second pass must not mutate the already-resolved model ID
        assert once == twice
