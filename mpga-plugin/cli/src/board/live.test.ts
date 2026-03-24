import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { addTask, createEmptyBoard, recalcStats } from './board.js';
import { parseTaskFile, renderTaskFile } from './task.js';
import { buildBoardLiveSnapshot, readRecentBoardEvents, writeBoardLiveSnapshot } from './live.js';

describe('live board snapshot', () => {
  let tmpDir: string;
  let boardDir: string;
  let tasksDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-live-'));
    boardDir = path.join(tmpDir, 'MPGA', 'board');
    tasksDir = path.join(boardDir, 'tasks');
    fs.mkdirSync(tasksDir, { recursive: true });
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('builds a snapshot with lanes, locks, and recent events', () => {
    const board = createEmptyBoard();
    board.milestone = 'M001-live';
    board.lanes['lane-auth-1'] = {
      id: 'lane-auth-1',
      task_ids: ['T001'],
      status: 'running',
      scope: 'src-board',
      files: ['src/board/task.ts'],
      current_agent: 'mpga-green-dev',
      updated_at: '2026-03-24T12:00:00.000Z',
    };
    board.active_runs['run-1'] = {
      id: 'run-1',
      lane_id: 'lane-auth-1',
      task_id: 'T001',
      status: 'running',
      agent: 'mpga-green-dev',
      started_at: '2026-03-24T12:00:00.000Z',
    };

    const task = addTask(board, tasksDir, { title: 'Track locks', column: 'in-progress' });
    const taskPath = path.join(tasksDir, fs.readdirSync(tasksDir)[0]!);
    const parsed = parseTaskFile(taskPath)!;
    parsed.lane_id = 'lane-auth-1';
    parsed.run_status = 'running';
    parsed.current_agent = 'mpga-green-dev';
    parsed.file_locks = [
      {
        path: 'src/board/task.ts',
        lane_id: 'lane-auth-1',
        agent: 'mpga-green-dev',
        acquired_at: '2026-03-24T12:00:00.000Z',
      },
    ];
    fs.writeFileSync(taskPath, renderTaskFile(parsed));

    fs.mkdirSync(path.join(boardDir, 'live'), { recursive: true });
    fs.writeFileSync(
      path.join(boardDir, 'live', 'events.ndjson'),
      `${JSON.stringify({
        type: 'lane-transition',
        lane_id: 'lane-auth-1',
        task_id: task.id,
        status: 'running',
      })}\n`,
    );

    recalcStats(board, tasksDir);
    const snapshot = buildBoardLiveSnapshot(board, tasksDir, boardDir);

    expect(snapshot.milestone).toBe('M001-live');
    expect(snapshot.columns['in-progress']).toHaveLength(1);
    expect(snapshot.columns['in-progress'][0]?.lane_id).toBe('lane-auth-1');
    expect(snapshot.active_lanes).toHaveLength(1);
    expect(snapshot.active_lanes[0]?.current_agent).toBe('mpga-green-dev');
    expect(snapshot.recent_events).toHaveLength(1);
  });

  it('ignores missing or malformed event files', () => {
    expect(readRecentBoardEvents(boardDir)).toEqual([]);

    fs.mkdirSync(path.join(boardDir, 'live'), { recursive: true });
    fs.writeFileSync(path.join(boardDir, 'live', 'events.ndjson'), '{"bad-json"\n');
    expect(readRecentBoardEvents(boardDir)).toEqual([]);
  });

  it('writes snapshot.json into the live board directory', () => {
    const board = createEmptyBoard();
    addTask(board, tasksDir, { title: 'Persist me', column: 'todo' });
    recalcStats(board, tasksDir);

    const filepath = writeBoardLiveSnapshot(board, tasksDir, boardDir);
    expect(filepath).toBe(path.join(boardDir, 'live', 'snapshot.json'));
    expect(fs.existsSync(filepath)).toBe(true);
    const raw = JSON.parse(fs.readFileSync(filepath, 'utf-8'));
    expect(raw.columns.todo[0].title).toBe('Persist me');
  });
});
