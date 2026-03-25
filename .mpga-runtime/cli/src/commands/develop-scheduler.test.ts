import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { addTask, createEmptyBoard, loadBoard, saveBoard } from '../board/board.js';
import { parseTaskFile, renderTaskFile } from '../board/task.js';
import {
  canAcquireFileLocks,
  persistLaneTransition,
  splitIntoFileGroups,
  runDevelopTask,
  saveTddCheckpoint,
  loadTddCheckpoint,
  type TddCheckpoint,
} from './develop-scheduler.js';

describe('develop scheduler', () => {
  let tmpDir: string;
  let boardDir: string;
  let tasksDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-develop-scheduler-'));
    boardDir = path.join(tmpDir, 'MPGA', 'board');
    tasksDir = path.join(boardDir, 'tasks');
    fs.mkdirSync(tasksDir, { recursive: true });
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('splits disjoint file groups into separate lanes', () => {
    const lanes = splitIntoFileGroups(
      'T001',
      [['src/a.ts'], ['src/b.ts', 'src/c.ts']],
      'src-board',
    );
    expect(lanes).toHaveLength(2);
    expect(lanes[0]?.files).toEqual(['src/a.ts']);
    expect(lanes[1]?.files).toEqual(['src/b.ts', 'src/c.ts']);
  });

  it('merges overlapping file groups into one lane', () => {
    const lanes = splitIntoFileGroups(
      'T001',
      [
        ['src/a.ts', 'src/b.ts'],
        ['src/b.ts', 'src/c.ts'],
      ],
      'src-board',
    );
    expect(lanes).toHaveLength(1);
    expect(lanes[0]?.files).toEqual(['src/a.ts', 'src/b.ts', 'src/c.ts']);
  });

  it('creates a default lane when no file groups are known yet', () => {
    const lanes = splitIntoFileGroups('T001', [[]], 'src-board');
    expect(lanes).toHaveLength(1);
    expect(lanes[0]?.files).toEqual([]);
  });

  it('rejects same-file lock conflicts against active tasks', () => {
    const board = createEmptyBoard();
    saveBoard(boardDir, board);
    addTask(board, tasksDir, { title: 'Lock holder', column: 'in-progress' });

    const taskPath = path.join(tasksDir, fs.readdirSync(tasksDir)[0]!);
    const parsed = parseTaskFile(taskPath)!;
    parsed.lane_id = 'lane-1';
    parsed.run_status = 'running';
    parsed.current_agent = 'mpga-green-dev';
    parsed.file_locks = [
      {
        path: 'src/shared.ts',
        lane_id: 'lane-1',
        agent: 'mpga-green-dev',
        acquired_at: '2026-03-24T12:00:00.000Z',
      },
    ];
    fs.writeFileSync(taskPath, renderTaskFile(parsed));

    const result = canAcquireFileLocks(['src/shared.ts'], tasksDir);
    expect(result.ok).toBe(false);
    expect(result.conflicts).toEqual(['src/shared.ts']);
  });

  it('runDevelopTask consolidates all files into one lane when parallel is none', async () => {
    const board = createEmptyBoard();
    saveBoard(boardDir, board);

    const task = addTask(board, tasksDir, {
      title: 'Multi-file task',
      column: 'in-progress',
      scopes: ['src-board'],
    });
    saveBoard(boardDir, board);
    const taskPath = path.join(
      tasksDir,
      fs.readdirSync(tasksDir).find((f) => f.startsWith(task.id))!,
    );
    const parsed = parseTaskFile(taskPath)!;
    parsed.file_locks = [
      {
        path: 'src/a.ts',
        lane_id: 'l1',
        agent: 'red-dev',
        acquired_at: '2026-03-24T12:00:00.000Z',
      },
      {
        path: 'src/b.ts',
        lane_id: 'l2',
        agent: 'red-dev',
        acquired_at: '2026-03-24T12:00:00.000Z',
      },
      {
        path: 'src/c.ts',
        lane_id: 'l3',
        agent: 'red-dev',
        acquired_at: '2026-03-24T12:00:00.000Z',
      },
    ];
    fs.writeFileSync(taskPath, renderTaskFile(parsed));

    const config = await import('../core/config.js');
    const spy = vi.spyOn(config, 'findProjectRoot').mockReturnValue(tmpDir);

    const laneIds = runDevelopTask(task.id, { parallel: 'none' });
    expect(laneIds).toHaveLength(1);

    const updatedBoard = loadBoard(boardDir);
    const lane = updatedBoard.lanes[laneIds[0]!];
    expect(lane?.files.sort()).toEqual(['src/a.ts', 'src/b.ts', 'src/c.ts']);

    spy.mockRestore();
  });

  it('runDevelopTask keeps separate lanes when parallel is auto', async () => {
    const board = createEmptyBoard();
    saveBoard(boardDir, board);

    const task = addTask(board, tasksDir, {
      title: 'Multi-file task',
      column: 'in-progress',
      scopes: ['src-board'],
    });
    saveBoard(boardDir, board);
    const taskPath = path.join(
      tasksDir,
      fs.readdirSync(tasksDir).find((f) => f.startsWith(task.id))!,
    );
    const parsed = parseTaskFile(taskPath)!;
    parsed.file_locks = [
      {
        path: 'src/a.ts',
        lane_id: 'l1',
        agent: 'red-dev',
        acquired_at: '2026-03-24T12:00:00.000Z',
      },
      {
        path: 'src/b.ts',
        lane_id: 'l2',
        agent: 'red-dev',
        acquired_at: '2026-03-24T12:00:00.000Z',
      },
    ];
    fs.writeFileSync(taskPath, renderTaskFile(parsed));

    const config = await import('../core/config.js');
    const spy = vi.spyOn(config, 'findProjectRoot').mockReturnValue(tmpDir);

    const laneIds = runDevelopTask(task.id, { parallel: 'auto' });
    expect(laneIds).toHaveLength(2);

    spy.mockRestore();
  });

  it('runDevelopTask skips lanes with conflicting file locks', async () => {
    const board = createEmptyBoard();
    saveBoard(boardDir, board);

    // Create a running task that holds a file lock on src/shared.ts
    const holder = addTask(board, tasksDir, { title: 'Lock holder', column: 'in-progress' });
    saveBoard(boardDir, board);
    const holderPath = path.join(
      tasksDir,
      fs.readdirSync(tasksDir).find((f) => f.startsWith(holder.id))!,
    );
    const holderTask = parseTaskFile(holderPath)!;
    holderTask.run_status = 'running';
    holderTask.lane_id = 'holder-lane';
    holderTask.file_locks = [
      {
        path: 'src/shared.ts',
        lane_id: 'holder-lane',
        agent: 'mpga-green-dev',
        acquired_at: '2026-03-24T12:00:00.000Z',
      },
    ];
    fs.writeFileSync(holderPath, renderTaskFile(holderTask));

    // Create a second task whose file_locks overlap with the holder
    const contender = addTask(board, tasksDir, {
      title: 'Contender',
      column: 'in-progress',
      scopes: ['src-board'],
    });
    saveBoard(boardDir, board);
    const contenderPath = path.join(
      tasksDir,
      fs.readdirSync(tasksDir).find((f) => f.startsWith(contender.id))!,
    );
    const contenderTask = parseTaskFile(contenderPath)!;
    contenderTask.file_locks = [
      {
        path: 'src/shared.ts',
        lane_id: 'c-lane',
        agent: 'mpga-red-dev',
        acquired_at: '2026-03-24T12:00:00.000Z',
      },
    ];
    fs.writeFileSync(contenderPath, renderTaskFile(contenderTask));

    // Mock findProjectRoot to point to our temp dir
    const config = await import('../core/config.js');
    const spy = vi.spyOn(config, 'findProjectRoot').mockReturnValue(tmpDir);

    const scheduledIds = runDevelopTask(contender.id, {});

    // The lane with src/shared.ts should NOT have been scheduled as 'running'
    const updatedBoard = loadBoard(boardDir);
    for (const laneId of scheduledIds) {
      const lane = updatedBoard.lanes[laneId];
      // If there are file lock conflicts, the lane should not be running
      if (lane && lane.files.includes('src/shared.ts')) {
        expect(lane.status).not.toBe('running');
      }
    }
    // If all files conflicted, no lanes should be scheduled
    expect(scheduledIds).toHaveLength(0);

    spy.mockRestore();
  });

  describe('TDD checkpoint', () => {
    it('saveTddCheckpoint writes a ## TDD Checkpoint section to the task body', () => {
      const board = createEmptyBoard();
      saveBoard(boardDir, board);
      const task = addTask(board, tasksDir, { title: 'Checkpoint task', column: 'in-progress' });
      saveBoard(boardDir, board);

      const checkpoint: TddCheckpoint = {
        stage: 'red',
        lastTestFile: 'src/foo.test.ts',
        lastImplFile: 'src/foo.ts',
        failingTest: 'should handle edge case',
        savedAt: '2026-03-24T14:00:00.000Z',
      };
      saveTddCheckpoint(tasksDir, task.id, checkpoint);

      const taskPath = path.join(
        tasksDir,
        fs.readdirSync(tasksDir).find((f) => f.startsWith(task.id))!,
      );
      const raw = fs.readFileSync(taskPath, 'utf-8');
      expect(raw).toContain('## TDD Checkpoint');
      expect(raw).toContain('stage: red');
      expect(raw).toContain('lastTestFile: src/foo.test.ts');
      expect(raw).toContain('lastImplFile: src/foo.ts');
      expect(raw).toContain('failingTest: should handle edge case');
      expect(raw).toContain('savedAt: 2026-03-24T14:00:00.000Z');
    });

    it('loadTddCheckpoint returns the saved checkpoint', () => {
      const board = createEmptyBoard();
      saveBoard(boardDir, board);
      const task = addTask(board, tasksDir, { title: 'Load checkpoint', column: 'in-progress' });
      saveBoard(boardDir, board);

      const checkpoint: TddCheckpoint = {
        stage: 'green',
        lastTestFile: 'src/bar.test.ts',
        lastImplFile: 'src/bar.ts',
        failingTest: 'should pass now',
        savedAt: '2026-03-24T15:00:00.000Z',
      };
      saveTddCheckpoint(tasksDir, task.id, checkpoint);

      const loaded = loadTddCheckpoint(tasksDir, task.id);
      expect(loaded).not.toBeNull();
      expect(loaded!.stage).toBe('green');
      expect(loaded!.lastTestFile).toBe('src/bar.test.ts');
      expect(loaded!.lastImplFile).toBe('src/bar.ts');
      expect(loaded!.failingTest).toBe('should pass now');
      expect(loaded!.savedAt).toBe('2026-03-24T15:00:00.000Z');
    });

    it('loadTddCheckpoint returns null when no checkpoint exists', () => {
      const board = createEmptyBoard();
      saveBoard(boardDir, board);
      const task = addTask(board, tasksDir, { title: 'No checkpoint', column: 'in-progress' });
      saveBoard(boardDir, board);

      const loaded = loadTddCheckpoint(tasksDir, task.id);
      expect(loaded).toBeNull();
    });

    it('saveTddCheckpoint replaces an existing checkpoint section', () => {
      const board = createEmptyBoard();
      saveBoard(boardDir, board);
      const task = addTask(board, tasksDir, { title: 'Replace checkpoint', column: 'in-progress' });
      saveBoard(boardDir, board);

      saveTddCheckpoint(tasksDir, task.id, {
        stage: 'red',
        lastTestFile: 'src/old.test.ts',
        savedAt: '2026-03-24T14:00:00.000Z',
      });
      saveTddCheckpoint(tasksDir, task.id, {
        stage: 'blue',
        lastTestFile: 'src/new.test.ts',
        lastImplFile: 'src/new.ts',
        savedAt: '2026-03-24T16:00:00.000Z',
      });

      const loaded = loadTddCheckpoint(tasksDir, task.id);
      expect(loaded!.stage).toBe('blue');
      expect(loaded!.lastTestFile).toBe('src/new.test.ts');
      expect(loaded!.lastImplFile).toBe('src/new.ts');

      // Ensure old checkpoint content is gone
      const taskPath = path.join(
        tasksDir,
        fs.readdirSync(tasksDir).find((f) => f.startsWith(task.id))!,
      );
      const raw = fs.readFileSync(taskPath, 'utf-8');
      const checkpointCount = (raw.match(/## TDD Checkpoint/g) || []).length;
      expect(checkpointCount).toBe(1);
    });

    it('loadTddCheckpoint returns null for non-existent task', () => {
      const loaded = loadTddCheckpoint(tasksDir, 'T999');
      expect(loaded).toBeNull();
    });

    it('checkpoint fields are optional except stage and savedAt', () => {
      const board = createEmptyBoard();
      saveBoard(boardDir, board);
      const task = addTask(board, tasksDir, { title: 'Minimal checkpoint', column: 'in-progress' });
      saveBoard(boardDir, board);

      saveTddCheckpoint(tasksDir, task.id, {
        stage: 'review',
        savedAt: '2026-03-24T17:00:00.000Z',
      });

      const loaded = loadTddCheckpoint(tasksDir, task.id);
      expect(loaded!.stage).toBe('review');
      expect(loaded!.lastTestFile).toBeUndefined();
      expect(loaded!.lastImplFile).toBeUndefined();
      expect(loaded!.failingTest).toBeUndefined();
      expect(loaded!.savedAt).toBe('2026-03-24T17:00:00.000Z');
    });

    it('runDevelopTask resumes from checkpoint when one exists', async () => {
      const board = createEmptyBoard();
      saveBoard(boardDir, board);
      const task = addTask(board, tasksDir, {
        title: 'Resume task',
        column: 'in-progress',
        scopes: ['src-board'],
      });
      saveBoard(boardDir, board);

      // Save a checkpoint so runDevelopTask can detect it
      saveTddCheckpoint(tasksDir, task.id, {
        stage: 'green',
        lastTestFile: 'src/resume.test.ts',
        lastImplFile: 'src/resume.ts',
        failingTest: 'should resume',
        savedAt: '2026-03-24T18:00:00.000Z',
      });

      const config = await import('../core/config.js');
      const spy = vi.spyOn(config, 'findProjectRoot').mockReturnValue(tmpDir);

      const laneIds = runDevelopTask(task.id, {});
      expect(laneIds.length).toBeGreaterThanOrEqual(1);

      // After scheduling, verify the task's tdd_stage is set to the checkpoint stage
      const taskPath = path.join(
        tasksDir,
        fs.readdirSync(tasksDir).find((f) => f.startsWith(task.id))!,
      );
      const parsed = parseTaskFile(taskPath)!;
      expect(parsed.tdd_stage).toBe('green');

      spy.mockRestore();
    });
  });

  it('persists lane transitions into task, board, and live snapshot state', () => {
    const board = createEmptyBoard();
    saveBoard(boardDir, board);
    const task = addTask(board, tasksDir, { title: 'Persist transition', column: 'todo' });
    saveBoard(boardDir, board);

    persistLaneTransition(boardDir, tasksDir, {
      taskId: task.id,
      laneId: 'lane-1',
      status: 'running',
      agent: 'mpga-green-dev',
      files: ['src/board/task.ts'],
      scope: 'src-board',
    });

    const taskPath = path.join(tasksDir, fs.readdirSync(tasksDir)[0]!);
    const parsed = parseTaskFile(taskPath)!;
    const nextBoard = loadBoard(boardDir);
    expect(parsed.lane_id).toBe('lane-1');
    expect(parsed.run_status).toBe('running');
    expect(parsed.file_locks[0]?.path).toBe('src/board/task.ts');
    expect(nextBoard.lanes['lane-1']?.current_agent).toBe('mpga-green-dev');
    expect(nextBoard.active_runs['lane-1:T001']?.status).toBe('running');
    expect(fs.existsSync(path.join(boardDir, 'live', 'snapshot.json'))).toBe(true);
  });
});
