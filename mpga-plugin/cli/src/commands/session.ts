import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import { log } from '../core/logger.js';
import { findProjectRoot } from '../core/config.js';
import { loadBoard, recalcStats } from '../board/board.js';
import { loadAllTasks } from '../board/task.js';

/** Approximate number of tokens per line of markdown/code. */
const TOKENS_PER_LINE = 4;
/** Default context window size in tokens (e.g. Claude 200K). */
const CONTEXT_WINDOW_TOKENS = 200_000;
/** Column width for budget display name padding. */
const BUDGET_NAME_PAD_WIDTH = 30;
/** Context budget percentage below which scope usage is healthy. */
const BUDGET_HEALTHY_PCT = 10;
/** Context budget percentage above which scope usage is getting full. */
const BUDGET_FULL_PCT = 30;

function getSessionsDir(projectRoot: string): string {
  return path.join(projectRoot, 'MPGA', 'sessions');
}

export function registerSession(program: Command): void {
  const cmd = program.command('session').description('Session management and context handoff');

  // session handoff
  cmd
    .command('handoff')
    .description('Export current session state for fresh context')
    .option('--accomplished <text>', 'What was accomplished this session')
    .action((opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const sessionsDir = getSessionsDir(projectRoot);
      fs.mkdirSync(sessionsDir, { recursive: true });

      const boardDir = path.join(projectRoot, 'MPGA', 'board');
      const tasksDir = path.join(boardDir, 'tasks');

      const board = fs.existsSync(path.join(boardDir, 'board.json')) ? loadBoard(boardDir) : null;
      if (board) recalcStats(board, tasksDir);

      const tasks = loadAllTasks(tasksDir);
      const inProgress = tasks.filter((t) =>
        ['in-progress', 'testing', 'review'].includes(t.column),
      );

      const now = new Date();
      const dateStr = now.toISOString().split('T')[0];
      const timeStr = now.toISOString().replace(/[:.]/g, '-').split('T')[1].slice(0, 8);
      const filename = `${dateStr}-${timeStr}-handoff.md`;

      const content = `# Session Handoff — ${dateStr}

## Accomplished
${opts.accomplished ?? '(describe what was done this session)'}

## Current state
- **Milestone:** ${board?.milestone ?? 'none'}
- **Board:** ${board?.stats.done ?? 0}/${board?.stats.total ?? 0} tasks done (${board?.stats.progress_pct ?? 0}%)
- **In flight:** ${inProgress.length} task(s)

## In-flight tasks
${
  inProgress.length === 0
    ? '(none)'
    : inProgress
        .map(
          (t) =>
            `- **${t.id}**: ${t.title} [${t.column}${t.tdd_stage ? `, TDD: ${t.tdd_stage}` : ''}${t.assigned ? `, assigned: ${t.assigned}` : ''}]`,
        )
        .join('\n')
}

## Decisions made
| Decision | Rationale |
|----------|-----------|
| (add decisions here) | |

## Open questions
- [ ] (add unresolved questions)

## Modified files
(list key files changed this session)

## Next action
${
  inProgress.length > 0
    ? `Resume task ${inProgress[0].id}: ${inProgress[0].title} — run \`mpga board claim ${inProgress[0].id}\``
    : board && board.columns.todo.length > 0
      ? `Pick up next todo task — run \`mpga board show\``
      : 'No immediate next step — run `mpga status` to assess'
}

## How to resume
1. Load this file into context: \`cat MPGA/sessions/${filename}\`
2. Load INDEX.md: \`cat MPGA/INDEX.md\`
3. Load relevant scope(s): \`cat MPGA/scopes/<name>.md\`
4. Resume from "Next action" above
`;

      const handoffPath = path.join(sessionsDir, filename);
      fs.writeFileSync(handoffPath, content);

      log.success(`Handoff saved to MPGA/sessions/${filename}`);
      log.dim('');
      log.dim('In a new session, load with:');
      log.dim(`  cat MPGA/sessions/${filename}`);
      log.dim('  cat MPGA/INDEX.md');
    });

  // session resume
  cmd
    .command('resume')
    .description('Show most recent handoff for resuming')
    .action(() => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const sessionsDir = getSessionsDir(projectRoot);

      if (!fs.existsSync(sessionsDir)) {
        log.info('No session handoffs found. Run `mpga session handoff` at end of sessions.');
        return;
      }

      const files = fs
        .readdirSync(sessionsDir)
        .filter((f) => f.endsWith('-handoff.md'))
        .sort()
        .reverse();

      if (files.length === 0) {
        log.info('No handoff files found.');
        return;
      }

      const latestPath = path.join(sessionsDir, files[0]);
      const content = fs.readFileSync(latestPath, 'utf-8');
      console.log(content);
      log.dim(`─── From: MPGA/sessions/${files[0]} ───`);
    });

  // session log
  cmd
    .command('log <message>')
    .description('Record a session decision or note')
    .action((message: string) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const sessionsDir = getSessionsDir(projectRoot);
      fs.mkdirSync(sessionsDir, { recursive: true });

      const logPath = path.join(sessionsDir, 'session-log.md');
      const now = new Date().toISOString();

      const entry = `\n- ${now}: ${message}\n`;
      if (fs.existsSync(logPath)) {
        fs.appendFileSync(logPath, entry);
      } else {
        fs.writeFileSync(logPath, `# Session Log\n${entry}`);
      }

      log.success(`Logged: ${message}`);
    });

  // session budget
  cmd
    .command('budget')
    .description('Estimate context window usage from MPGA layer')
    .action(() => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const mpgaDir = path.join(projectRoot, 'MPGA');

      const estimates: Array<{ name: string; lines: number; tier: string }> = [];

      // INDEX.md
      const indexPath = path.join(mpgaDir, 'INDEX.md');
      if (fs.existsSync(indexPath)) {
        const lines = fs.readFileSync(indexPath, 'utf-8').split('\n').length;
        estimates.push({ name: 'INDEX.md', lines, tier: 'Tier 1 (hot)' });
      }

      // Scope docs
      const scopesDir = path.join(mpgaDir, 'scopes');
      if (fs.existsSync(scopesDir)) {
        for (const f of fs.readdirSync(scopesDir).filter((f) => f.endsWith('.md'))) {
          const lines = fs.readFileSync(path.join(scopesDir, f), 'utf-8').split('\n').length;
          estimates.push({ name: `scopes/${f}`, lines, tier: 'Tier 2 (warm)' });
        }
      }

      log.header('Context Budget');
      let total = 0;
      for (const e of estimates) {
        console.log(
          `  ${e.name.padEnd(BUDGET_NAME_PAD_WIDTH)} ${String(e.lines).padStart(5)} lines  [${e.tier}]`,
        );
        total += e.lines;
      }
      console.log('');
      console.log(
        `  Total MPGA context:  ${total} lines (~${Math.round(total * TOKENS_PER_LINE)} tokens)`,
      );
      const pct = Math.round(((total * TOKENS_PER_LINE) / CONTEXT_WINDOW_TOKENS) * 100);
      console.log(`  % of ${CONTEXT_WINDOW_TOKENS / 1000}K window:    ~${pct}%`);
      console.log('');

      if (pct < BUDGET_HEALTHY_PCT) log.success(`Healthy — room for more scope docs`);
      else if (pct < BUDGET_FULL_PCT)
        log.info(`Getting full — consider using fewer scope docs per session`);
      else log.warn(`Context heavy — consider running /mpga:handoff and starting fresh`);
    });
}
