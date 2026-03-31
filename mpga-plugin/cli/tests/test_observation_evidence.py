"""Tests for T029 — Extend evidence parser for observation:# references."""
from __future__ import annotations

import pytest

from mpga.evidence.parser import EvidenceLink, parse_evidence_link, parse_evidence_links


# ---------------------------------------------------------------------------
# 1. Parse observation:123 reference
# ---------------------------------------------------------------------------

def test_parse_observation_reference():
    """observation:123 is recognised as an evidence reference."""
    link = parse_evidence_link("observation:123")
    assert link is not None, "Parser should recognise observation:123"
    assert link.raw == "observation:123"


# ---------------------------------------------------------------------------
# 2. Evidence type is 'observation'
# ---------------------------------------------------------------------------

def test_observation_evidence_type():
    """Parsed observation reference has type='observation'."""
    link = parse_evidence_link("observation:456")
    assert link is not None
    assert link.type == "observation"


# ---------------------------------------------------------------------------
# 3. Observation ID extracted
# ---------------------------------------------------------------------------

def test_observation_id_extracted():
    """The numeric observation ID is extracted into the description field."""
    link = parse_evidence_link("observation:789")
    assert link is not None
    assert link.description == "789" or link.symbol == "789"
    # The ID should be accessible from the parsed link
    raw_id = link.description or link.symbol
    assert raw_id == "789"


# ---------------------------------------------------------------------------
# 4. Multiple observation refs in text
# ---------------------------------------------------------------------------

def test_multiple_observation_refs():
    """Multiple observation:N references on separate lines are all parsed."""
    content = (
        "See observation:100 for the initial discovery.\n"
        "Also related: observation:200 and observation:300\n"
    )
    links = parse_evidence_links(content)
    obs_links = [lnk for lnk in links if lnk.type == "observation"]
    assert len(obs_links) >= 3, f"Expected 3 observation refs, got {len(obs_links)}"
    ids = sorted(lnk.description or lnk.symbol or "" for lnk in obs_links)
    assert "100" in ids
    assert "200" in ids
    assert "300" in ids


# ---------------------------------------------------------------------------
# 5. Observation ref within markdown context
# ---------------------------------------------------------------------------

def test_observation_ref_in_markdown():
    """observation:N works embedded in a markdown bullet list."""
    content = (
        "## Evidence\n"
        "- [E] src/auth.ts:10-20\n"
        "- observation:42\n"
        "- [Unknown] need more info\n"
    )
    links = parse_evidence_links(content)
    obs_links = [lnk for lnk in links if lnk.type == "observation"]
    assert len(obs_links) == 1
    assert (obs_links[0].description or obs_links[0].symbol) == "42"

    all_types = {lnk.type for lnk in links}
    assert "valid" in all_types, "Should also parse [E] link"
    assert "unknown" in all_types, "Should also parse [Unknown] link"
    assert "observation" in all_types
