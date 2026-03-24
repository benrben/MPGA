import fs from 'fs';
import path from 'path';
import type { BoardState, BoardLane, BoardRun } from './board.js';
import { loadAllTasks, type Task } from './task.js';

export interface BoardLiveEvent {
  type: string;
  lane_id?: string;
  task_id?: string;
  status?: string;
  [key: string]: unknown;
}

export interface BoardLiveTaskSummary {
  id: string;
  title: string;
  column: Task['column'];
  priority: Task['priority'];
  assigned?: string;
  lane_id: string | null;
  run_status: Task['run_status'];
  current_agent: string | null;
  file_locks: Task['file_locks'];
  scope_locks: Task['scope_locks'];
}

export interface BoardLiveSnapshot {
  generated_at: string;
  milestone: string | null;
  stats: BoardState['stats'];
  scheduler: BoardState['scheduler'];
  ui: BoardState['ui'];
  columns: Record<Task['column'], BoardLiveTaskSummary[]>;
  active_lanes: BoardLane[];
  active_runs: BoardRun[];
  recent_events: BoardLiveEvent[];
}

export function getBoardLiveDir(boardDir: string): string {
  return path.join(boardDir, 'live');
}

export function readRecentBoardEvents(boardDir: string, limit = 20): BoardLiveEvent[] {
  const eventsPath = path.join(getBoardLiveDir(boardDir), 'events.ndjson');
  if (!fs.existsSync(eventsPath)) return [];

  try {
    return fs
      .readFileSync(eventsPath, 'utf-8')
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .slice(-limit)
      .flatMap((line) => {
        try {
          return [JSON.parse(line) as BoardLiveEvent];
        } catch {
          return [];
        }
      });
  } catch {
    return [];
  }
}

function summarizeTask(task: Task): BoardLiveTaskSummary {
  return {
    id: task.id,
    title: task.title,
    column: task.column,
    priority: task.priority,
    assigned: task.assigned,
    lane_id: task.lane_id,
    run_status: task.run_status,
    current_agent: task.current_agent,
    file_locks: task.file_locks,
    scope_locks: task.scope_locks,
  };
}

export function buildBoardLiveSnapshot(
  board: BoardState,
  tasksDir: string,
  boardDir: string,
): BoardLiveSnapshot {
  const tasks = loadAllTasks(tasksDir);
  const columns: BoardLiveSnapshot['columns'] = {
    backlog: [],
    todo: [],
    'in-progress': [],
    testing: [],
    review: [],
    done: [],
  };

  for (const task of tasks) {
    columns[task.column].push(summarizeTask(task));
  }

  return {
    generated_at: new Date().toISOString(),
    milestone: board.milestone,
    stats: board.stats,
    scheduler: board.scheduler,
    ui: board.ui,
    columns,
    active_lanes: Object.values(board.lanes),
    active_runs: Object.values(board.active_runs),
    recent_events: readRecentBoardEvents(boardDir),
  };
}

export function writeBoardLiveSnapshot(
  board: BoardState,
  tasksDir: string,
  boardDir: string,
): string {
  const liveDir = getBoardLiveDir(boardDir);
  fs.mkdirSync(liveDir, { recursive: true });
  const snapshotPath = path.join(liveDir, 'snapshot.json');
  const snapshot = buildBoardLiveSnapshot(board, tasksDir, boardDir);
  fs.writeFileSync(snapshotPath, JSON.stringify(snapshot, null, 2) + '\n');
  return snapshotPath;
}
