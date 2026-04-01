"""T001 — Verify Stop and StopFailure hooks are registered in hooks.json."""

import json
import pathlib

HOOKS_JSON = pathlib.Path(__file__).parents[3] / "hooks" / "hooks.json"


def _load():
    return json.loads(HOOKS_JSON.read_text())


def _assert_hook_entry(hooks_dict, event_name):
    assert event_name in hooks_dict, f"hooks.json missing top-level key '{event_name}'"
    entries = hooks_dict[event_name]
    assert isinstance(entries, list) and len(entries) >= 1, (
        f"'{event_name}' must be a non-empty list"
    )
    entry = entries[0]
    assert "hooks" in entry, f"'{event_name}' entry missing 'hooks' array"
    inner = entry["hooks"]
    assert isinstance(inner, list) and len(inner) >= 1, (
        f"'{event_name}.hooks' must be a non-empty list"
    )
    cmd_hook = inner[0]
    assert cmd_hook.get("type") == "command", (
        f"'{event_name}' hook type must be 'command', got {cmd_hook.get('type')!r}"
    )
    assert "post-stop" in cmd_hook.get("command", ""), (
        f"'{event_name}' command must call 'post-stop', got {cmd_hook.get('command')!r}"
    )
    assert cmd_hook.get("async") is True, (
        f"'{event_name}' hook must have async:true, got {cmd_hook.get('async')!r}"
    )


def test_stop_hook_registered():
    data = _load()
    hooks = data["hooks"]
    _assert_hook_entry(hooks, "Stop")


def test_stop_failure_hook_registered():
    data = _load()
    hooks = data["hooks"]
    _assert_hook_entry(hooks, "StopFailure")


def test_hooks_json_is_valid_json():
    """Sanity: file must parse without error."""
    _load()
