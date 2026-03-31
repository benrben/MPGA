"""Tests for the MCP stdio adapter exposing memory tools."""
from __future__ import annotations

import importlib


def test_mcp_module_exists() -> None:
    mod = importlib.import_module("mpga.mcp.server")
    assert mod is not None


def test_mcp_has_tools_list() -> None:
    from mpga.mcp.server import TOOLS

    assert isinstance(TOOLS, list)
    assert len(TOOLS) == 3


def test_mcp_memory_search_tool() -> None:
    from mpga.mcp.server import TOOLS

    names = {t["name"] for t in TOOLS}
    assert "memory_search" in names
    tool = next(t for t in TOOLS if t["name"] == "memory_search")
    assert "description" in tool
    assert "inputSchema" in tool


def test_mcp_memory_context_tool() -> None:
    from mpga.mcp.server import TOOLS

    names = {t["name"] for t in TOOLS}
    assert "memory_context" in names
    tool = next(t for t in TOOLS if t["name"] == "memory_context")
    assert "description" in tool
    assert "inputSchema" in tool


def test_mcp_memory_get_tool() -> None:
    from mpga.mcp.server import TOOLS

    names = {t["name"] for t in TOOLS}
    assert "memory_get" in names
    tool = next(t for t in TOOLS if t["name"] == "memory_get")
    assert "description" in tool
    assert "inputSchema" in tool
