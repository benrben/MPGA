"""T045: Test that stub error views in db_dashboard.html show something useful.

The Tasks and Milestones views had broken placeholder messages like
"not yet implemented. Check back soon!" rendered in an .error div —
which is visually broken and confusing. They should either be hidden
with a TODO comment or implemented minimally.
"""
from pathlib import Path

DASHBOARD = Path("/Users/benreich/MPGA/mpga-plugin/cli/src/mpga/web/templates/db_dashboard.html")


def test_tasks_view_not_broken_stub():
    """The Tasks view must not show a broken 'not yet implemented' error message."""
    content = DASHBOARD.read_text(encoding="utf-8")
    assert "Tasks view not yet implemented" not in content, (
        "db_dashboard.html still has broken stub: 'Tasks view not yet implemented'. "
        "Either implement the view or hide it with display:none + TODO comment."
    )


def test_milestones_view_not_broken_stub():
    """The Milestones view must not show a broken 'not yet implemented' error message."""
    content = DASHBOARD.read_text(encoding="utf-8")
    assert "Milestones view not yet implemented" not in content, (
        "db_dashboard.html still has broken stub: 'Milestones view not yet implemented'. "
        "Either implement the view or hide it with display:none + TODO comment."
    )
