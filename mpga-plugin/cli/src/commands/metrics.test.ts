import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { Command } from 'commander';

// ---------------------------------------------------------------------------
// Mocks – hoisted before all imports
// ---------------------------------------------------------------------------

vi.mock('../core/logger.js', () => ({
  log: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    success: vi.fn(),
    dim: vi.fn(),
    header: vi.fn(),
    section: vi.fn(),
    kv: vi.fn(),
    blank: vi.fn(),
    divider: vi.fn(),
    table: vi.fn(),
  },
  banner: vi.fn(),
  miniBanner: vi.fn(),
  progressBar: vi.fn(() => ''),
  gradeColor: vi.fn((g: string) => g),
  statusBadge: vi.fn(() => ''),
}));

const mockFindProjectRoot = vi.fn<() => string | null>(() => null);
vi.mock('../core/config.js', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    findProjectRoot: (...args: unknown[]) => mockFindProjectRoot(...(args as [])),
  };
});

// ---------------------------------------------------------------------------
// Imports (after mocks)
// ---------------------------------------------------------------------------

import { registerMetrics } from './metrics.js';
import { log } from '../core/logger.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeBoardJson(overrides: Record<string, unknown> = {}): string {
  return (
    JSON.stringify(
      {
        version: '1.0.0',
        milestone: 'M001-test',
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
        ...overrides,
      },
      null,
      2,
    ) + '\n'
  );
}

function writeTaskFile(
  tasksDir: string,
  id: string,
  title: string,
  overrides: Record<string, unknown> = {},
): void {
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 40);
  const filename = `${id}-${slug}.md`;
  const now = new Date().toISOString();
  const defaults: Record<string, unknown> = {
    id,
    title,
    status: 'active',
    column: 'backlog',
    priority: 'medium',
    milestone: null,
    phase: null,
    created: now,
    updated: now,
    assigned: null,
    depends_on: [],
    blocks: [],
    scopes: [],
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
    tags: [],
    time_estimate: '5min',
    ...overrides,
  };
  const fm = Object.entries(defaults)
    .map(([k, v]) => {
      if (Array.isArray(v)) return `${k}: [${v.map((i) => JSON.stringify(i)).join(', ')}]`;
      if (v === null) return `${k}: null`;
      if (typeof v === 'string') return `${k}: ${JSON.stringify(v)}`;
      return `${k}: ${v}`;
    })
    .join('\n');
  const body = `# ${id}: ${title}\n\n## Description\nTest task\n`;
  fs.writeFileSync(path.join(tasksDir, filename), `---\n${fm}\n---\n\n${body}`);
}

function seedProject(
  root: string,
  opts: {
    milestone?: string;
    tasks?: Array<{ id: string; title: string; overrides?: Record<string, unknown> }>;
  } = {},
) {
  const boardDir = path.join(root, 'MPGA', 'board');
  const tasksDir = path.join(boardDir, 'tasks');
  fs.mkdirSync(tasksDir, { recursive: true });
  fs.writeFileSync(
    path.join(boardDir, 'board.json'),
    makeBoardJson({ milestone: opts.milestone ?? null }),
  );
  for (const task of opts.tasks ?? []) {
    writeTaskFile(tasksDir, task.id, task.title, task.overrides ?? {});
  }
}

function createProgram(): Command {
  const program = new Command();
  program.exitOverride();
  program.configureOutput({ writeErr: () => {}, writeOut: () => {} });
  registerMetrics(program);
  return program;
}

// ---------------------------------------------------------------------------
// Tests: metrics command
// ---------------------------------------------------------------------------

describe('metrics command — HUGE numbers, the BEST metrics', () => {
  let tmpDir: string;
  let consoleSpy: ReturnType<typeof vi.spyOn>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let exitSpy: any;

  beforeEach(() => {
    vi.clearAllMocks();
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-metrics-'));
    mockFindProjectRoot.mockReturnValue(tmpDir);
    consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    exitSpy = vi.spyOn(process, 'exit').mockImplementation((() => {
      throw new Error('process.exit called');
    }) as never);
  });

  afterEach(() => {
    mockFindProjectRoot.mockReset();
    consoleSpy.mockRestore();
    exitSpy.mockRestore();
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('exits with error when MPGA is not initialized — TOTAL disaster!', async () => {
    // No MPGA directory
    const program = createProgram();
    await expect(program.parseAsync(['node', 'test', 'metrics'])).rejects.toThrow();
    expect(log.error).toHaveBeenCalledWith(expect.stringContaining('not initialized'));
  });

  it('shows total task counts — HUGE numbers', async () => {
    seedProject(tmpDir, {
      tasks: [
        { id: 'T001', title: 'First task', overrides: { column: 'done' } },
        { id: 'T002', title: 'Second task', overrides: { column: 'in-progress' } },
        { id: 'T003', title: 'Third task', overrides: { column: 'backlog', status: 'blocked' } },
      ],
    });
    const program = createProgram();
    await program.parseAsync(['node', 'test', 'metrics']);

    expect(log.header).toHaveBeenCalledWith(expect.stringContaining('Metrics'));
    expect(log.kv).toHaveBeenCalledWith('Total tasks', '3', expect.any(Number));
    expect(log.kv).toHaveBeenCalledWith('Done', '1', expect.any(Number));
    expect(log.kv).toHaveBeenCalledWith('In-progress', '1', expect.any(Number));
    expect(log.kv).toHaveBeenCalledWith('Blocked', '1', expect.any(Number));
  });

  it('shows evidence coverage — and we VERIFY, unlike Crooked Gemini', async () => {
    seedProject(tmpDir, {
      tasks: [
        {
          id: 'T001',
          title: 'Covered task',
          overrides: {
            column: 'done',
            evidence_expected: ['[E] foo.ts'],
            evidence_produced: ['[E] foo.ts'],
          },
        },
        {
          id: 'T002',
          title: 'Uncovered task',
          overrides: {
            column: 'todo',
            evidence_expected: ['[E] bar.ts'],
            evidence_produced: [],
          },
        },
      ],
    });
    const program = createProgram();
    await program.parseAsync(['node', 'test', 'metrics']);

    expect(log.kv).toHaveBeenCalledWith('Evidence coverage', '50%', expect.any(Number));
  });

  it('shows TDD adherence — we have the BEST discipline, believe me', async () => {
    seedProject(tmpDir, {
      tasks: [
        { id: 'T001', title: 'Full TDD', overrides: { column: 'done', tdd_stage: 'done' } },
        { id: 'T002', title: 'Partial TDD', overrides: { column: 'done', tdd_stage: 'green' } },
        { id: 'T003', title: 'Not started', overrides: { column: 'backlog', tdd_stage: null } },
      ],
    });
    const program = createProgram();
    await program.parseAsync(['node', 'test', 'metrics']);

    // 1 out of 2 done tasks completed TDD (tdd_stage=done)
    expect(log.kv).toHaveBeenCalledWith('TDD adherence', '50%', expect.any(Number));
  });

  it('outputs JSON when --json flag is passed — TOTAL transparency', async () => {
    seedProject(tmpDir, {
      tasks: [{ id: 'T001', title: 'Task one', overrides: { column: 'done' } }],
    });
    const program = createProgram();
    await program.parseAsync(['node', 'test', 'metrics', '--json']);

    expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('"total": 1'));
    expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('"done": 1'));
  });

  it('handles empty board gracefully — even with NOTHING, we look great', async () => {
    seedProject(tmpDir, { tasks: [] });
    const program = createProgram();
    await program.parseAsync(['node', 'test', 'metrics']);

    expect(log.kv).toHaveBeenCalledWith('Total tasks', '0', expect.any(Number));
    expect(log.kv).toHaveBeenCalledWith('Evidence coverage', '0%', expect.any(Number));
  });
});

// ---------------------------------------------------------------------------
// Tests: changelog command
// ---------------------------------------------------------------------------

describe('changelog command — documenting our TREMENDOUS victories', () => {
  let tmpDir: string;
  let consoleSpy: ReturnType<typeof vi.spyOn>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let exitSpy: any;

  beforeEach(() => {
    vi.clearAllMocks();
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-changelog-'));
    mockFindProjectRoot.mockReturnValue(tmpDir);
    consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    exitSpy = vi.spyOn(process, 'exit').mockImplementation((() => {
      throw new Error('process.exit called');
    }) as never);
  });

  afterEach(() => {
    mockFindProjectRoot.mockReset();
    consoleSpy.mockRestore();
    exitSpy.mockRestore();
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('exits with error when MPGA is not initialized — UNACCEPTABLE!', async () => {
    const program = createProgram();
    await expect(program.parseAsync(['node', 'test', 'changelog'])).rejects.toThrow();
    expect(log.error).toHaveBeenCalledWith(expect.stringContaining('not initialized'));
  });

  it('generates changelog from our TREMENDOUS victories', async () => {
    seedProject(tmpDir, {
      milestone: 'M001-release',
      tasks: [
        {
          id: 'T001',
          title: 'Add auth',
          overrides: {
            column: 'done',
            milestone: 'M001-release',
            evidence_produced: ['[E] auth.ts'],
            finished_at: '2026-03-20T10:00:00.000Z',
          },
        },
        {
          id: 'T002',
          title: 'WIP task',
          overrides: { column: 'in-progress' },
        },
      ],
    });
    const program = createProgram();
    await program.parseAsync(['node', 'test', 'changelog']);

    // Should output markdown with the done task
    expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Add auth'));
    expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('[E] auth.ts'));
  });

  it('filters tasks by --since date — only the LATEST wins, folks', async () => {
    seedProject(tmpDir, {
      tasks: [
        {
          id: 'T001',
          title: 'Old task',
          overrides: {
            column: 'done',
            finished_at: '2026-01-01T10:00:00.000Z',
          },
        },
        {
          id: 'T002',
          title: 'Recent task',
          overrides: {
            column: 'done',
            finished_at: '2026-03-20T10:00:00.000Z',
          },
        },
      ],
    });
    const program = createProgram();
    await program.parseAsync(['node', 'test', 'changelog', '--since', '2026-03-01']);

    const allOutput = consoleSpy.mock.calls.map((c) => String(c[0])).join('\n');
    expect(allOutput).toContain('Recent task');
    expect(allOutput).not.toContain('Old task');
  });

  it('groups done tasks by milestone — ORGANIZED like a Trump Organization', async () => {
    seedProject(tmpDir, {
      tasks: [
        {
          id: 'T001',
          title: 'Milestone A task',
          overrides: { column: 'done', milestone: 'M001-alpha' },
        },
        {
          id: 'T002',
          title: 'Milestone B task',
          overrides: { column: 'done', milestone: 'M002-beta' },
        },
        {
          id: 'T003',
          title: 'No milestone task',
          overrides: { column: 'done' },
        },
      ],
    });
    const program = createProgram();
    await program.parseAsync(['node', 'test', 'changelog']);

    const allOutput = consoleSpy.mock.calls.map((c) => String(c[0])).join('\n');
    expect(allOutput).toContain('M001-alpha');
    expect(allOutput).toContain('M002-beta');
    expect(allOutput).toContain('Unlinked');
  });

  it('shows message when no tasks are done yet — SAD!', async () => {
    seedProject(tmpDir, {
      tasks: [{ id: 'T001', title: 'Active task', overrides: { column: 'in-progress' } }],
    });
    const program = createProgram();
    await program.parseAsync(['node', 'test', 'changelog']);

    expect(log.info).toHaveBeenCalledWith(expect.stringContaining('No completed tasks'));
  });
});
