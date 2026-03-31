"""MCP stdio server exposing memory tools via JSON-RPC over stdin/stdout."""
from __future__ import annotations

import json
import sys
from contextlib import closing
from pathlib import Path

from mpga.core.config import find_project_root
from mpga.db.connection import open_db

TOOLS: list[dict] = [
    {
        "name": "memory_search",
        "description": "Search observations by query string (Layer 1: compact index)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "memory_context",
        "description": "Show timeline around an observation (Layer 2: context window)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "observation_id": {"type": "integer", "description": "Observation ID"},
                "window": {"type": "integer", "description": "Observations before/after", "default": 5},
            },
            "required": ["observation_id"],
        },
    },
    {
        "name": "memory_get",
        "description": "Retrieve full observation details (Layer 3: complete record)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "observation_id": {"type": "integer", "description": "Observation ID"},
            },
            "required": ["observation_id"],
        },
    },
]

_TOOL_MAP = {t["name"]: t for t in TOOLS}


def _dispatch_memory_search(params: dict) -> dict:
    from mpga.db.search import DualIndexSearch

    root = find_project_root()
    query = params["query"]
    limit = params.get("limit", 20)
    with closing(open_db(root)) as conn:
        searcher = DualIndexSearch(conn)
        results = searcher.search(query, types=["observation"], limit=limit)
        rows = []
        for r in results:
            row = conn.execute(
                "SELECT id, type, title, created_at FROM observations WHERE id = ?",
                (int(r.entity_id),),
            ).fetchone()
            if row:
                rows.append({"id": row[0], "type": row[1], "title": row[2], "created_at": row[3]})
    return {"results": rows}


def _dispatch_memory_context(params: dict) -> dict:
    root = find_project_root()
    obs_id = params["observation_id"]
    window = params.get("window", 5)
    with closing(open_db(root)) as conn:
        row = conn.execute(
            "SELECT id, session_id, scope_id, title, type, narrative, created_at "
            "FROM observations WHERE id = ?",
            (obs_id,),
        ).fetchone()
        if row is None:
            return {"error": f"Observation {obs_id} not found"}
        obs = {"id": row[0], "title": row[3], "type": row[4], "narrative": row[5], "created_at": row[6]}
        before = conn.execute(
            "SELECT id, title, type, created_at FROM observations "
            "WHERE created_at < ? ORDER BY created_at DESC LIMIT ?",
            (row[6], window),
        ).fetchall()
        after = conn.execute(
            "SELECT id, title, type, created_at FROM observations "
            "WHERE created_at > ? ORDER BY created_at ASC LIMIT ?",
            (row[6], window),
        ).fetchall()
        timeline = [{"id": r[0], "title": r[1], "type": r[2], "created_at": r[3]} for r in reversed(before)]
        timeline.append({**obs, "current": True})
        timeline.extend({"id": r[0], "title": r[1], "type": r[2], "created_at": r[3]} for r in after)
    return {"observation": obs, "timeline": timeline}


def _dispatch_memory_get(params: dict) -> dict:
    root = find_project_root()
    obs_id = params["observation_id"]
    with closing(open_db(root)) as conn:
        row = conn.execute(
            "SELECT id, session_id, scope_id, title, type, narrative, facts, "
            "concepts, files_read, files_modified, evidence_links, created_at "
            "FROM observations WHERE id = ?",
            (obs_id,),
        ).fetchone()
        if row is None:
            return {"error": f"Observation {obs_id} not found"}
        return {
            "id": row[0], "session_id": row[1], "scope_id": row[2],
            "title": row[3], "type": row[4], "narrative": row[5],
            "facts": json.loads(row[6]) if row[6] else [],
            "concepts": json.loads(row[7]) if row[7] else [],
            "files_read": row[8] or "", "files_modified": row[9] or "",
            "evidence_links": row[10] or "", "created_at": row[11] or "",
        }


_DISPATCHERS = {
    "memory_search": _dispatch_memory_search,
    "memory_context": _dispatch_memory_context,
    "memory_get": _dispatch_memory_get,
}


def handle_request(request: dict | str) -> dict | str:
    """Dispatch a JSON-RPC request to the appropriate memory tool.

    Accepts a parsed dict or a raw JSON string. When given a string,
    returns a JSON string; when given a dict, returns a dict.
    """
    _stringify = isinstance(request, str)
    if _stringify:
        try:
            request = json.loads(request)
        except json.JSONDecodeError:
            return json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})

    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "tools/list":
        resp = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        dispatcher = _DISPATCHERS.get(tool_name)
        if dispatcher is None:
            resp = {
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }
        else:
            result = dispatcher(arguments)
            resp = {"jsonrpc": "2.0", "id": req_id, "result": result}
    else:
        resp = {
            "jsonrpc": "2.0", "id": req_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"},
        }

    return json.dumps(resp) if _stringify else resp


def main() -> None:
    """Read JSON-RPC requests from stdin, write responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
            continue
        resp = handle_request(request)
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
