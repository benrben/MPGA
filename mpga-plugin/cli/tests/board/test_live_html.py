from mpga.board.board import BoardScheduler, BoardStats, BoardUI
from mpga.board.live import BoardLiveSnapshot, BoardLiveTaskSummary
from mpga.board.live_html import render_board_live_html


def test_renders_polling_html_shell_with_lane_and_lock_sections():
    html = render_board_live_html()
    assert "Live Board" in html
    assert "setInterval(() => loadSnapshot().catch(console.error), 2500)" in html
    assert 'data-section="lanes"' in html
    assert 'data-section="locks"' in html
    assert "mpga-initial-snapshot" in html
    assert "function loadEmbeddedSnapshot" in html


def test_embeds_safely_escaped_snapshot_for_direct_open_fallback():
    snapshot = BoardLiveSnapshot(
        generated_at="2026-03-24T19:30:00.000Z",
        milestone="M001",
        stats=BoardStats(total=1, in_flight=1),
        scheduler=BoardScheduler(),
        ui=BoardUI(),
        columns={
            "backlog": [],
            "todo": [
                BoardLiveTaskSummary(
                    id="T001",
                    title="</script><script>alert(1)</script>",
                    column="todo",
                    priority="high",
                    assigned="codex",
                ),
            ],
            "in-progress": [],
            "testing": [],
            "review": [],
            "done": [],
        },
        active_lanes=[],
        active_runs=[],
        recent_events=[],
    )
    html = render_board_live_html(snapshot)

    assert "</script><script>alert(1)</script>" not in html
    assert (
        "\\u003c/script\\u003e\\u003cscript\\u003ealert(1)\\u003c/script\\u003e" in html
    )
    assert "textContent = value" in html
