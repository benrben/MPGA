from __future__ import annotations

import json
from pathlib import Path

from mpga.board.live import BoardLiveSnapshot, _snapshot_to_dict


def _serialize_snapshot_for_html(snapshot: BoardLiveSnapshot | None) -> str:
    if snapshot is None:
        raw = json.dumps(None)
    else:
        raw = json.dumps(_snapshot_to_dict(snapshot))
    return (
        raw
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def _read_embedded_snapshot(board_dir: str) -> BoardLiveSnapshot | None:
    snapshot_path = Path(board_dir) / "live" / "snapshot.json"
    if not snapshot_path.exists():
        return None

    try:
        raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
        # Return the raw dict wrapped as a snapshot — for HTML embedding we
        # just need it to round-trip through _snapshot_to_dict, so we
        # reconstruct a minimal BoardLiveSnapshot from the persisted JSON.
        from mpga.board.board import BoardScheduler, BoardStats, BoardUI
        from mpga.board.live import BoardLane, BoardLiveEvent, BoardLiveTaskSummary, BoardRun

        stats_raw = raw.get("stats", {})
        sched_raw = raw.get("scheduler", {})
        ui_raw = raw.get("ui", {})

        columns: dict[str, list[BoardLiveTaskSummary]] = {}
        for col, items in raw.get("columns", {}).items():
            summaries: list[BoardLiveTaskSummary] = []
            for item in items:
                summaries.append(BoardLiveTaskSummary(
                    id=item.get("id", ""),
                    title=item.get("title", ""),
                    column=item.get("column", "backlog"),
                    priority=item.get("priority", "medium"),
                    assigned=item.get("assigned"),
                    lane_id=item.get("lane_id"),
                    run_status=item.get("run_status", "queued"),
                    current_agent=item.get("current_agent"),
                    file_locks=item.get("file_locks", []),
                    scope_locks=item.get("scope_locks", []),
                ))
            columns[col] = summaries

        active_lanes: list[BoardLane] = []
        for lane_raw in raw.get("active_lanes", []):
            active_lanes.append(BoardLane(
                id=lane_raw.get("id", ""),
                task_ids=lane_raw.get("task_ids", []),
                status=lane_raw.get("status", "queued"),
                scope=lane_raw.get("scope"),
                files=lane_raw.get("files", []),
                current_agent=lane_raw.get("current_agent"),
                updated_at=lane_raw.get("updated_at", ""),
            ))

        active_runs: list[BoardRun] = []
        for run_raw in raw.get("active_runs", []):
            active_runs.append(BoardRun(
                id=run_raw.get("id", ""),
                lane_id=run_raw.get("lane_id", ""),
                task_id=run_raw.get("task_id", ""),
                status=run_raw.get("status", "queued"),
                agent=run_raw.get("agent"),
                started_at=run_raw.get("started_at", ""),
                finished_at=run_raw.get("finished_at"),
            ))

        recent_events: list[BoardLiveEvent] = []
        for ev_raw in raw.get("recent_events", []):
            recent_events.append(BoardLiveEvent(
                type=ev_raw.get("type", ""),
                lane_id=ev_raw.get("lane_id"),
                task_id=ev_raw.get("task_id"),
                status=ev_raw.get("status"),
                extra={k: v for k, v in ev_raw.items() if k not in ("type", "lane_id", "task_id", "status")},
            ))

        return BoardLiveSnapshot(
            generated_at=raw.get("generated_at", ""),
            milestone=raw.get("milestone"),
            stats=BoardStats(
                total=stats_raw.get("total", 0),
                done=stats_raw.get("done", 0),
                in_flight=stats_raw.get("in_flight", 0),
                blocked=stats_raw.get("blocked", 0),
                progress_pct=stats_raw.get("progress_pct", 0),
                evidence_produced=stats_raw.get("evidence_produced", 0),
                evidence_expected=stats_raw.get("evidence_expected", 0),
                avg_task_time=stats_raw.get("avg_task_time"),
            ),
            scheduler=BoardScheduler(
                lock_mode=sched_raw.get("lock_mode", "file"),
                max_parallel_lanes=sched_raw.get("max_parallel_lanes", 3),
                split_strategy=sched_raw.get("split_strategy", "file-groups"),
            ),
            ui=BoardUI(
                refresh_interval_ms=ui_raw.get("refresh_interval_ms", 2500),
                theme=ui_raw.get("theme", "mpga-signal"),
            ),
            columns=columns,
            active_lanes=active_lanes,
            active_runs=active_runs,
            recent_events=recent_events,
        )
    except Exception:
        return None


def render_board_live_html(initial_snapshot: BoardLiveSnapshot | None = None) -> str:
    serialized = _serialize_snapshot_for_html(initial_snapshot)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>MPGA Live Board</title>
    <style>
      :root {{
        --bg: linear-gradient(160deg, #f3efe4 0%, #d8e1e8 48%, #f6f1e7 100%);
        --panel: rgba(255, 255, 255, 0.88);
        --ink: #1d2d35;
        --muted: #62727b;
        --line: rgba(29, 45, 53, 0.12);
        --accent: #d55d3d;
        --accent-2: #0d6b72;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        font-family: "Avenir Next", "Helvetica Neue", sans-serif;
        color: var(--ink);
        background: var(--bg);
      }}
      main {{
        max-width: 1400px;
        margin: 0 auto;
        padding: 32px 20px 48px;
      }}
      .hero, .panel {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 24px;
        backdrop-filter: blur(16px);
        box-shadow: 0 24px 60px rgba(29, 45, 53, 0.12);
      }}
      .hero {{
        padding: 28px;
        margin-bottom: 24px;
      }}
      .hero h1 {{
        margin: 0 0 8px;
        font-size: clamp(2rem, 4vw, 3.8rem);
        letter-spacing: -0.04em;
      }}
      .hero p {{
        margin: 0;
        color: var(--muted);
        max-width: 72ch;
      }}
      .stats, .grid {{
        display: grid;
        gap: 16px;
      }}
      .stats {{
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        margin: 24px 0;
      }}
      .stat {{
        padding: 18px;
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.7);
        border: 1px solid var(--line);
      }}
      .stat strong, .card strong {{
        display: block;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--muted);
        margin-bottom: 8px;
      }}
      .stat span {{
        font-size: 1.7rem;
        font-weight: 700;
      }}
      .grid {{
        grid-template-columns: 2fr 1fr;
      }}
      .panel {{
        padding: 20px;
      }}
      .board-columns {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 14px;
      }}
      .column {{
        border-radius: 18px;
        padding: 16px;
        background: rgba(255, 255, 255, 0.74);
        border: 1px solid var(--line);
      }}
      .column h2, .panel h2 {{
        margin: 0 0 14px;
        font-size: 1rem;
        letter-spacing: 0.02em;
      }}
      .card {{
        padding: 12px 14px;
        border-radius: 14px;
        border: 1px solid var(--line);
        background: rgba(246, 241, 231, 0.9);
        margin-bottom: 10px;
      }}
      .card p, .meta, .empty, li {{
        margin: 0;
        color: var(--muted);
        font-size: 0.92rem;
      }}
      .meta {{ margin-top: 8px; }}
      ul {{
        list-style: none;
        padding: 0;
        margin: 0;
      }}
      li {{
        padding: 10px 0;
        border-bottom: 1px solid var(--line);
      }}
      li:last-child {{ border-bottom: 0; }}
      .empty {{ padding: 10px 0; }}
      @media (max-width: 980px) {{
        .grid {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <h1>Live Board</h1>
        <p>Auto-refreshing MPGA board view. Tracks columns, active lanes,
        lock ownership, and recent transitions from file-backed state.</p>
        <div class="stats" data-section="stats"></div>
      </section>
      <section class="grid">
        <section class="panel">
          <h2>Columns</h2>
          <div class="board-columns" data-section="columns"></div>
        </section>
        <section class="panel">
          <h2>Execution</h2>
          <div class="panel-section">
            <h2>Active Lanes</h2>
            <ul data-section="lanes"></ul>
          </div>
          <div class="panel-section">
            <h2>Locks</h2>
            <ul data-section="locks"></ul>
          </div>
          <div class="panel-section">
            <h2>Recent Events</h2>
            <ul data-section="events"></ul>
          </div>
        </section>
      </section>
    </main>
    <script id="mpga-initial-snapshot" type="application/json">{serialized}</script>
    <script>
      const section = (name) => document.querySelector('[data-section="' + name + '"]');
      const embeddedSnapshotNode = document.getElementById('mpga-initial-snapshot');
      let lastSnapshot = null;

      function escapeHtml(value) {{
        return String(value)
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&#39;');
      }}

      function setText(node, value) {{
        node.textContent = value;
      }}

      function cardMeta(task) {{
        return [task.priority, task.current_agent || 'unassigned', task.run_status]
          .filter(Boolean)
          .join(' · ');
      }}

      function renderStats(snapshot) {{
        const host = section('stats');
        host.innerHTML = '';
        const items = [
          ['Milestone', snapshot.milestone || 'none'],
          ['Tasks', String(snapshot.stats.total)],
          ['Progress', String(snapshot.stats.progress_pct) + '%'],
          ['Refresh', String(snapshot.ui.refresh_interval_ms) + 'ms'],
        ];
        for (const [label, value] of items) {{
          const card = document.createElement('article');
          card.className = 'stat';
          const strong = document.createElement('strong');
          setText(strong, label);
          const span = document.createElement('span');
          setText(span, value);
          card.append(strong, span);
          host.append(card);
        }}
      }}

      function renderColumns(snapshot) {{
        const host = section('columns');
        host.innerHTML = '';
        for (const [column, tasks] of Object.entries(snapshot.columns)) {{
          const panel = document.createElement('section');
          panel.className = 'column';
          const heading = document.createElement('h2');
          setText(heading, column + ' (' + tasks.length + ')');
          panel.append(heading);
          if (tasks.length === 0) {{
            const empty = document.createElement('p');
            empty.className = 'empty';
            setText(empty, 'No tasks');
            panel.append(empty);
          }}
          for (const task of tasks) {{
            const article = document.createElement('article');
            article.className = 'card';
            const strong = document.createElement('strong');
            setText(strong, task.id + ' · ' + task.title);
            const meta = document.createElement('p');
            meta.className = 'meta';
            setText(meta, cardMeta(task));
            article.append(strong, meta);
            panel.append(article);
          }}
          host.append(panel);
        }}
      }}

      function renderList(name, items, mapper) {{
        const host = section(name);
        host.innerHTML = '';
        if (!items.length) {{
          const item = document.createElement('li');
          setText(item, 'None');
          host.append(item);
          return;
        }}
        for (const value of items) {{
          const item = document.createElement('li');
          setText(item, mapper(value));
          host.append(item);
        }}
      }}

      function collectLocks(snapshot) {{
        return Object.values(snapshot.columns)
          .flat()
          .flatMap((task) => task.file_locks.map((lock) => task.id + ' · ' + lock.path + ' · ' + lock.agent));
      }}

      function renderSnapshot(snapshot) {{
        if (!snapshot) return;
        lastSnapshot = snapshot;
        renderStats(snapshot);
        renderColumns(snapshot);
        renderList('lanes', snapshot.active_lanes,
          (lane) => lane.id + ' · ' + (lane.current_agent || 'idle') + ' · ' + lane.status);
        renderList('locks', collectLocks(snapshot), (value) => value);
        renderList('events', snapshot.recent_events, (event) => JSON.stringify(event));
      }}

      function loadEmbeddedSnapshot() {{
        if (!embeddedSnapshotNode) return null;
        try {{
          return JSON.parse(embeddedSnapshotNode.textContent || 'null');
        }} catch {{
          return null;
        }}
      }}

      async function loadSnapshot() {{
        try {{
          const response = await fetch('./snapshot.json?ts=' + Date.now(), {{ cache: 'no-store' }});
          if (!response.ok) throw new Error('Snapshot fetch failed');
          renderSnapshot(await response.json());
          return;
        }} catch {{
          const embedded = loadEmbeddedSnapshot();
          if (embedded) {{
            renderSnapshot(embedded);
            return;
          }}
          if (lastSnapshot) {{
            renderSnapshot(lastSnapshot);
          }}
        }}
      }}

      renderSnapshot(loadEmbeddedSnapshot());
      loadSnapshot().catch(console.error);
      setInterval(() => loadSnapshot().catch(console.error), 2500);
      window.escapeHtml = escapeHtml;
    </script>
  </body>
</html>"""


def write_board_live_html(board_dir: str) -> str:
    live_dir = Path(board_dir) / "live"
    live_dir.mkdir(parents=True, exist_ok=True)
    html_path = live_dir / "index.html"
    html_path.write_text(
        render_board_live_html(_read_embedded_snapshot(board_dir)),
        encoding="utf-8",
    )
    return str(html_path)
