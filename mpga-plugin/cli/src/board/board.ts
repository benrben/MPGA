import fs from 'fs';
import path from 'path';
import { Task, Column, loadAllTasks, taskFilename, renderTaskFile, parseTaskFile } from './task.js';

export interface BoardLane {
  id: string;
  task_ids: string[];
  status: 'queued' | 'running' | 'blocked' | 'done' | 'failed';
  scope?: string;
  files: string[];
  current_agent?: string | null;
  updated_at: string;
}

export interface BoardRun {
  id: string;
  lane_id: string;
  task_id: string;
  status: 'queued' | 'running' | 'handoff' | 'done' | 'failed';
  agent?: string | null;
  started_at: string;
  finished_at?: string | null;
}

export interface BoardState {
  version: string;
  milestone: string | null;
  updated: string;
  columns: Record<Column, string[]>;
  stats: {
    total: number;
    done: number;
    in_flight: number;
    blocked: number;
    progress_pct: number;
    evidence_produced: number;
    evidence_expected: number;
    avg_task_time?: string;
  };
  wip_limits: Record<string, number>;
  next_task_id: number;
  lanes: Record<string, BoardLane>;
  active_runs: Record<string, BoardRun>;
  scheduler: {
    lock_mode: 'file';
    max_parallel_lanes: number;
    split_strategy: 'file-groups';
  };
  ui: {
    refresh_interval_ms: number;
    theme: string;
  };
}

export function loadBoard(boardDir: string): BoardState {
  const boardPath = path.join(boardDir, 'board.json');
  if (!fs.existsSync(boardPath)) {
    return createEmptyBoard();
  }
  return normalizeBoardState(JSON.parse(fs.readFileSync(boardPath, 'utf-8')));
}

export function saveBoard(boardDir: string, state: BoardState): void {
  fs.mkdirSync(boardDir, { recursive: true });
  state.updated = new Date().toISOString();
  fs.writeFileSync(path.join(boardDir, 'board.json'), JSON.stringify(state, null, 2) + '\n');
}

export function createEmptyBoard(): BoardState {
  return normalizeBoardState({
    version: '1.0.0',
    milestone: null,
    updated: new Date().toISOString(),
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
  });
}

function normalizeBoardState(board: Partial<BoardState>): BoardState {
  return {
    version: board.version ?? '1.0.0',
    milestone: board.milestone ?? null,
    updated: board.updated ?? new Date().toISOString(),
    columns: {
      backlog: board.columns?.backlog ?? [],
      todo: board.columns?.todo ?? [],
      'in-progress': board.columns?.['in-progress'] ?? [],
      testing: board.columns?.testing ?? [],
      review: board.columns?.review ?? [],
      done: board.columns?.done ?? [],
    },
    stats: {
      total: board.stats?.total ?? 0,
      done: board.stats?.done ?? 0,
      in_flight: board.stats?.in_flight ?? 0,
      blocked: board.stats?.blocked ?? 0,
      progress_pct: board.stats?.progress_pct ?? 0,
      evidence_produced: board.stats?.evidence_produced ?? 0,
      evidence_expected: board.stats?.evidence_expected ?? 0,
      avg_task_time: board.stats?.avg_task_time,
    },
    wip_limits: {
      'in-progress': board.wip_limits?.['in-progress'] ?? 3,
      testing: board.wip_limits?.testing ?? 3,
      review: board.wip_limits?.review ?? 2,
    },
    next_task_id: board.next_task_id ?? 1,
    lanes: board.lanes ?? {},
    active_runs: board.active_runs ?? {},
    scheduler: {
      lock_mode: 'file',
      max_parallel_lanes: board.scheduler?.max_parallel_lanes ?? 3,
      split_strategy: 'file-groups',
    },
    ui: {
      refresh_interval_ms: board.ui?.refresh_interval_ms ?? 2500,
      theme: board.ui?.theme ?? 'mpga-signal',
    },
  };
}

export function recalcStats(
  board: BoardState,
  tasksDir: string,
  preloadedTasks?: Task[],
): BoardState {
  const tasks = preloadedTasks ?? loadAllTasks(tasksDir);
  const total = tasks.length;
  const done = tasks.filter((t) => t.column === 'done').length;
  const inFlight = tasks.filter((t) =>
    ['in-progress', 'testing', 'review'].includes(t.column),
  ).length;
  const blocked = tasks.filter((t) => t.status === 'blocked').length;
  const evidenceProduced = tasks.reduce((s, t) => s + t.evidence_produced.length, 0);
  const evidenceExpected = tasks.reduce((s, t) => s + t.evidence_expected.length, 0);

  board.stats = {
    total,
    done,
    in_flight: inFlight,
    blocked,
    progress_pct: total === 0 ? 0 : Math.round((done / total) * 100),
    evidence_produced: evidenceProduced,
    evidence_expected: evidenceExpected,
  };

  // Rebuild columns
  const columns: Record<Column, string[]> = {
    backlog: [],
    todo: [],
    'in-progress': [],
    testing: [],
    review: [],
    done: [],
  };
  for (const task of tasks) {
    if (columns[task.column]) columns[task.column].push(task.id);
  }
  board.columns = columns;

  return board;
}

export function checkWipLimit(board: BoardState, column: Column): boolean {
  const limit = board.wip_limits[column];
  if (!limit) return true;
  return board.columns[column].length < limit;
}

export function nextTaskId(board: BoardState, prefix = 'T'): string {
  const id = `${prefix}${String(board.next_task_id).padStart(3, '0')}`;
  board.next_task_id++;
  return id;
}

export function addTask(
  board: BoardState,
  tasksDir: string,
  options: {
    title: string;
    column?: Column;
    priority?: Task['priority'];
    scopes?: string[];
    depends?: string[];
    tags?: string[];
    milestone?: string;
  },
): Task {
  const id = nextTaskId(board);
  const now = new Date().toISOString();
  const task: Task = {
    id,
    title: options.title,
    column: options.column ?? 'backlog',
    status: null,
    priority: options.priority ?? 'medium',
    milestone: options.milestone,
    created: now,
    updated: now,
    depends_on: options.depends ?? [],
    blocks: [],
    scopes: options.scopes ?? [],
    tdd_stage: null,
    lane_id: null,
    run_status: 'queued',
    current_agent: null,
    file_locks: [],
    scope_locks: [],
    started_at: null,
    finished_at: null,
    heartbeat_at: null,
    evidence_expected: [],
    evidence_produced: [],
    tags: options.tags ?? [],
    time_estimate: '5min',
    body: '',
  };

  fs.mkdirSync(tasksDir, { recursive: true });
  const filename = taskFilename(id, options.title);
  fs.writeFileSync(path.join(tasksDir, filename), renderTaskFile(task));

  // Add to board columns
  board.columns[task.column].push(id);
  return task;
}

export function moveTask(
  board: BoardState,
  tasksDir: string,
  taskId: string,
  toColumn: Column,
  force = false,
): { success: boolean; error?: string } {
  // Check WIP limit
  if (!force && !checkWipLimit(board, toColumn)) {
    return {
      success: false,
      error: `WIP limit reached for '${toColumn}' (${board.columns[toColumn].length}/${board.wip_limits[toColumn]}). Use --force to override.`,
    };
  }

  const taskFile = findTaskFile(tasksDir, taskId);
  if (!taskFile) return { success: false, error: `Task '${taskId}' not found` };

  const task = parseTaskFile(taskFile);
  if (!task) return { success: false, error: `Could not parse task file` };

  // Remove from old column
  const oldColumn = task.column;
  board.columns[oldColumn] = board.columns[oldColumn].filter((id) => id !== taskId);

  // Add to new column
  task.column = toColumn;
  task.updated = new Date().toISOString();
  board.columns[toColumn].push(taskId);

  // Write updated task file
  fs.writeFileSync(taskFile, renderTaskFile(task));

  return { success: true };
}

export function findTaskFile(tasksDir: string, taskId: string): string | null {
  if (!fs.existsSync(tasksDir)) return null;
  const files = fs
    .readdirSync(tasksDir)
    .filter((f) => f.startsWith(taskId + '-') || f.startsWith(taskId + '.'));
  return files.length > 0 ? path.join(tasksDir, files[0]) : null;
}
