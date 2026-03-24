import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';

export type Column = 'backlog' | 'todo' | 'in-progress' | 'testing' | 'review' | 'done';
export type Priority = 'critical' | 'high' | 'medium' | 'low';
export type TddStage = 'green' | 'red' | 'blue' | 'review' | 'done' | null;
export type TaskStatus = 'blocked' | 'stale' | 'rework' | 'paused' | null;
export type RunStatus = 'queued' | 'running' | 'handoff' | 'done' | 'failed';

export interface FileLock {
  path: string;
  lane_id: string;
  agent: string;
  acquired_at: string;
  heartbeat_at?: string | null;
}

export interface ScopeLock {
  scope: string;
  lane_id: string;
  agent: string;
  acquired_at: string;
  heartbeat_at?: string | null;
}

export interface Task {
  id: string;
  title: string;
  column: Column;
  status: TaskStatus;
  priority: Priority;
  milestone?: string;
  phase?: number;
  created: string;
  updated: string;
  assigned?: string;
  depends_on: string[];
  blocks: string[];
  scopes: string[];
  tdd_stage: TddStage;
  lane_id: string | null;
  run_status: RunStatus;
  current_agent: string | null;
  file_locks: FileLock[];
  scope_locks: ScopeLock[];
  started_at: string | null;
  finished_at: string | null;
  heartbeat_at: string | null;
  evidence_expected: string[];
  evidence_produced: string[];
  tags: string[];
  time_estimate: string;
  body: string;
}

export function taskFilename(id: string, title: string): string {
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 40);
  return `${id}-${slug}.md`;
}

export function renderTaskFile(task: Task): string {
  const frontmatter: Record<string, unknown> = {
    id: task.id,
    title: task.title,
    status: task.status ?? 'active',
    column: task.column,
    priority: task.priority,
    milestone: task.milestone ?? null,
    phase: task.phase ?? null,
    created: task.created,
    updated: task.updated,
    assigned: task.assigned ?? null,
    depends_on: task.depends_on,
    blocks: task.blocks,
    scopes: task.scopes,
    tdd_stage: task.tdd_stage,
    lane_id: task.lane_id,
    run_status: task.run_status,
    current_agent: task.current_agent,
    file_locks: task.file_locks,
    scope_locks: task.scope_locks,
    started_at: task.started_at,
    finished_at: task.finished_at,
    heartbeat_at: task.heartbeat_at,
    evidence_expected: task.evidence_expected,
    evidence_produced: task.evidence_produced,
    tags: task.tags,
    time_estimate: task.time_estimate,
  };

  const body =
    task.body ||
    `# ${task.id}: ${task.title}

## Description
(describe the task)

## Acceptance criteria
- [ ] (define measurable criteria)

## Evidence links (from scope)
(will be populated as work progresses)

## TDD trace
- 🔴 red-dev: (pending)
- 🟢 green-dev: (pending)
- 🔵 blue-dev: (pending)
- 📋 reviewer: (pending)

## Notes
(optional notes)

## History
- ${task.created}: created
`;

  const fm = Object.entries(frontmatter)
    .map(([k, v]) => {
      if (Array.isArray(v)) return `${k}: [${v.map((i) => JSON.stringify(i)).join(', ')}]`;
      if (v === null) return `${k}: null`;
      if (typeof v === 'string') return `${k}: ${JSON.stringify(v)}`;
      return `${k}: ${v}`;
    })
    .join('\n');

  return `---\n${fm}\n---\n\n${body}`;
}

export function parseTaskFile(filepath: string): Task | null {
  if (!fs.existsSync(filepath)) return null;
  try {
    const raw = fs.readFileSync(filepath, 'utf-8');
    const { data, content } = matter(raw);
    return {
      id: data.id,
      title: data.title,
      column: data.column ?? 'backlog',
      status: data.status === 'active' ? null : data.status,
      priority: data.priority ?? 'medium',
      milestone: data.milestone,
      phase: data.phase,
      created: data.created,
      updated: data.updated,
      assigned: data.assigned,
      depends_on: data.depends_on ?? [],
      blocks: data.blocks ?? [],
      scopes: data.scopes ?? [],
      tdd_stage: data.tdd_stage ?? null,
      lane_id: data.lane_id ?? null,
      run_status: data.run_status ?? 'queued',
      current_agent: data.current_agent ?? null,
      file_locks: data.file_locks ?? [],
      scope_locks: data.scope_locks ?? [],
      started_at: data.started_at ?? null,
      finished_at: data.finished_at ?? null,
      heartbeat_at: data.heartbeat_at ?? null,
      evidence_expected: data.evidence_expected ?? [],
      evidence_produced: data.evidence_produced ?? [],
      tags: data.tags ?? [],
      time_estimate: data.time_estimate ?? '5min',
      body: content.trim(),
    };
  } catch {
    return null;
  }
}

export function loadAllTasks(tasksDir: string): Task[] {
  if (!fs.existsSync(tasksDir)) return [];
  return fs
    .readdirSync(tasksDir)
    .filter((f) => f.endsWith('.md'))
    .map((f) => parseTaskFile(path.join(tasksDir, f)))
    .filter((t): t is Task => t !== null);
}
