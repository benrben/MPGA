import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { renderBoardMd } from './board-md.js';
import { createEmptyBoard, saveBoard, addTask, recalcStats } from './board.js';

describe('renderBoardMd', () => {
  let tmpDir: string;
  let boardDir: string;
  let tasksDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-boardmd-'));
    boardDir = path.join(tmpDir, 'MPGA', 'board');
    tasksDir = path.join(boardDir, 'tasks');
    fs.mkdirSync(tasksDir, { recursive: true });
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('includes milestone title and progress line', () => {
    const board = createEmptyBoard();
    board.milestone = 'M001-demo';
    saveBoard(boardDir, board);
    addTask(board, tasksDir, { title: 'Task one', column: 'todo' });
    recalcStats(board, tasksDir);
    const md = renderBoardMd(board, tasksDir);
    expect(md).toContain('# Board: M001-demo');
    expect(md).toContain('**Progress:');
    expect(md).toContain('Todo');
    expect(md).toContain('Task one');
  });

  it('shows health line for blocked tasks', () => {
    const board = createEmptyBoard();
    saveBoard(boardDir, board);
    board.stats.blocked = 2;
    board.stats.total = 3;
    board.stats.done = 0;
    board.stats.in_flight = 0;
    board.stats.progress_pct = 0;
    board.stats.evidence_produced = 0;
    board.stats.evidence_expected = 0;
    const md = renderBoardMd(board, tasksDir);
    expect(md).toContain('blocked');
  });
});
