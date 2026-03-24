import fs from 'fs';
import path from 'path';
import type { BoardLiveSnapshot } from './live.js';

function serializeSnapshotForHtml(snapshot: BoardLiveSnapshot | null): string {
  return JSON.stringify(snapshot)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026');
}

function readEmbeddedSnapshot(boardDir: string): BoardLiveSnapshot | null {
  const snapshotPath = path.join(boardDir, 'live', 'snapshot.json');
  if (!fs.existsSync(snapshotPath)) return null;

  try {
    return JSON.parse(fs.readFileSync(snapshotPath, 'utf-8')) as BoardLiveSnapshot;
  } catch {
    return null;
  }
}

export function renderBoardLiveHtml(initialSnapshot: BoardLiveSnapshot | null = null): string {
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>MPGA Live Board</title>
    <style>
      :root {
        --bg: linear-gradient(160deg, #f3efe4 0%, #d8e1e8 48%, #f6f1e7 100%);
        --panel: rgba(255, 255, 255, 0.88);
        --ink: #1d2d35;
        --muted: #62727b;
        --line: rgba(29, 45, 53, 0.12);
        --accent: #d55d3d;
        --accent-2: #0d6b72;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        font-family: "Avenir Next", "Helvetica Neue", sans-serif;
        color: var(--ink);
        background: var(--bg);
      }
      main {
        max-width: 1400px;
        margin: 0 auto;
        padding: 32px 20px 48px;
      }
      .hero, .panel {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 24px;
        backdrop-filter: blur(16px);
        box-shadow: 0 24px 60px rgba(29, 45, 53, 0.12);
      }
      .hero {
        padding: 28px;
        margin-bottom: 24px;
      }
      .hero h1 {
        margin: 0 0 8px;
        font-size: clamp(2rem, 4vw, 3.8rem);
        letter-spacing: -0.04em;
      }
      .hero p {
        margin: 0;
        color: var(--muted);
        max-width: 72ch;
      }
      .stats, .grid {
        display: grid;
        gap: 16px;
      }
      .stats {
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        margin: 24px 0;
      }
      .stat {
        padding: 18px;
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.7);
        border: 1px solid var(--line);
      }
      .stat strong, .card strong {
        display: block;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--muted);
        margin-bottom: 8px;
      }
      .stat span {
        font-size: 1.7rem;
        font-weight: 700;
      }
      .grid {
        grid-template-columns: 2fr 1fr;
      }
      .panel {
        padding: 20px;
      }
      .board-columns {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 14px;
      }
      .column {
        border-radius: 18px;
        padding: 16px;
        background: rgba(255, 255, 255, 0.74);
        border: 1px solid var(--line);
      }
      .column h2, .panel h2 {
        margin: 0 0 14px;
        font-size: 1rem;
        letter-spacing: 0.02em;
      }
      .card {
        padding: 12px 14px;
        border-radius: 14px;
        border: 1px solid var(--line);
        background: rgba(246, 241, 231, 0.9);
        margin-bottom: 10px;
      }
      .card p, .meta, .empty, li {
        margin: 0;
        color: var(--muted);
        font-size: 0.92rem;
      }
      .meta { margin-top: 8px; }
      ul {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      li {
        padding: 10px 0;
        border-bottom: 1px solid var(--line);
      }
      li:last-child { border-bottom: 0; }
      .empty { padding: 10px 0; }
      @media (max-width: 980px) {
        .grid { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <h1>Live Board</h1>
        <p>Auto-refreshing MPGA board view. Tracks columns, active lanes, lock ownership, and recent transitions from file-backed state.</p>
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
    <script id="mpga-initial-snapshot" type="application/json">${serializeSnapshotForHtml(initialSnapshot)}</script>
    <script>
      const section = (name) => document.querySelector('[data-section="' + name + '"]');
      const embeddedSnapshotNode = document.getElementById('mpga-initial-snapshot');
      let lastSnapshot = null;

      function escapeHtml(value) {
        return String(value)
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&#39;');
      }

      function setText(node, value) {
        node.textContent = value;
      }

      function cardMeta(task) {
        return [task.priority, task.current_agent || 'unassigned', task.run_status]
          .filter(Boolean)
          .join(' · ');
      }

      function renderStats(snapshot) {
        const host = section('stats');
        host.innerHTML = '';
        const items = [
          ['Milestone', snapshot.milestone || 'none'],
          ['Tasks', String(snapshot.stats.total)],
          ['Progress', String(snapshot.stats.progress_pct) + '%'],
          ['Refresh', String(snapshot.ui.refresh_interval_ms) + 'ms'],
        ];
        for (const [label, value] of items) {
          const card = document.createElement('article');
          card.className = 'stat';
          const strong = document.createElement('strong');
          setText(strong, label);
          const span = document.createElement('span');
          setText(span, value);
          card.append(strong, span);
          host.append(card);
        }
      }

      function renderColumns(snapshot) {
        const host = section('columns');
        host.innerHTML = '';
        for (const [column, tasks] of Object.entries(snapshot.columns)) {
          const panel = document.createElement('section');
          panel.className = 'column';
          const heading = document.createElement('h2');
          setText(heading, column + ' (' + tasks.length + ')');
          panel.append(heading);
          if (tasks.length === 0) {
            const empty = document.createElement('p');
            empty.className = 'empty';
            setText(empty, 'No tasks');
            panel.append(empty);
          }
          for (const task of tasks) {
            const article = document.createElement('article');
            article.className = 'card';
            const strong = document.createElement('strong');
            setText(strong, task.id + ' · ' + task.title);
            const meta = document.createElement('p');
            meta.className = 'meta';
            setText(meta, cardMeta(task));
            article.append(strong, meta);
            panel.append(article);
          }
          host.append(panel);
        }
      }

      function renderList(name, items, mapper) {
        const host = section(name);
        host.innerHTML = '';
        if (!items.length) {
          const item = document.createElement('li');
          setText(item, 'None');
          host.append(item);
          return;
        }
        for (const value of items) {
          const item = document.createElement('li');
          setText(item, mapper(value));
          host.append(item);
        }
      }

      function collectLocks(snapshot) {
        return Object.values(snapshot.columns)
          .flat()
          .flatMap((task) => task.file_locks.map((lock) => task.id + ' · ' + lock.path + ' · ' + lock.agent));
      }

      function renderSnapshot(snapshot) {
        if (!snapshot) return;
        lastSnapshot = snapshot;
        renderStats(snapshot);
        renderColumns(snapshot);
        renderList('lanes', snapshot.active_lanes, (lane) => lane.id + ' · ' + (lane.current_agent || 'idle') + ' · ' + lane.status);
        renderList('locks', collectLocks(snapshot), (value) => value);
        renderList('events', snapshot.recent_events, (event) => JSON.stringify(event));
      }

      function loadEmbeddedSnapshot() {
        if (!embeddedSnapshotNode) return null;
        try {
          return JSON.parse(embeddedSnapshotNode.textContent || 'null');
        } catch {
          return null;
        }
      }

      async function loadSnapshot() {
        try {
          const response = await fetch('./snapshot.json?ts=' + Date.now(), { cache: 'no-store' });
          if (!response.ok) throw new Error('Snapshot fetch failed');
          renderSnapshot(await response.json());
          return;
        } catch {
          const embedded = loadEmbeddedSnapshot();
          if (embedded) {
            renderSnapshot(embedded);
            return;
          }
          if (lastSnapshot) {
            renderSnapshot(lastSnapshot);
          }
        }
      }

      renderSnapshot(loadEmbeddedSnapshot());
      loadSnapshot().catch(console.error);
      setInterval(() => loadSnapshot().catch(console.error), 2500);
      window.escapeHtml = escapeHtml;
    </script>
  </body>
</html>`;
}

export function writeBoardLiveHtml(boardDir: string): string {
  const liveDir = path.join(boardDir, 'live');
  fs.mkdirSync(liveDir, { recursive: true });
  const htmlPath = path.join(liveDir, 'index.html');
  fs.writeFileSync(htmlPath, renderBoardLiveHtml(readEmbeddedSnapshot(boardDir)));
  return htmlPath;
}
