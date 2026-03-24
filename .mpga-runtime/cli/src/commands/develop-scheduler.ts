import fs from 'fs';
import path from 'path';
import { findProjectRoot } from '../core/config.js';
import { loadBoard, saveBoard, type BoardLane } from '../board/board.js';
import { parseTaskFile, renderTaskFile, loadAllTasks, type RunStatus, type FileLock, type TddStage } from '../board/task.js';
import { findTaskFile, recalcStats } from '../board/board.js';
import { writeBoardLiveSnapshot } from '../board/live.js';
import { writeBoardLiveHtml } from '../board/live-html.js';

export interface PersistLaneTransitionOptions {
  taskId: string;
  laneId: string;
  status: RunStatus;
  agent?: string;
  files?: string[];
  scope?: string;
}

export interface TddCheckpoint {
  stage: 'red' | 'green' | 'blue' | 'review';
  lastTestFile?: string;
  lastImplFile?: string;
  failingTest?: string;
  savedAt: string;
}

function renderCheckpointSection(checkpoint: TddCheckpoint): string {
  const lines = ['## TDD Checkpoint'];
  lines.push(`- stage: ${checkpoint.stage}`);
  if (checkpoint.lastTestFile) lines.push(`- lastTestFile: ${checkpoint.lastTestFile}`);
  if (checkpoint.lastImplFile) lines.push(`- lastImplFile: ${checkpoint.lastImplFile}`);
  if (checkpoint.failingTest) lines.push(`- failingTest: ${checkpoint.failingTest}`);
  lines.push(`- savedAt: ${checkpoint.savedAt}`);
  return lines.join('\n');
}

function parseCheckpointSection(body: string): TddCheckpoint | null {
  const sectionStart = body.indexOf('## TDD Checkpoint');
  if (sectionStart === -1) return null;

  const afterHeader = body.slice(sectionStart);
  // Find the next ## heading (if any) to bound the section
  const nextSection = afterHeader.indexOf('\n## ', 1);
  const sectionText = nextSection === -1 ? afterHeader : afterHeader.slice(0, nextSection);

  const getValue = (key: string): string | undefined => {
    const match = sectionText.match(new RegExp(`^- ${key}: (.+)$`, 'm'));
    return match ? match[1] : undefined;
  };

  const stage = getValue('stage');
  const savedAt = getValue('savedAt');
  if (!stage || !savedAt) return null;

  const checkpoint: TddCheckpoint = {
    stage: stage as TddCheckpoint['stage'],
    savedAt,
  };
  const lastTestFile = getValue('lastTestFile');
  const lastImplFile = getValue('lastImplFile');
  const failingTest = getValue('failingTest');
  if (lastTestFile) checkpoint.lastTestFile = lastTestFile;
  if (lastImplFile) checkpoint.lastImplFile = lastImplFile;
  if (failingTest) checkpoint.failingTest = failingTest;

  return checkpoint;
}

export function saveTddCheckpoint(tasksDir: string, taskId: string, checkpoint: TddCheckpoint): void {
  const taskFile = findTaskFile(tasksDir, taskId);
  if (!taskFile) throw new Error(`Task '${taskId}' not found`);

  const task = parseTaskFile(taskFile);
  if (!task) throw new Error(`Could not parse task '${taskId}'`);

  const checkpointText = renderCheckpointSection(checkpoint);

  // Remove existing checkpoint section if present
  const sectionStart = task.body.indexOf('## TDD Checkpoint');
  if (sectionStart !== -1) {
    const afterHeader = task.body.slice(sectionStart);
    const nextSection = afterHeader.indexOf('\n## ', 1);
    const sectionEnd = nextSection === -1 ? task.body.length : sectionStart + nextSection;
    task.body = task.body.slice(0, sectionStart).trimEnd() + '\n\n' + checkpointText + task.body.slice(sectionEnd);
  } else {
    // Append the checkpoint section at the end
    task.body = task.body.trimEnd() + '\n\n' + checkpointText + '\n';
  }

  fs.writeFileSync(taskFile, renderTaskFile(task));
}

export function loadTddCheckpoint(tasksDir: string, taskId: string): TddCheckpoint | null {
  const taskFile = findTaskFile(tasksDir, taskId);
  if (!taskFile) return null;

  const task = parseTaskFile(taskFile);
  if (!task) return null;

  return parseCheckpointSection(task.body);
}

function mergeFileGroups(groups: string[][]): string[][] {
  const normalized = groups
    .map((group) => Array.from(new Set(group)).sort())
    .filter((group) => group.length > 0);
  const merged: string[][] = [];

  for (const group of normalized) {
    const overlapping = merged.filter((existing) => existing.some((file) => group.includes(file)));
    if (overlapping.length === 0) {
      merged.push(group);
      continue;
    }

    const combined = Array.from(new Set(overlapping.flat().concat(group))).sort();
    for (const overlap of overlapping) {
      const idx = merged.indexOf(overlap);
      if (idx >= 0) merged.splice(idx, 1);
    }
    merged.push(combined);
  }

  return merged.sort((a, b) => a[0]!.localeCompare(b[0]!));
}

export function splitIntoFileGroups(taskId: string, groups: string[][], scope?: string): BoardLane[] {
  const merged = mergeFileGroups(groups);
  const normalized = merged.length > 0 ? merged : [[]];

  return normalized.map((files, index) => ({
    id: `${taskId}-lane-${index + 1}`,
    task_ids: [taskId],
    status: 'queued',
    scope,
    files,
    current_agent: null,
    updated_at: new Date().toISOString(),
  }));
}

export function canAcquireFileLocks(files: string[], tasksDir: string): { ok: boolean; conflicts: string[] } {
  const tasks = loadAllTasks(tasksDir);
  const activeLocks = new Set(
    tasks
      .filter((task) => ['running', 'handoff'].includes(task.run_status))
      .flatMap((task) => task.file_locks.map((lock) => lock.path)),
  );
  const conflicts = Array.from(new Set(files.filter((file) => activeLocks.has(file))));
  return { ok: conflicts.length === 0, conflicts };
}

export function persistLaneTransition(
  boardDir: string,
  tasksDir: string,
  opts: PersistLaneTransitionOptions,
): void {
  const board = loadBoard(boardDir);
  const taskFile = findTaskFile(tasksDir, opts.taskId);
  if (!taskFile) throw new Error(`Task '${opts.taskId}' not found`);

  const task = parseTaskFile(taskFile);
  if (!task) throw new Error(`Could not parse task '${opts.taskId}'`);

  const now = new Date().toISOString();
  const files = opts.files ?? [];
  const fileLocks: FileLock[] =
    opts.status === 'done' || opts.status === 'failed'
      ? []
      : files.map((file) => ({
          path: file,
          lane_id: opts.laneId,
          agent: opts.agent ?? 'mpga-red-dev',
          acquired_at: task.started_at ?? now,
          heartbeat_at: now,
        }));

  task.lane_id = opts.laneId;
  task.run_status = opts.status;
  task.current_agent = opts.agent ?? null;
  task.file_locks = fileLocks;
  task.scope_locks =
    opts.scope && opts.status !== 'done' && opts.status !== 'failed'
      ? [
          {
            scope: opts.scope,
            lane_id: opts.laneId,
            agent: opts.agent ?? 'mpga-red-dev',
            acquired_at: task.started_at ?? now,
            heartbeat_at: now,
          },
        ]
      : [];
  task.started_at = task.started_at ?? now;
  task.finished_at = opts.status === 'done' || opts.status === 'failed' ? now : null;
  task.heartbeat_at = opts.status === 'done' || opts.status === 'failed' ? null : now;
  task.updated = now;

  board.lanes[opts.laneId] = {
    id: opts.laneId,
    task_ids: [opts.taskId],
    status:
      opts.status === 'handoff'
        ? 'running'
        : opts.status === 'queued' || opts.status === 'running' || opts.status === 'done' || opts.status === 'failed'
          ? opts.status
          : 'running',
    scope: opts.scope,
    files,
    current_agent: opts.agent ?? null,
    updated_at: now,
  };
  board.active_runs[`${opts.laneId}:${opts.taskId}`] = {
    id: `${opts.laneId}:${opts.taskId}`,
    lane_id: opts.laneId,
    task_id: opts.taskId,
    status: opts.status,
    agent: opts.agent ?? null,
    started_at: task.started_at ?? now,
    finished_at: task.finished_at,
  };

  fs.writeFileSync(taskFile, renderTaskFile(task));
  recalcStats(board, tasksDir);
  saveBoard(boardDir, board);
  writeBoardLiveSnapshot(board, tasksDir, boardDir);
  writeBoardLiveHtml(boardDir);
}

export function runDevelopTask(
  taskId: string,
  opts: { parallel?: string; lanes?: number; dashboard?: boolean },
): string[] {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const boardDir = path.join(projectRoot, 'MPGA', 'board');
  const tasksDir = path.join(boardDir, 'tasks');
  const taskFile = findTaskFile(tasksDir, taskId);
  if (!taskFile) throw new Error(`Task '${taskId}' not found`);

  const task = parseTaskFile(taskFile);
  if (!task) throw new Error(`Could not parse task '${taskId}'`);

  // Check for an existing TDD checkpoint and resume from that stage
  const checkpoint = loadTddCheckpoint(tasksDir, taskId);
  const agentForStage: Record<string, string> = {
    red: 'mpga-red-dev',
    green: 'mpga-green-dev',
    blue: 'mpga-blue-dev',
    review: 'mpga-reviewer',
  };
  const resumeAgent = checkpoint ? (agentForStage[checkpoint.stage] ?? 'mpga-red-dev') : 'mpga-red-dev';
  if (checkpoint) {
    task.tdd_stage = checkpoint.stage as TddStage;
    fs.writeFileSync(taskFile, renderTaskFile(task));
  }

  const filePaths = task.file_locks.map((lock) => lock.path);
  const initialGroups =
    filePaths.length === 0
      ? [[]]
      : opts.parallel === 'none'
        ? [filePaths] // Consolidate all files into a single lane
        : filePaths.map((p) => [p]); // Each file gets its own lane (auto/default)
  const lanes = splitIntoFileGroups(taskId, initialGroups, task.scopes[0]);
  const maxLanes = opts.lanes && opts.lanes > 0 ? opts.lanes : lanes.length;
  const scheduled = lanes.slice(0, maxLanes);

  const launched: BoardLane[] = [];
  for (const lane of scheduled) {
    // Check file locks before scheduling each lane
    if (lane.files.length > 0) {
      const lockCheck = canAcquireFileLocks(lane.files, tasksDir);
      if (!lockCheck.ok) continue; // Skip lanes with conflicting file locks
    }

    persistLaneTransition(boardDir, tasksDir, {
      taskId,
      laneId: lane.id,
      status: 'running',
      agent: resumeAgent,
      files: lane.files,
      scope: lane.scope,
    });
    launched.push(lane);
  }

  if (opts.dashboard) {
    writeBoardLiveHtml(boardDir);
  }

  return launched.map((lane) => lane.id);
}
