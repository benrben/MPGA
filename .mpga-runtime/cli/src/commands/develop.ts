import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import { findProjectRoot } from '../core/config.js';
import { loadBoard, findTaskFile } from '../board/board.js';
import { parseTaskFile, renderTaskFile } from '../board/task.js';
import { log } from '../core/logger.js';
import { persistBoard } from './board.js';
import { runDevelopTask } from './develop-scheduler.js';

// ── Handlers ──────────────────────────────────────────────

export function handleDevelopStatus(taskId: string): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const tasksDir = path.join(projectRoot, 'MPGA', 'board', 'tasks');

  const taskFile = findTaskFile(tasksDir, taskId);
  if (!taskFile) throw new Error(`Task '${taskId}' not found`);

  const task = parseTaskFile(taskFile);
  if (!task) throw new Error(`Could not parse task '${taskId}'`);

  log.header(`Develop Status: ${task.id}`);
  console.log(`  Title:         ${task.title}`);
  console.log(`  Column:        ${task.column}`);
  console.log(`  TDD Stage:     ${task.tdd_stage ?? '(none)'}`);
  console.log(`  Run Status:    ${task.run_status}`);
  console.log(`  Lane:          ${task.lane_id ?? '(none)'}`);
  console.log(`  Agent:         ${task.current_agent ?? '(none)'}`);

  if (task.file_locks.length > 0) {
    console.log('  File Locks:');
    for (const lock of task.file_locks) {
      console.log(`    - ${lock.path} (${lock.agent}, lane: ${lock.lane_id})`);
    }
  }

  if (task.scope_locks.length > 0) {
    console.log('  Scope Locks:');
    for (const lock of task.scope_locks) {
      console.log(`    - ${lock.scope} (${lock.agent}, lane: ${lock.lane_id})`);
    }
  }

  if (task.started_at) console.log(`  Started:       ${task.started_at}`);
  if (task.finished_at) console.log(`  Finished:      ${task.finished_at}`);
}

export function handleDevelopAbort(taskId: string): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const boardDir = path.join(projectRoot, 'MPGA', 'board');
  const tasksDir = path.join(boardDir, 'tasks');

  const taskFile = findTaskFile(tasksDir, taskId);
  if (!taskFile) throw new Error(`Task '${taskId}' not found`);

  const task = parseTaskFile(taskFile);
  if (!task) throw new Error(`Could not parse task '${taskId}'`);

  // Release all locks
  task.file_locks = [];
  task.scope_locks = [];
  task.current_agent = null;
  task.lane_id = null;
  task.run_status = 'queued';
  task.heartbeat_at = null;

  // Move task back to todo
  task.column = 'todo';
  task.updated = new Date().toISOString();

  fs.writeFileSync(taskFile, renderTaskFile(task));

  // Update board columns
  const board = loadBoard(boardDir);
  persistBoard(board, boardDir, tasksDir);

  log.success(`${taskId} aborted — locks released, moved to todo`);
}

export function handleDevelopResume(taskId: string): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const boardDir = path.join(projectRoot, 'MPGA', 'board');
  const tasksDir = path.join(boardDir, 'tasks');

  const taskFile = findTaskFile(tasksDir, taskId);
  if (!taskFile) throw new Error(`Task '${taskId}' not found`);

  const task = parseTaskFile(taskFile);
  if (!task) throw new Error(`Could not parse task '${taskId}'`);

  // Resume: move to in-progress, set running
  task.column = 'in-progress';
  task.run_status = 'running';
  task.updated = new Date().toISOString();

  fs.writeFileSync(taskFile, renderTaskFile(task));

  // Update board columns
  const board = loadBoard(boardDir);
  persistBoard(board, boardDir, tasksDir);

  log.success(`${taskId} resumed from TDD stage: ${task.tdd_stage ?? '(none)'}`);
}

// ── Registration ──────────────────────────────────────────

export function registerDevelop(program: Command): void {
  const cmd = program
    .command('develop <task-id>')
    .description('Execute a task through the develop scheduler')
    .option('--parallel <mode>', 'Parallel scheduling mode', 'auto')
    .option('--lanes <count>', 'Maximum number of parallel lanes', (value) => Number(value))
    .option('--dashboard', 'Refresh live board artifacts during scheduling')
    .action((taskId: string, opts) => {
      runDevelopTask(taskId, {
        parallel: opts.parallel,
        lanes: opts.lanes,
        dashboard: !!opts.dashboard,
      });
    });

  cmd
    .command('status <task-id>')
    .description('Show current TDD stage, lane status, and file locks')
    .action((taskId: string) => handleDevelopStatus(taskId));

  cmd
    .command('abort <task-id>')
    .description('Release all locks and move task back to todo')
    .action((taskId: string) => handleDevelopAbort(taskId));

  cmd
    .command('resume <task-id>')
    .description('Resume task from last TDD stage')
    .action((taskId: string) => handleDevelopResume(taskId));
}
