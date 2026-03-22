import { BoardState } from './board.js';
import { Task, Column, loadAllTasks } from './task.js';
import { progressBar } from '../core/logger.js';

const TDD_ICONS: Record<string, string> = {
  green: '🟢', red: '🔴', blue: '🔵', review: '📋', done: '✅',
};

const PRIORITY_ICONS: Record<string, string> = {
  critical: '🔴', high: '🟠', medium: '🟡', low: '⚪',
};

const STATUS_ICONS: Record<string, string> = {
  blocked: '🔴 blocked', stale: '🟡 stale', rework: '🔁 rework', paused: '⏸️ paused',
};

const WIP_LIMITS_DEFAULT: Record<string, number> = { 'in-progress': 3, testing: 3, review: 2 };

export function renderBoardMd(board: BoardState, tasksDir: string): string {
  const tasks = loadAllTasks(tasksDir);
  const byColumn: Record<Column, Task[]> = {
    backlog: [], todo: [], 'in-progress': [], testing: [], review: [], done: []
  };
  for (const task of tasks) {
    if (byColumn[task.column]) byColumn[task.column].push(task);
  }

  const { stats } = board;
  const lines: string[] = [];

  const milestone = board.milestone ?? 'No active milestone';
  lines.push(`# Board: ${milestone}`, '');

  lines.push(`**Progress: ${progressBar(stats.done, stats.total)}** (${stats.done}/${stats.total} tasks)`);
  lines.push(`**Evidence: ${progressBar(stats.evidence_produced, stats.evidence_expected)}** (${stats.evidence_produced}/${stats.evidence_expected} links produced)`);
  lines.push(`**Health: ${stats.blocked > 0 ? `⚠ ${stats.blocked} blocked task(s)` : '✓ No blocked tasks'}**`);
  lines.push('');

  // In-progress
  const wip = board.wip_limits ?? WIP_LIMITS_DEFAULT;
  const inProgress = byColumn['in-progress'];
  if (inProgress.length > 0) {
    lines.push(`## 🔴 In progress (${inProgress.length}/${wip['in-progress'] ?? 3} WIP limit)`);
    lines.push('| ID | Task | Agent | TDD | Priority |');
    lines.push('|----|------|-------|-----|----------|');
    for (const t of inProgress) {
      const tdd = t.tdd_stage ? TDD_ICONS[t.tdd_stage] + ' ' + t.tdd_stage : '—';
      const status = t.status ? STATUS_ICONS[t.status] + ' ' : '';
      lines.push(`| ${t.id} | ${status}${t.title} | ${t.assigned ?? '—'} | ${tdd} | ${PRIORITY_ICONS[t.priority]} ${t.priority} |`);
    }
    lines.push('');
  }

  // Testing
  const testing = byColumn['testing'];
  if (testing.length > 0) {
    lines.push(`## 🧪 Testing (${testing.length}/${wip['testing'] ?? 3} WIP limit)`);
    lines.push('| ID | Task | Agent | TDD | Priority |');
    lines.push('|----|------|-------|-----|----------|');
    for (const t of testing) {
      const tdd = t.tdd_stage ? TDD_ICONS[t.tdd_stage] + ' ' + t.tdd_stage : '—';
      lines.push(`| ${t.id} | ${t.title} | ${t.assigned ?? '—'} | ${tdd} | ${PRIORITY_ICONS[t.priority]} ${t.priority} |`);
    }
    lines.push('');
  }

  // Review
  const review = byColumn['review'];
  if (review.length > 0) {
    lines.push(`## 📋 Review (${review.length}/${wip['review'] ?? 2} WIP limit)`);
    lines.push('| ID | Task | Agent | Evidence | Priority |');
    lines.push('|----|------|-------|----------|----------|');
    for (const t of review) {
      const evPct = t.evidence_expected.length > 0
        ? `${t.evidence_produced.length}/${t.evidence_expected.length} ✓`
        : '—';
      lines.push(`| ${t.id} | ${t.title} | ${t.assigned ?? '—'} | ${evPct} | ${PRIORITY_ICONS[t.priority]} ${t.priority} |`);
    }
    lines.push('');
  }

  // Todo
  const todo = byColumn['todo'];
  if (todo.length > 0) {
    lines.push(`## 📥 Todo (${todo.length})`);
    lines.push('| ID | Task | Depends on | Priority |');
    lines.push('|----|------|-----------|----------|');
    for (const t of todo) {
      const deps = t.depends_on.length > 0 ? t.depends_on.join(', ') : '—';
      lines.push(`| ${t.id} | ${t.title} | ${deps} | ${PRIORITY_ICONS[t.priority]} ${t.priority} |`);
    }
    lines.push('');
  }

  // Backlog
  const backlog = byColumn['backlog'];
  if (backlog.length > 0) {
    lines.push(`## 📦 Backlog (${backlog.length})`);
    for (const t of backlog) {
      lines.push(`- ${t.id}: ${t.title}`);
    }
    lines.push('');
  }

  // Done
  const done = byColumn['done'];
  if (done.length > 0) {
    lines.push(`## ✅ Done (${done.length})`);
    lines.push('| ID | Task | Evidence produced | Completed |');
    lines.push('|----|------|-------------------|-----------|');
    for (const t of done) {
      const evCount = `${t.evidence_produced.length} links`;
      const completed = t.updated.split('T')[0];
      lines.push(`| ${t.id} | ${t.title} | ${evCount} | ${completed} |`);
    }
    lines.push('');
  }

  if (tasks.length === 0) {
    lines.push('No tasks yet. Run `/mpga:plan` to generate tasks from a milestone.');
  }

  return lines.join('\n');
}
