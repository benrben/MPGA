"""Simple prefix-based router for /api/* routes."""

from __future__ import annotations

from typing import Any, Callable


# (pattern, handler_name, path_param_name_or_None)
# Patterns are matched in order — most specific first.
_ROUTES: list[tuple[str, str, str | None]] = [
    ("/api/task-scopes/link", "task_scope_link", None),
    ("/api/task-scopes/unlink", "task_scope_unlink", None),
    ("/api/scope-tasks/", "scope_tasks", "scope_id"),
    ("/api/sessions", "sessions", None),
    ("/api/graph", "graph", None),
    ("/api/design-system", "design_system", None),
    ("/api/decisions", "decisions", None),
    ("/api/develop", "develop", None),
    ("/api/observations/search",   "observations_search",   None),
    ("/api/observations/timeline",  "observations_timeline", None),
    ("/api/observations/",          "observation_detail",    "obs_id"),
    ("/api/observations",           "observations",          None),
    ("/api/stream",       "stream",       None),
    ("/api/search",       "search",       None),
    ("/api/tasks/",       "task_detail",  "task_id"),
    ("/api/tasks",        "tasks",        None),
    ("/api/scopes/",      "scope_detail", "scope_id"),
    ("/api/scopes",       "scopes",       None),
    ("/api/evidence",     "evidence",     None),
    ("/api/board",        "board",        None),
    ("/api/milestones",   "milestones",   None),
    ("/api/stats",        "stats",        None),
    ("/api/health",       "health",       None),
]


def route(
    path: str,
    method: str = "GET",
    query_params: dict[str, str] | None = None,
) -> tuple[str, dict[str, str]] | None:
    """Match *path* against known API routes.

    Returns (handler_name, path_params_dict) or None if no route matches.
    handler_name is a string key — callers resolve to the actual callable.
    """
    for pattern, handler_name, param_name in _ROUTES:
        if param_name is not None:
            # Pattern like "/api/tasks/" expects an id segment after the slash
            if path.startswith(pattern):
                param_value = path[len(pattern):]
                if param_value:
                    return handler_name, {param_name: param_value}
        else:
            if path == pattern or path == pattern + "/":
                return handler_name, {}
    return None
