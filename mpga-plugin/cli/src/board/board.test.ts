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
  });

  it('saveBoard round-trips through loadBoard', () => {
    const board = createEmptyBoard();
    board.milestone = 'M001-x';
    saveBoard(boardDir, board);
    const again = loadBoard(boardDir);
    expect(again.milestone).toBe('M001-x');
    expect(fs.existsSync(path.join(boardDir, 'board.json'))).toBe(true);
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
    saveBoard(boardDir, board);
    addTask(board, tasksDir, { title: 'A', column: 'todo' });
    addTask(board, tasksDir, { title: 'B', column: 'done' });
    recalcStats(board, tasksDir);
    expect(board.stats.total).toBe(2);
    expect(board.stats.done).toBe(1);
    expect(board.stats.progress_pct).toBe(50);
  });
});
