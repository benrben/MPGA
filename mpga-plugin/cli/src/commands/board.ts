import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import chalk from 'chalk';
import { log, progressBar } from '../core/logger.js';
import { findProjectRoot, loadConfig } from '../core/config.js';
import {
  loadBoard, saveBoard, recalcStats, addTask, moveTask, findTaskFile, nextTaskId
} from '../board/board.js';
import { parseTaskFile, renderTaskFile, loadAllTasks, Column, Priority } from '../board/task.js';
import { renderBoardMd } from '../board/board-md.js';

function getBoardDir(projectRoot: string): string {
  return path.join(projectRoot, 'MPGA', 'board');
}
function getTasksDir(projectRoot: string): string {
  return path.join(projectRoot, 'MPGA', 'board', 'tasks');
}

export function registerBoard(program: Command): void {
  const cmd = program
    .command('board')
    .description('Task board management');

  // board show
  cmd
    .command('show')
    .description('Display board (terminal-formatted)')
    .option('--json', 'Machine-readable output')
    .option('--milestone <id>', 'Specific milestone board')
    .action((opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const boardDir = getBoardDir(projectRoot);
      const tasksDir = getTasksDir(projectRoot);

      const board = loadBoard(boardDir);
      recalcStats(board, tasksDir);

      if (opts.json) {
        const tasks = loadAllTasks(tasksDir);
        console.log(JSON.stringify({ board, tasks }, null, 2));
        return;
      }

      const mdContent = renderBoardMd(board, tasksDir);
      console.log(mdContent);
    });

  // board add
  cmd
    .command('add <title>')
    .description('Create a new task')
    .option('--priority <level>', 'critical|high|medium|low', 'medium')
    .option('--scope <name>', 'Link to scope document')
    .option('--depends <task-id>', 'Add dependency (comma-separated)')
    .option('--tags <tags>', 'Comma-separated tags')
    .option('--column <col>', 'Initial column (default: backlog)', 'backlog')
    .option('--milestone <id>', 'Link to milestone')
    .action((title: string, opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const boardDir = getBoardDir(projectRoot);
      const tasksDir = getTasksDir(projectRoot);

      const board = loadBoard(boardDir);

      const task = addTask(board, tasksDir, {
        title,
        column: opts.column as Column,
        priority: opts.priority as Priority,
        scopes: opts.scope ? [opts.scope] : [],
        depends: opts.depends ? opts.depends.split(',').map((s: string) => s.trim()) : [],
        tags: opts.tags ? opts.tags.split(',').map((s: string) => s.trim()) : [],
        milestone: opts.milestone,
      });

      recalcStats(board, tasksDir);
      saveBoard(boardDir, board);

      // Regenerate BOARD.md
      fs.writeFileSync(path.join(boardDir, 'BOARD.md'), renderBoardMd(board, tasksDir));

      log.success(`Created task ${task.id}: ${task.title}`);
      log.dim(`  Column: ${task.column}  Priority: ${task.priority}`);
    });

  // board move
  cmd
    .command('move <task-id> <column>')
    .description('Move task between columns')
    .option('--force', 'Ignore WIP limits')
    .action((taskId: string, column: string, opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const boardDir = getBoardDir(projectRoot);
      const tasksDir = getTasksDir(projectRoot);

      const board = loadBoard(boardDir);
      const result = moveTask(board, tasksDir, taskId, column as Column, opts.force);

      if (!result.success) {
        log.error(result.error ?? 'Move failed');
        process.exit(1);
      }

      recalcStats(board, tasksDir);
      saveBoard(boardDir, board);
      fs.writeFileSync(path.join(boardDir, 'BOARD.md'), renderBoardMd(board, tasksDir));

      log.success(`Moved ${taskId} → ${column}`);
    });

  // board claim
  cmd
    .command('claim <task-id>')
    .description('Agent claims a task (moves to in-progress)')
    .option('--agent <name>', 'Agent name')
    .action((taskId: string, opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const boardDir = getBoardDir(projectRoot);
      const tasksDir = getTasksDir(projectRoot);

      const board = loadBoard(boardDir);

      // Find and update the task file
      const taskFile = findTaskFile(tasksDir, taskId);
      if (!taskFile) {
        log.error(`Task '${taskId}' not found`);
        process.exit(1);
      }

      const task = parseTaskFile(taskFile);
      if (!task) { log.error('Could not parse task file'); process.exit(1); }

      task.assigned = opts.agent ?? 'agent';
      task.updated = new Date().toISOString();

      const oldColumn = task.column;
      task.column = 'in-progress';
      board.columns[oldColumn] = board.columns[oldColumn].filter(id => id !== taskId);
      board.columns['in-progress'].push(taskId);

      fs.writeFileSync(taskFile, renderTaskFile(task));
      recalcStats(board, tasksDir);
      saveBoard(boardDir, board);
      fs.writeFileSync(path.join(boardDir, 'BOARD.md'), renderBoardMd(board, tasksDir));

      log.success(`${taskId} claimed by ${task.assigned} → in-progress`);
    });

  // board assign
  cmd
    .command('assign <task-id> <agent>')
    .description('Assign task to an agent or "human"')
    .action((taskId: string, agent: string) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const tasksDir = getTasksDir(projectRoot);

      const taskFile = findTaskFile(tasksDir, taskId);
      if (!taskFile) { log.error(`Task '${taskId}' not found`); process.exit(1); }

      const task = parseTaskFile(taskFile);
      if (!task) { log.error('Could not parse task'); process.exit(1); }

      task.assigned = agent;
      task.updated = new Date().toISOString();
      fs.writeFileSync(taskFile, renderTaskFile(task));

      log.success(`${taskId} assigned to ${agent}`);
    });

  // board update
  cmd
    .command('update <task-id>')
    .description('Update task fields')
    .option('--status <status>', 'blocked|stale|rework|paused')
    .option('--priority <level>', 'critical|high|medium|low')
    .option('--evidence-add <link>', 'Record produced evidence link')
    .option('--tdd-stage <stage>', 'green|red|blue|review|done')
    .action((taskId: string, opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const boardDir = getBoardDir(projectRoot);
      const tasksDir = getTasksDir(projectRoot);

      const taskFile = findTaskFile(tasksDir, taskId);
      if (!taskFile) { log.error(`Task '${taskId}' not found`); process.exit(1); }

      const task = parseTaskFile(taskFile);
      if (!task) { log.error('Could not parse task'); process.exit(1); }

      if (opts.status) task.status = opts.status;
      if (opts.priority) task.priority = opts.priority as Priority;
      if (opts.evidenceAdd) task.evidence_produced.push(opts.evidenceAdd);
      if (opts.tddStage) task.tdd_stage = opts.tddStage;
      task.updated = new Date().toISOString();

      fs.writeFileSync(taskFile, renderTaskFile(task));

      const board = loadBoard(boardDir);
      recalcStats(board, tasksDir);
      saveBoard(boardDir, board);
      fs.writeFileSync(path.join(boardDir, 'BOARD.md'), renderBoardMd(board, tasksDir));

      log.success(`Updated ${taskId}`);
    });

  // board block
  cmd
    .command('block <task-id> <reason>')
    .description('Mark task as blocked')
    .action((taskId: string, reason: string) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const boardDir = getBoardDir(projectRoot);
      const tasksDir = getTasksDir(projectRoot);

      const taskFile = findTaskFile(tasksDir, taskId);
      if (!taskFile) { log.error(`Task '${taskId}' not found`); process.exit(1); }

      const task = parseTaskFile(taskFile);
      if (!task) { log.error('Could not parse task'); process.exit(1); }

      task.status = 'blocked';
      task.body += `\n\n## Blocked\n${new Date().toISOString()}: ${reason}\n`;
      task.updated = new Date().toISOString();
      fs.writeFileSync(taskFile, renderTaskFile(task));

      const board = loadBoard(boardDir);
      recalcStats(board, tasksDir);
      saveBoard(boardDir, board);
      fs.writeFileSync(path.join(boardDir, 'BOARD.md'), renderBoardMd(board, tasksDir));

      log.warn(`${taskId} marked as blocked: ${reason}`);
    });

  // board unblock
  cmd
    .command('unblock <task-id>')
    .description('Remove blocked status from task')
    .action((taskId: string) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const boardDir = getBoardDir(projectRoot);
      const tasksDir = getTasksDir(projectRoot);

      const taskFile = findTaskFile(tasksDir, taskId);
      if (!taskFile) { log.error(`Task '${taskId}' not found`); process.exit(1); }

      const task = parseTaskFile(taskFile);
      if (!task) { log.error('Could not parse task'); process.exit(1); }

      task.status = null;
      task.updated = new Date().toISOString();
      fs.writeFileSync(taskFile, renderTaskFile(task));

      const board = loadBoard(boardDir);
      recalcStats(board, tasksDir);
      saveBoard(boardDir, board);
      fs.writeFileSync(path.join(boardDir, 'BOARD.md'), renderBoardMd(board, tasksDir));

      log.success(`${taskId} unblocked`);
    });

  // board deps
  cmd
    .command('deps <task-id>')
    .description('Show dependency tree for a task')
    .action((taskId: string) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const tasksDir = getTasksDir(projectRoot);

      const tasks = loadAllTasks(tasksDir);
      const taskMap = new Map(tasks.map(t => [t.id, t]));

      function printDeps(id: string, indent = 0): void {
        const task = taskMap.get(id);
        const prefix = '  '.repeat(indent);
        if (!task) {
          console.log(`${prefix}${id} (not found)`);
          return;
        }
        console.log(`${prefix}${task.id}: ${task.title} [${task.column}]`);
        for (const dep of task.depends_on) printDeps(dep, indent + 1);
      }

      log.header(`Dependencies for ${taskId}`);
      printDeps(taskId);

      // Also show what this task blocks
      const blocks = tasks.filter(t => t.depends_on.includes(taskId));
      if (blocks.length > 0) {
        console.log('');
        log.dim('This task blocks:');
        for (const t of blocks) log.dim(`  ${t.id}: ${t.title}`);
      }
    });

  // board stats
  cmd
    .command('stats')
    .description('Board statistics')
    .option('--velocity', 'Tasks completed per session')
    .option('--burndown', 'Remaining work over time')
    .action((opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const boardDir = getBoardDir(projectRoot);
      const tasksDir = getTasksDir(projectRoot);

      const board = loadBoard(boardDir);
      recalcStats(board, tasksDir);

      log.header('Board Statistics');
      const { stats } = board;

      console.log(`  Total tasks:     ${stats.total}`);
      console.log(`  Done:            ${stats.done} (${stats.progress_pct}%)`);
      console.log(`  In flight:       ${stats.in_flight}`);
      console.log(`  Blocked:         ${stats.blocked}`);
      console.log(`  Evidence:        ${stats.evidence_produced}/${stats.evidence_expected} links produced`);

      const tasks = loadAllTasks(tasksDir);
      const byPriority: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
      for (const t of tasks) byPriority[t.priority] = (byPriority[t.priority] ?? 0) + 1;

      console.log('');
      log.dim('By priority:');
      for (const [p, count] of Object.entries(byPriority)) {
        if (count > 0) console.log(`  ${p.padEnd(10)} ${count}`);
      }
    });

  // board archive
  cmd
    .command('archive')
    .description('Archive all done tasks to milestone directory')
    .action(() => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const boardDir = getBoardDir(projectRoot);
      const tasksDir = getTasksDir(projectRoot);

      const board = loadBoard(boardDir);
      const doneIds = board.columns['done'];

      if (doneIds.length === 0) {
        log.info('No done tasks to archive.');
        return;
      }

      const archiveDir = board.milestone
        ? path.join(projectRoot, 'MPGA', 'milestones', board.milestone, 'tasks')
        : path.join(projectRoot, 'MPGA', 'milestones', '_archived-tasks');

      fs.mkdirSync(archiveDir, { recursive: true });

      let archived = 0;
      for (const taskId of doneIds) {
        const taskFile = findTaskFile(tasksDir, taskId);
        if (!taskFile) continue;
        const destFile = path.join(archiveDir, path.basename(taskFile));
        fs.renameSync(taskFile, destFile);
        archived++;
      }

      board.columns['done'] = [];
      recalcStats(board, tasksDir);
      saveBoard(boardDir, board);
      fs.writeFileSync(path.join(boardDir, 'BOARD.md'), renderBoardMd(board, tasksDir));

      log.success(`Archived ${archived} done task(s) to ${path.relative(projectRoot, archiveDir)}`);
    });
}
