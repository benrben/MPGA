import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { Command } from 'commander';
import { createEmptyBoard, saveBoard, addTask, loadBoard } from '../board/board.js';
import { parseTaskFile, renderTaskFile } from '../board/task.js';

vi.mock('./develop-scheduler.js', () => ({
  runDevelopTask: vi.fn(),
}));

import { registerDevelop } from './develop.js';
import { runDevelopTask } from './develop-scheduler.js';

function createProgram(): Command {
  const program = new Command();
  program.exitOverride();
  return program;
}

describe('develop command', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('registers the develop run command and forwards scheduler options', async () => {
    const program = createProgram();
    registerDevelop(program);

    await program.parseAsync(['develop', 'T001', '--parallel', 'auto', '--lanes', '2', '--dashboard'], {
      from: 'user',
    });

    expect(runDevelopTask).toHaveBeenCalledWith('T001', {
      parallel: 'auto',
      lanes: 2,
      dashboard: true,
    });
  });
});

describe('develop status/abort/resume', () => {
  let tmpDir: string;
  let boardDir: string;
  let tasksDir: string;
  let logSpy: ReturnType<typeof vi.spyOn>;
  let errorSpy: ReturnType<typeof vi.spyOn>;

  function captured(): string {
    return logSpy.mock.calls.map((c) => c.join(' ')).join('\n');
  }

  function capturedErr(): string {
    return errorSpy.mock.calls.map((c) => c.join(' ')).join('\n');
  }

  beforeEach(async () => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-develop-cmds-'));
    boardDir = path.join(tmpDir, 'MPGA', 'board');
    tasksDir = path.join(boardDir, 'tasks');
    fs.mkdirSync(tasksDir, { recursive: true });

    const config = await import('../core/config.js');
    vi.spyOn(config, 'findProjectRoot').mockReturnValue(tmpDir);

    logSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    logSpy.mockRestore();
    errorSpy.mockRestore();
    fs.rmSync(tmpDir, { recursive: true, force: true });
    vi.restoreAllMocks();
  });

  function seedRunningTask(): string {
    const board = createEmptyBoard();
    saveBoard(boardDir, board);
    const task = addTask(board, tasksDir, {
      title: 'Running task',
      column: 'in-progress',
      priority: 'high',
      scopes: ['core'],
    });
    saveBoard(boardDir, board);

    // Simulate a running develop state
    const taskPath = path.join(tasksDir, fs.readdirSync(tasksDir).find((f) => f.startsWith(task.id))!);
    const parsed = parseTaskFile(taskPath)!;
    parsed.lane_id = 'T001-lane-1';
    parsed.run_status = 'running';
    parsed.current_agent = 'mpga-red-dev';
    parsed.tdd_stage = 'red';
    parsed.file_locks = [
      { path: 'src/board.ts', lane_id: 'T001-lane-1', agent: 'mpga-red-dev', acquired_at: '2026-03-24T12:00:00.000Z' },
    ];
    parsed.scope_locks = [
      { scope: 'core', lane_id: 'T001-lane-1', agent: 'mpga-red-dev', acquired_at: '2026-03-24T12:00:00.000Z' },
    ];
    parsed.started_at = '2026-03-24T12:00:00.000Z';
    fs.writeFileSync(taskPath, renderTaskFile(parsed));

    return task.id;
  }

  // ── develop status ──────────────────────────────────────

  describe('develop status', () => {
    it('shows current TDD stage and lane status for a running task', async () => {
      const taskId = seedRunningTask();
      const { handleDevelopStatus } = await import('./develop.js');

      handleDevelopStatus(taskId);

      const output = captured();
      expect(output).toContain(taskId);
      expect(output).toContain('red');
      expect(output).toContain('running');
      expect(output).toContain('mpga-red-dev');
    });

    it('shows file locks for a running task', async () => {
      const taskId = seedRunningTask();
      const { handleDevelopStatus } = await import('./develop.js');

      handleDevelopStatus(taskId);

      const output = captured();
      expect(output).toContain('src/board.ts');
    });

    it('errors when task does not exist', async () => {
      // Need a board to exist
      const board = createEmptyBoard();
      saveBoard(boardDir, board);

      const { handleDevelopStatus } = await import('./develop.js');

      expect(() => handleDevelopStatus('T999')).toThrow();
    });
  });

  // ── develop abort ───────────────────────────────────────

  describe('develop abort', () => {
    it('releases all locks and moves task back to todo', async () => {
      const taskId = seedRunningTask();
      const { handleDevelopAbort } = await import('./develop.js');

      handleDevelopAbort(taskId);

      // Verify the task was updated
      const taskPath = path.join(tasksDir, fs.readdirSync(tasksDir).find((f) => f.startsWith(taskId))!);
      const parsed = parseTaskFile(taskPath)!;
      expect(parsed.column).toBe('todo');
      expect(parsed.run_status).toBe('queued');
      expect(parsed.file_locks).toHaveLength(0);
      expect(parsed.scope_locks).toHaveLength(0);
      expect(parsed.current_agent).toBeNull();
      expect(parsed.lane_id).toBeNull();

      // Verify board columns updated
      const board = loadBoard(boardDir);
      expect(board.columns['todo']).toContain(taskId);
      expect(board.columns['in-progress']).not.toContain(taskId);
    });

    it('prints success message on abort', async () => {
      const taskId = seedRunningTask();
      const { handleDevelopAbort } = await import('./develop.js');

      handleDevelopAbort(taskId);

      const output = captured();
      expect(output).toContain(taskId);
      expect(output).toContain('abort');
    });

    it('errors when task does not exist', async () => {
      const board = createEmptyBoard();
      saveBoard(boardDir, board);

      const { handleDevelopAbort } = await import('./develop.js');
      expect(() => handleDevelopAbort('T999')).toThrow();
    });
  });

  // ── develop resume ──────────────────────────────────────

  describe('develop resume', () => {
    it('resumes from last TDD stage', async () => {
      const taskId = seedRunningTask();

      // First abort the task
      const { handleDevelopAbort, handleDevelopResume } = await import('./develop.js');
      handleDevelopAbort(taskId);

      // Now resume it
      handleDevelopResume(taskId);

      // Verify the task was moved back to in-progress and re-activated
      const taskPath = path.join(tasksDir, fs.readdirSync(tasksDir).find((f) => f.startsWith(taskId))!);
      const parsed = parseTaskFile(taskPath)!;
      expect(parsed.column).toBe('in-progress');
      expect(parsed.run_status).toBe('running');
      expect(parsed.tdd_stage).toBe('red'); // preserved from before abort
    });

    it('prints success message with TDD stage on resume', async () => {
      const taskId = seedRunningTask();
      const { handleDevelopAbort, handleDevelopResume } = await import('./develop.js');
      handleDevelopAbort(taskId);
      logSpy.mockClear();

      handleDevelopResume(taskId);

      const output = captured();
      expect(output).toContain(taskId);
      expect(output).toContain('resum');
    });

    it('errors when task does not exist', async () => {
      const board = createEmptyBoard();
      saveBoard(boardDir, board);

      const { handleDevelopResume } = await import('./develop.js');
      expect(() => handleDevelopResume('T999')).toThrow();
    });
  });
});
