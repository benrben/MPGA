"""Tests for mpga.memory.extract — heuristic observation extractor.

Coverage checklist for: T036 — Implement heuristic observation extractor

Acceptance criteria → Test status
──────────────────────────────────
[x] AC1: extract_observation returns Observation  → test_extract_returns_observation
[x] AC2: heuristic title from Read tool context   → test_extract_title_from_read_tool
[x] AC3: heuristic title from Edit tool context   → test_extract_title_from_edit_tool
[x] AC4: classify_type default for I/O tools      → test_classify_type_tool_output
[x] AC5: classify_type detects decision            → test_classify_type_decision
[x] AC6: classify_type detects error/traceback     → test_classify_type_error
[x] AC7: classify_type detects discovery           → test_classify_type_discovery
[x] AC8: narrative synthesis from tool output      → test_narrative_from_tool_output
[x] AC9: facts field is valid JSON list            → test_facts_extraction_json
[x] AC10: concepts extraction                      → test_concepts_extraction
[x] AC11: files_read from Read tool                → test_files_read_from_read_tool
[x] AC12: files_modified from Edit tool            → test_files_modified_from_edit_tool
[x] AC13: data_hash is SHA256 (64 hex chars)       → test_data_hash_is_sha256
[x] AC14: data_hash deterministic                  → test_data_hash_deterministic
[x] AC15: data_hash varies with input              → test_data_hash_changes_with_input
[x] AC16: scope assignment from filepath           → test_scope_assignment_from_filepath

Untested branches / edge cases:
- [ ] empty tool_output (degenerate)
- [ ] tool_name not in known set (unknown tool)
- [ ] very large tool_output (truncation?)
- [ ] unicode in file paths
- [ ] tool_input with multiple file paths
"""

from __future__ import annotations

import json
import re

import pytest

# Evidence: [E] mpga-plugin/cli/src/mpga/memory/extract.py (not yet created)
# This import will FAIL — the module doesn't exist yet. That's the RED state.
from mpga.memory.extract import classify_type, extract_observation

# Evidence: [E] mpga-plugin/cli/src/mpga/db/repos/observations.py:12-27 :: Observation dataclass
from mpga.db.repos.observations import Observation


class TestExtractReturnsObservation:
    """extract_observation must return an Observation dataclass."""

    # --- TPP step 1: null/constant — simplest possible call ---

    def test_extract_returns_observation(self) -> None:
        """Calling extract_observation with minimal args returns an Observation."""
        result = extract_observation(
            tool_name="Read",
            tool_input="/src/main.py",
            tool_output="print('hello')",
        )
        assert isinstance(result, Observation)


class TestTitleGeneration:
    """Heuristic title generation from tool name and input context."""

    # --- TPP step 2: constant → variable (title varies with input) ---

    def test_extract_title_from_read_tool(self) -> None:
        """Read tool with a filepath input produces a title mentioning the file."""
        result = extract_observation(
            tool_name="Read",
            tool_input="/src/utils/helpers.py",
            tool_output="def helper(): pass",
        )
        assert result.title
        assert "helpers.py" in result.title

    def test_extract_title_from_edit_tool(self) -> None:
        """Edit tool produces a title mentioning the edited file."""
        result = extract_observation(
            tool_name="Edit",
            tool_input="/src/models/user.py",
            tool_output="File updated successfully",
        )
        assert result.title
        assert "user.py" in result.title


class TestClassifyType:
    """Type classification: tool_output, decision, discovery, pattern, error."""

    # --- TPP step 3: unconditional → selection (branching on content) ---

    def test_classify_type_tool_output(self) -> None:
        """Standard I/O tools (Read, Write, Bash) default to 'tool_output'."""
        assert classify_type("Read", "", "file contents here") == "tool_output"
        assert classify_type("Write", "", "wrote 42 bytes") == "tool_output"
        assert classify_type("Bash", "", "command output") == "tool_output"

    def test_classify_type_decision(self) -> None:
        """Output containing decision language classifies as 'decision'."""
        output = "I chose React over Vue because of the existing component library"
        assert classify_type("Assistant", "", output) == "decision"

    def test_classify_type_error(self) -> None:
        """Output containing error or traceback classifies as 'error'."""
        output = "Traceback (most recent call last):\n  File 'x.py', line 1\nValueError: bad"
        assert classify_type("Bash", "", output) == "error"

    def test_classify_type_discovery(self) -> None:
        """Output describing a new finding classifies as 'discovery'."""
        output = "Found that the API uses JWT tokens stored in httpOnly cookies"
        assert classify_type("Read", "", output) == "discovery"


class TestNarrativeSynthesis:
    """Narrative field summarizes what happened during the tool invocation."""

    # --- TPP step 4: narrative is non-empty string derived from output ---

    def test_narrative_from_tool_output(self) -> None:
        """Narrative is a non-empty string summarizing the tool interaction."""
        result = extract_observation(
            tool_name="Read",
            tool_input="/src/config.py",
            tool_output="DATABASE_URL = 'sqlite:///app.db'\nDEBUG = True\nSECRET = 'abc'",
        )
        assert result.narrative
        assert isinstance(result.narrative, str)
        assert len(result.narrative) > 10


class TestFactsExtraction:
    """Facts field must be a valid JSON list of key facts."""

    # --- TPP step 5: scalar → collection (JSON list) ---

    def test_facts_extraction_json(self) -> None:
        """facts field is a valid JSON list with at least one entry."""
        result = extract_observation(
            tool_name="Read",
            tool_input="/src/config.py",
            tool_output="DATABASE_URL = 'sqlite:///app.db'\nDEBUG = True\nPORT = 8080",
        )
        assert result.facts is not None
        parsed = json.loads(result.facts)
        assert isinstance(parsed, list)
        assert len(parsed) >= 1


class TestConceptsExtraction:
    """Concepts field captures domain-relevant terms."""

    def test_concepts_extraction(self) -> None:
        """concepts field is a valid JSON list of domain terms."""
        result = extract_observation(
            tool_name="Read",
            tool_input="/src/auth/jwt.py",
            tool_output="import jwt\ndef verify_token(token): return jwt.decode(token, SECRET)",
        )
        assert result.concepts is not None
        parsed = json.loads(result.concepts)
        assert isinstance(parsed, list)
        assert len(parsed) >= 1


class TestFilesExtraction:
    """files_read / files_modified populated from tool context."""

    # --- TPP step 6: tool-specific field population ---

    def test_files_read_from_read_tool(self) -> None:
        """Read tool populates files_read with the input filepath."""
        result = extract_observation(
            tool_name="Read",
            tool_input="/src/main.py",
            tool_output="content",
        )
        assert result.files_read is not None
        parsed = json.loads(result.files_read)
        assert isinstance(parsed, list)
        assert "/src/main.py" in parsed

    def test_files_modified_from_edit_tool(self) -> None:
        """Edit tool populates files_modified with the edited filepath."""
        result = extract_observation(
            tool_name="Edit",
            tool_input="/src/models/user.py",
            tool_output="File updated",
        )
        assert result.files_modified is not None
        parsed = json.loads(result.files_modified)
        assert isinstance(parsed, list)
        assert "/src/models/user.py" in parsed


class TestDataHash:
    """SHA256 data_hash for deduplication."""

    # --- TPP step 7: value computation (hashing) ---

    def test_data_hash_is_sha256(self) -> None:
        """data_hash is a 64-character lowercase hex string (SHA256)."""
        result = extract_observation(
            tool_name="Read",
            tool_input="/src/main.py",
            tool_output="print('hello')",
        )
        assert result.data_hash is not None
        assert re.fullmatch(r"[0-9a-f]{64}", result.data_hash)

    def test_data_hash_deterministic(self) -> None:
        """Same inputs produce the same data_hash."""
        args = dict(
            tool_name="Read",
            tool_input="/src/main.py",
            tool_output="print('hello')",
        )
        r1 = extract_observation(**args)
        r2 = extract_observation(**args)
        assert r1.data_hash == r2.data_hash

    def test_data_hash_changes_with_input(self) -> None:
        """Different tool_output produces a different data_hash."""
        r1 = extract_observation(
            tool_name="Read",
            tool_input="/src/main.py",
            tool_output="print('hello')",
        )
        r2 = extract_observation(
            tool_name="Read",
            tool_input="/src/main.py",
            tool_output="print('goodbye')",
        )
        assert r1.data_hash != r2.data_hash


class TestScopeAssignment:
    """Scope assignment via file path heuristic."""

    # --- TPP step 8: string → structured extraction ---

    def test_scope_assignment_from_filepath(self) -> None:
        """File under 'mpga-plugin/' gets scope_id 'mpga-plugin'."""
        result = extract_observation(
            tool_name="Read",
            tool_input="mpga-plugin/cli/src/mpga/db/schema.py",
            tool_output="CREATE TABLE ...",
        )
        assert result.scope_id == "mpga-plugin"
