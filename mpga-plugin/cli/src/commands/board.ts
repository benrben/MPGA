import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import { loadBoard, recalcStats, saveBoard } from '../board/board.js';
import { renderBoardMd } from '../board/board-md.js';
import * as h from './board-handlers.js';

/** Recalculate stats, save board.json, and regenerate BOARD.md in one call. */
export function persistBoard(
  board: ReturnType<typeof loadBoard>,
  boardDir: string,
  tasksDir: string,
): void {
  recalcStats(board, tasksDir);
  saveBoard(boardDir, board);
  fs.writeFileSync(path.join(boardDir, 'BOARD.md'), renderBoardMd(board, tasksDir));
}

export function registerBoard(program: Command): void {
  const cmd = program.command('board').description('Task board management');

  cmd
    .command('show')
    .description('Display board (terminal-formatted)')
    .option('--json', 'Machine-readable output')
    .option('--milestone <id>', 'Specific milestone board')
    .action((opts) => h.handleBoardShow(opts));
  cmd
    .command('add <title>')
    .description('Create a new task')
    .option('--priority <level>', 'critical|high|medium|low', 'medium')
    .option('--scope <name>', 'Link to scope document')
    .option('--depends <task-id>', 'Add dependency (comma-separated)')
    .option('--tags <tags>', 'Comma-separated tags')
    .option('--column <col>', 'Initial column (default: backlog)', 'backlog')
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
    .action((taskId: string, opts) => h.handleBoardClaim(taskId, opts));
  cmd
    .command('assign <task-id> <agent>')
    .description('Assign task to an agent or "human"')
    .action((taskId: string, agent: string) => h.handleBoardAssign(taskId, agent));
  cmd
    .command('update <task-id>')
    .description('Update task fields')
    .option('--status <status>', 'blocked|stale|rework|paused')
    .option('--priority <level>', 'critical|high|medium|low')
    .option('--evidence-add <link>', 'Record produced evidence link')
    .option('--tdd-stage <stage>', 'green|red|blue|review|done')
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
}
