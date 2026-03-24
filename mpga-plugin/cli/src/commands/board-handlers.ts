import fs from 'fs';
import path from 'path';
import { log } from '../core/logger.js';
import { findProjectRoot } from '../core/config.js';
import { loadBoard, recalcStats, addTask, moveTask, findTaskFile } from '../board/board.js';
import { parseTaskFile, renderTaskFile, loadAllTasks, Column, Priority } from '../board/task.js';
import { renderBoardMd } from '../board/board-md.js';
import { persistBoard } from './board.js';

export function getBoardDir(projectRoot: string): string {
  return path.join(projectRoot, 'MPGA', 'board');
}

export function getTasksDir(projectRoot: string): string {
  return path.join(projectRoot, 'MPGA', 'board', 'tasks');
}

export function handleBoardShow(opts: { json?: boolean; milestone?: string }): void {
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
}

export function handleBoardAdd(
  title: string,
  opts: {
    priority?: string;
    scope?: string;
    depends?: string;
    tags?: string;
    column?: string;
    milestone?: string;
  },
): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const boardDir = getBoardDir(projectRoot);
  const tasksDir = getTasksDir(projectRoot);

  const board = loadBoard(boardDir);

  const task = addTask(board, tasksDir, {
    title,
    column: (opts.column ?? 'backlog') as Column,
    priority: (opts.priority ?? 'medium') as Priority,
    scopes: opts.scope ? [opts.scope] : [],
    depends: opts.depends ? opts.depends.split(',').map((s: string) => s.trim()) : [],
    tags: opts.tags ? opts.tags.split(',').map((s: string) => s.trim()) : [],
    milestone: opts.milestone,
  });

  persistBoard(board, boardDir, tasksDir);

  log.success(`Created task ${task.id}: ${task.title}`);
  log.dim(`  Column: ${task.column}  Priority: ${task.priority}`);
}

export function handleBoardMove(taskId: string, column: string, opts: { force?: boolean }): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const boardDir = getBoardDir(projectRoot);
  const tasksDir = getTasksDir(projectRoot);

  const board = loadBoard(boardDir);
  const result = moveTask(board, tasksDir, taskId, column as Column, opts.force);

  if (!result.success) {
    log.error(result.error ?? 'Move failed');
    process.exit(1);
  }

  persistBoard(board, boardDir, tasksDir);

  log.success(`Moved ${taskId} → ${column}`);
}

export function handleBoardClaim(taskId: string, opts: { agent?: string }): void {
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
  if (!task) {
    log.error('Could not parse task file');
    process.exit(1);
  }

  task.assigned = opts.agent ?? 'agent';
  task.updated = new Date().toISOString();

  const oldColumn = task.column;
  task.column = 'in-progress';
  board.columns[oldColumn] = board.columns[oldColumn].filter((id) => id !== taskId);
  board.columns['in-progress'].push(taskId);

  fs.writeFileSync(taskFile, renderTaskFile(task));
  persistBoard(board, boardDir, tasksDir);

  log.success(`${taskId} claimed by ${task.assigned} → in-progress`);
}

export function handleBoardAssign(taskId: string, agent: string): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const tasksDir = getTasksDir(projectRoot);

  const taskFile = findTaskFile(tasksDir, taskId);
  if (!taskFile) {
    log.error(`Task '${taskId}' not found`);
    process.exit(1);
  }

  const task = parseTaskFile(taskFile);
  if (!task) {
    log.error('Could not parse task');
    process.exit(1);
  }

  task.assigned = agent;
  task.updated = new Date().toISOString();
  fs.writeFileSync(taskFile, renderTaskFile(task));

  log.success(`${taskId} assigned to ${agent}`);
}

export function handleBoardUpdate(
  taskId: string,
  opts: {
    status?: string;
    priority?: string;
    evidenceAdd?: string;
    tddStage?: string;
  },
): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const boardDir = getBoardDir(projectRoot);
  const tasksDir = getTasksDir(projectRoot);

  const taskFile = findTaskFile(tasksDir, taskId);
  if (!taskFile) {
    log.error(`Task '${taskId}' not found`);
    process.exit(1);
  }

  const task = parseTaskFile(taskFile);
  if (!task) {
    log.error('Could not parse task');
    process.exit(1);
  }

  if (opts.status) task.status = opts.status as import('../board/task.js').TaskStatus;
  if (opts.priority) task.priority = opts.priority as Priority;
  if (opts.evidenceAdd) task.evidence_produced.push(opts.evidenceAdd);
  if (opts.tddStage) task.tdd_stage = opts.tddStage as import('../board/task.js').TddStage;
  task.updated = new Date().toISOString();

  fs.writeFileSync(taskFile, renderTaskFile(task));

  const board = loadBoard(boardDir);
  persistBoard(board, boardDir, tasksDir);

  log.success(`Updated ${taskId}`);
}

export function handleBoardBlock(taskId: string, reason: string): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const boardDir = getBoardDir(projectRoot);
  const tasksDir = getTasksDir(projectRoot);

  const taskFile = findTaskFile(tasksDir, taskId);
  if (!taskFile) {
    log.error(`Task '${taskId}' not found`);
    process.exit(1);
  }

  const task = parseTaskFile(taskFile);
  if (!task) {
    log.error('Could not parse task');
    process.exit(1);
  }

  task.status = 'blocked';
  task.body += `\n\n## Blocked\n${new Date().toISOString()}: ${reason}\n`;
  task.updated = new Date().toISOString();
  fs.writeFileSync(taskFile, renderTaskFile(task));

  const board = loadBoard(boardDir);
  persistBoard(board, boardDir, tasksDir);

  log.warn(`${taskId} marked as blocked: ${reason}`);
}

export function handleBoardUnblock(taskId: string): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const boardDir = getBoardDir(projectRoot);
  const tasksDir = getTasksDir(projectRoot);

  const taskFile = findTaskFile(tasksDir, taskId);
  if (!taskFile) {
    log.error(`Task '${taskId}' not found`);
    process.exit(1);
  }

  const task = parseTaskFile(taskFile);
  if (!task) {
    log.error('Could not parse task');
    process.exit(1);
  }

  task.status = null;
  task.updated = new Date().toISOString();
  fs.writeFileSync(taskFile, renderTaskFile(task));

  const board = loadBoard(boardDir);
  persistBoard(board, boardDir, tasksDir);

  log.success(`${taskId} unblocked`);
}

export function handleBoardDeps(taskId: string): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const tasksDir = getTasksDir(projectRoot);

  const tasks = loadAllTasks(tasksDir);
  const taskMap = new Map(tasks.map((t) => [t.id, t]));

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
  const blocks = tasks.filter((t) => t.depends_on.includes(taskId));
  if (blocks.length > 0) {
    console.log('');
    log.dim('This task blocks:');
    for (const t of blocks) log.dim(`  ${t.id}: ${t.title}`);
  }
}

export function handleBoardStats(): void {
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
  console.log(
    `  Evidence:        ${stats.evidence_produced}/${stats.evidence_expected} links produced`,
  );

  const tasks = loadAllTasks(tasksDir);
  const byPriority: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
  for (const t of tasks) byPriority[t.priority] = (byPriority[t.priority] ?? 0) + 1;

  console.log('');
  log.dim('By priority:');
  for (const [p, count] of Object.entries(byPriority)) {
    if (count > 0) console.log(`  ${p.padEnd(10)} ${count}`);
  }
}

export function handleBoardArchive(): void {
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
  persistBoard(board, boardDir, tasksDir);

  log.success(`Archived ${archived} done task(s) to ${path.relative(projectRoot, archiveDir)}`);
}
