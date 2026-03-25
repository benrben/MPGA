import fs from 'fs';
import path from 'path';
import { Command, Option } from 'commander';
import { loadBoard, recalcStats, saveBoard } from '../board/board.js';
import { loadAllTasks } from '../board/task.js';
import { renderBoardMd } from '../board/board-md.js';
import { writeBoardLiveSnapshot } from '../board/live.js';
import { writeBoardLiveHtml } from '../board/live-html.js';
import * as h from './board-handlers.js';
import { handleBoardSearch } from './board-search.js';

/** Recalculate stats, save board.json, and regenerate BOARD.md in one call. */
export function persistBoard(
  board: ReturnType<typeof loadBoard>,
  boardDir: string,
  tasksDir: string,
): void {
  const tasks = loadAllTasks(tasksDir);
  recalcStats(board, tasksDir, tasks);
  saveBoard(boardDir, board);
  fs.writeFileSync(path.join(boardDir, 'BOARD.md'), renderBoardMd(board, tasksDir, tasks));
  writeBoardLiveSnapshot(board, tasksDir, boardDir, tasks);
  writeBoardLiveHtml(boardDir);
}

export function registerBoard(program: Command): void {
  const cmd = program.command('board').description('Task board management');

  cmd
    .command('live')
    .description('Generate local auto-refresh HTML board artifacts')
    .option('--serve', 'Serve the live board through a local Node HTTP server')
    .option('--open', 'Open the served board in the default browser')
    .option('--port <port>', 'Port for the local live board server', (value) => Number(value), 4173)
    .action((opts) => h.handleBoardLive(opts));
  cmd
    .command('show')
    .description('Display board (terminal-formatted)')
    .option('--json', 'Machine-readable output')
    .option('--milestone <id>', 'Specific milestone board')
    .action((opts) => h.handleBoardShow(opts));
  cmd
    .command('add <title>')
    .description('Create a new task')
    .addOption(
      new Option('--priority <level>', 'Task priority')
        .choices(['critical', 'high', 'medium', 'low'])
        .default('medium'),
    )
    .option('--scope <name>', 'Link to scope document')
    .option('--depends <task-id>', 'Add dependency (comma-separated)')
    .option('--tags <tags>', 'Comma-separated tags')
    .addOption(
      new Option('--column <col>', 'Initial column')
        .choices(['backlog', 'todo', 'in-progress', 'testing', 'review', 'done'])
        .default('backlog'),
    )
    .option('--milestone <id>', 'Link to milestone')
    .action((title: string, opts) => h.handleBoardAdd(title, opts));
  cmd
    .command('move <task-id> <column>')
    .description('Move task between columns')
    .option('--force', 'Ignore WIP limits')
    .action((taskId: string, column: string, opts) => h.handleBoardMove(taskId, column, opts));
  cmd
    .command('claim <task-id>')
    .description('Agent claims a task (moves to in-progress)')
    .option('--agent <name>', 'Agent name')
    .option('--force', 'Ignore WIP limits')
    .action((taskId: string, opts) => h.handleBoardClaim(taskId, opts));
  cmd
    .command('assign <task-id> <agent>')
    .description('Assign task to an agent or "human"')
    .action((taskId: string, agent: string) => h.handleBoardAssign(taskId, agent));
  cmd
    .command('update <task-id>')
    .description('Update task fields')
    .addOption(
      new Option('--status <status>', 'Task status').choices([
        'blocked',
        'stale',
        'rework',
        'paused',
      ]),
    )
    .addOption(
      new Option('--priority <level>', 'Task priority').choices([
        'critical',
        'high',
        'medium',
        'low',
      ]),
    )
    .option('--evidence-add <link>', 'Record produced evidence link')
    .addOption(
      new Option('--tdd-stage <stage>', 'TDD stage').choices([
        'green',
        'red',
        'blue',
        'review',
        'done',
      ]),
    )
    .action((taskId: string, opts) => h.handleBoardUpdate(taskId, opts));
  cmd
    .command('block <task-id> <reason>')
    .description('Mark task as blocked')
    .action((taskId: string, reason: string) => h.handleBoardBlock(taskId, reason));
  cmd
    .command('unblock <task-id>')
    .description('Remove blocked status from task')
    .action((taskId: string) => h.handleBoardUnblock(taskId));
  cmd
    .command('deps <task-id>')
    .description('Show dependency tree for a task')
    .action((taskId: string) => h.handleBoardDeps(taskId));
  cmd
    .command('stats')
    .description('Board statistics')
    .action(() => h.handleBoardStats());
  cmd
    .command('archive')
    .description('Archive all done tasks to milestone directory')
    .action(() => h.handleBoardArchive());
  cmd
    .command('search [query]')
    .description('Search and filter tasks')
    .addOption(
      new Option('--priority <level>', 'Filter by priority').choices([
        'critical',
        'high',
        'medium',
        'low',
      ]),
    )
    .addOption(
      new Option('--column <col>', 'Filter by column').choices([
        'backlog',
        'todo',
        'in-progress',
        'testing',
        'review',
        'done',
      ]),
    )
    .option('--scope <name>', 'Filter by scope')
    .option('--agent <name>', 'Filter by assigned agent')
    .option('--tags <tags>', 'Filter by tags (comma-separated)')
    .action((query: string | undefined, opts) => {
      handleBoardSearch(query ?? '', {
        priority: opts.priority,
        column: opts.column,
        scope: opts.scope,
        agent: opts.agent,
        tags: opts.tags,
      });
    });
}
