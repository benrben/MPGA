import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { loadBoard, saveBoard, createEmptyBoard, recalcStats, addTask, moveTask } from './board.js';
import { parseTaskFile } from './task.js';

describe('board', () => {
  let tmpDir: string;
  let boardDir: string;
  let tasksDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-board-'));
    boardDir = path.join(tmpDir, 'MPGA', 'board');
    tasksDir = path.join(boardDir, 'tasks');
    fs.mkdirSync(tasksDir, { recursive: true });
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('loadBoard returns empty board when board.json missing', () => {
    const board = loadBoard(boardDir);
    expect(board.milestone).toBeNull();
    expect(board.columns.todo).toEqual([]);
    expect(board.lanes).toEqual({});
    expect(board.active_runs).toEqual({});
    expect(board.scheduler.lock_mode).toBe('file');
    expect(board.ui.refresh_interval_ms).toBe(2500);
  });

  it('saveBoard round-trips through loadBoard', () => {
    const board = createEmptyBoard();
    board.milestone = 'M001-x';
    board.scheduler.max_parallel_lanes = 4;
    board.ui.theme = 'signal';
    saveBoard(boardDir, board);
    const again = loadBoard(boardDir);
    expect(again.milestone).toBe('M001-x');
    expect(again.scheduler.max_parallel_lanes).toBe(4);
    expect(again.ui.theme).toBe('signal');
    expect(fs.existsSync(path.join(boardDir, 'board.json'))).toBe(true);
  });

  it('loadBoard backfills missing runtime metadata for legacy board files', () => {
    fs.mkdirSync(boardDir, { recursive: true });
    fs.writeFileSync(
      path.join(boardDir, 'board.json'),
      JSON.stringify({
        version: '1.0.0',
        milestone: 'M001-legacy',
        updated: '2026-03-24T00:00:00.000Z',
        columns: { backlog: [], todo: [], 'in-progress': [], testing: [], review: [], done: [] },
        stats: {
          total: 0,
          done: 0,
          in_flight: 0,
          blocked: 0,
          progress_pct: 0,
          evidence_produced: 0,
          evidence_expected: 0,
        },
        wip_limits: { 'in-progress': 3, testing: 3, review: 2 },
        next_task_id: 1,
      }),
    );

    const board = loadBoard(boardDir);
    expect(board.lanes).toEqual({});
    expect(board.active_runs).toEqual({});
    expect(board.scheduler.lock_mode).toBe('file');
    expect(board.ui.refresh_interval_ms).toBe(2500);
  });

  it('addTask writes task file and appends id to column', () => {
    const board = createEmptyBoard();
    saveBoard(boardDir, board);
    const task = addTask(board, tasksDir, { title: 'Hello world', column: 'todo' });
    expect(task.id).toMatch(/^T\d+/);
    expect(board.columns.todo).toContain(task.id);
    const fp = path.join(tasksDir, fs.readdirSync(tasksDir)[0]);
    expect(parseTaskFile(fp)?.title).toBe('Hello world');
  });

  it('moveTask updates column in board and task file', () => {
    const board = createEmptyBoard();
    saveBoard(boardDir, board);
    const task = addTask(board, tasksDir, { title: 'Move me', column: 'todo' });
    const res = moveTask(board, tasksDir, task.id, 'in-progress', true);
    expect(res.success).toBe(true);
    expect(board.columns.todo).not.toContain(task.id);
    expect(board.columns['in-progress']).toContain(task.id);
    const taskFile = path.join(tasksDir, fs.readdirSync(tasksDir)[0]);
    expect(parseTaskFile(taskFile)?.column).toBe('in-progress');
  });

  it('recalcStats aggregates tasks from disk', () => {
    const board = createEmptyBoard();
    board.lanes['lane-1'] = {
      id: 'lane-1',
      task_ids: [],
      status: 'queued',
      files: ['src/board/task.ts'],
      updated_at: '2026-03-24T00:00:00.000Z',
    };
    saveBoard(boardDir, board);
    addTask(board, tasksDir, { title: 'A', column: 'todo' });
    addTask(board, tasksDir, { title: 'B', column: 'done' });
    recalcStats(board, tasksDir);
    expect(board.stats.total).toBe(2);
    expect(board.stats.done).toBe(1);
    expect(board.stats.progress_pct).toBe(50);
    expect(board.lanes['lane-1']?.files).toEqual(['src/board/task.ts']);
  });
});
