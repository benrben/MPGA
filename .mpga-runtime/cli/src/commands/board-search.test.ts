import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { createEmptyBoard, saveBoard, addTask } from '../board/board.js';
import { parseTaskFile, renderTaskFile } from '../board/task.js';
import { handleBoardSearch } from './board-search.js';

describe('board search', () => {
  let tmpDir: string;
  let boardDir: string;
  let tasksDir: string;
  let logSpy: ReturnType<typeof vi.spyOn>;

  function captured(): string {
    return logSpy.mock.calls.map((c) => c.join(' ')).join('\n');
  }

  beforeEach(async () => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-board-search-'));
    boardDir = path.join(tmpDir, 'MPGA', 'board');
    tasksDir = path.join(boardDir, 'tasks');
    fs.mkdirSync(tasksDir, { recursive: true });

    const board = createEmptyBoard();
    saveBoard(boardDir, board);

    // Seed tasks with varied attributes
    const t1 = addTask(board, tasksDir, {
      title: 'Fix critical login bug',
      column: 'todo',
      priority: 'critical',
      scopes: ['auth'],
      tags: ['bugfix', 'urgent'],
    });
    const t2 = addTask(board, tasksDir, {
      title: 'Add unit tests for parser',
      column: 'in-progress',
      priority: 'high',
      scopes: ['core'],
      tags: ['testing'],
    });
    const t3 = addTask(board, tasksDir, {
      title: 'Refactor board layout',
      column: 'backlog',
      priority: 'medium',
      scopes: ['board'],
      tags: ['refactor'],
    });
    const t4 = addTask(board, tasksDir, {
      title: 'Update documentation',
      column: 'done',
      priority: 'low',
      scopes: ['docs'],
      tags: ['docs'],
    });
    saveBoard(boardDir, board);

    // Assign agents to some tasks
    const t2File = path.join(tasksDir, fs.readdirSync(tasksDir).find((f) => f.startsWith(t2.id))!);
    const t2Task = parseTaskFile(t2File)!;
    t2Task.assigned = 'green-dev';
    fs.writeFileSync(t2File, renderTaskFile(t2Task));

    const t1File = path.join(tasksDir, fs.readdirSync(tasksDir).find((f) => f.startsWith(t1.id))!);
    const t1Task = parseTaskFile(t1File)!;
    t1Task.assigned = 'red-dev';
    fs.writeFileSync(t1File, renderTaskFile(t1Task));

    // Mock findProjectRoot
    const config = await import('../core/config.js');
    vi.spyOn(config, 'findProjectRoot').mockReturnValue(tmpDir);

    logSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    logSpy.mockRestore();
    fs.rmSync(tmpDir, { recursive: true, force: true });
    vi.restoreAllMocks();
  });

  it('returns all tasks when no filters are provided', () => {
    const results = handleBoardSearch('', {});
    expect(results).toHaveLength(4);
  });

  it('filters tasks by priority', () => {
    const results = handleBoardSearch('', { priority: 'critical' });
    expect(results).toHaveLength(1);
    expect(results[0]!.id).toBe('T001');
  });

  it('filters tasks by column', () => {
    const results = handleBoardSearch('', { column: 'in-progress' });
    expect(results).toHaveLength(1);
    expect(results[0]!.title).toContain('parser');
  });

  it('filters tasks by scope', () => {
    const results = handleBoardSearch('', { scope: 'auth' });
    expect(results).toHaveLength(1);
    expect(results[0]!.title).toContain('login');
  });

  it('filters tasks by assigned agent', () => {
    const results = handleBoardSearch('', { agent: 'green-dev' });
    expect(results).toHaveLength(1);
    expect(results[0]!.title).toContain('parser');
  });

  it('filters tasks by tags', () => {
    const results = handleBoardSearch('', { tags: 'bugfix' });
    expect(results).toHaveLength(1);
    expect(results[0]!.title).toContain('login');
  });

  it('searches task titles with text query', () => {
    const results = handleBoardSearch('board', {});
    expect(results).toHaveLength(1);
    expect(results[0]!.title).toContain('board');
  });

  it('case-insensitive text search', () => {
    const results = handleBoardSearch('LOGIN', {});
    expect(results).toHaveLength(1);
    expect(results[0]!.title).toContain('login');
  });

  it('combines text query with filter options', () => {
    // Search for 'test' with priority high
    const results = handleBoardSearch('test', { priority: 'high' });
    expect(results).toHaveLength(1);
    expect(results[0]!.title).toContain('parser');
  });

  it('returns empty array when no tasks match', () => {
    const results = handleBoardSearch('nonexistent', { priority: 'critical' });
    expect(results).toHaveLength(0);
  });

  it('supports multiple tag matching (comma-separated)', () => {
    const results = handleBoardSearch('', { tags: 'bugfix,urgent' });
    expect(results).toHaveLength(1);
    expect(results[0]!.tags).toContain('bugfix');
    expect(results[0]!.tags).toContain('urgent');
  });

  it('prints matching tasks to console', () => {
    handleBoardSearch('login', {});
    const output = captured();
    expect(output).toContain('T001');
    expect(output).toContain('login');
  });

  it('prints a message when no results found', () => {
    handleBoardSearch('zzz-no-match-zzz', {});
    const output = captured();
    expect(output).toContain('No tasks match');
  });
});
