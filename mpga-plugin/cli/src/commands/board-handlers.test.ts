import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock dependencies before importing
vi.mock('../core/config.js', () => ({
  findProjectRoot: vi.fn(() => '/tmp/test-project'),
}));

vi.mock('../board/board.js', () => ({
  loadBoard: vi.fn(),
  checkWipLimit: vi.fn(),
  findTaskFile: vi.fn(),
}));

vi.mock('../board/task.js', () => ({
  parseTaskFile: vi.fn(),
  renderTaskFile: vi.fn(() => '---\nid: "T001"\n---\n# T001\n'),
}));

vi.mock('../board/board-md.js', () => ({
  renderBoardMd: vi.fn(() => '# Board'),
}));

vi.mock('../board/live.js', () => ({
  writeBoardLiveSnapshot: vi.fn(() => ''),
}));

vi.mock('../board/live-html.js', () => ({
  writeBoardLiveHtml: vi.fn(() => ''),
}));

vi.mock('./board-live-server.js', () => ({
  createBoardLiveServer: vi.fn(),
  openBoardLiveUrl: vi.fn(),
}));

vi.mock('./board.js', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./board.js')>();
  return {
    ...actual,
    persistBoard: vi.fn(),
  };
});

vi.mock('fs', async () => {
  const actual = await vi.importActual<typeof import('fs')>('fs');
  return {
    ...actual,
    default: {
      ...actual,
      writeFileSync: vi.fn(),
      mkdirSync: vi.fn(),
      existsSync: vi.fn(() => true),
      readdirSync: vi.fn(() => []),
    },
    writeFileSync: vi.fn(),
    mkdirSync: vi.fn(),
    existsSync: vi.fn(() => true),
    readdirSync: vi.fn(() => []),
  };
});

vi.mock('../core/logger.js', () => ({
  log: {
    error: vi.fn(),
    success: vi.fn(),
    dim: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    header: vi.fn(),
  },
}));

import { Command } from 'commander';
import { loadBoard, checkWipLimit, findTaskFile } from '../board/board.js';
import { parseTaskFile, renderTaskFile } from '../board/task.js';
import { log } from '../core/logger.js';
import { handleBoardClaim } from './board-handlers.js';
import { registerBoard } from './board.js';

function makeBoard(inProgressCount: number) {
  return {
    version: '1.0.0',
    milestone: null,
    updated: new Date().toISOString(),
    columns: {
      backlog: [],
      todo: ['T001'],
      'in-progress': Array.from({ length: inProgressCount }, (_, i) => `TWIP${i}`),
      testing: [],
      review: [],
      done: [],
    },
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
    next_task_id: 10,
    lanes: {},
    active_runs: {},
    scheduler: {
      lock_mode: 'file' as const,
      max_parallel_lanes: 3,
      split_strategy: 'file-groups' as const,
    },
    ui: { refresh_interval_ms: 2500, theme: 'mpga-signal' },
  };
}

function makeTask(column: string = 'todo') {
  return {
    id: 'T001',
    title: 'Test task',
    column,
    status: null,
    priority: 'medium',
    created: new Date().toISOString(),
    updated: new Date().toISOString(),
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
    body: '',
  };
}

function createProgram(): Command {
  const program = new Command();
  program.exitOverride();
  program.configureOutput({ writeErr: () => {}, writeOut: () => {} });
  registerBoard(program);
  return program;
}

describe('CLI enum validation', () => {
  it('rejects invalid priority in board add with choices error', async () => {
    const program = createProgram();
    await expect(
      program.parseAsync(['board', 'add', 'Test', '--priority', 'bogus'], { from: 'user' }),
    ).rejects.toThrow(/Allowed choices are/);
  });

  it('rejects invalid column in board add with choices error', async () => {
    const program = createProgram();
    await expect(
      program.parseAsync(['board', 'add', 'Test', '--column', 'bogus'], { from: 'user' }),
    ).rejects.toThrow(/Allowed choices are/);
  });

  it('rejects invalid tdd-stage in board update with choices error', async () => {
    const program = createProgram();
    await expect(
      program.parseAsync(['board', 'update', 'T001', '--tdd-stage', 'bogus'], { from: 'user' }),
    ).rejects.toThrow(/Allowed choices are/);
  });

  it('rejects invalid status in board update with choices error', async () => {
    const program = createProgram();
    await expect(
      program.parseAsync(['board', 'update', 'T001', '--status', 'bogus'], { from: 'user' }),
    ).rejects.toThrow(/Allowed choices are/);
  });

  it('rejects invalid priority in board update with choices error', async () => {
    const program = createProgram();
    await expect(
      program.parseAsync(['board', 'update', 'T001', '--priority', 'bogus'], { from: 'user' }),
    ).rejects.toThrow(/Allowed choices are/);
  });
});

describe('handleBoardClaim', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('rejects claim when in-progress WIP limit is reached', () => {
    const board = makeBoard(3); // 3 tasks already in-progress, limit is 3
    vi.mocked(loadBoard).mockReturnValue(board);
    vi.mocked(checkWipLimit).mockReturnValue(false);
    vi.mocked(findTaskFile).mockReturnValue('/tmp/test-project/MPGA/board/tasks/T001-test.md');
    vi.mocked(parseTaskFile).mockReturnValue(makeTask('todo') as any);

    const mockExit = vi.spyOn(process, 'exit').mockImplementation((() => {
      throw new Error('process.exit called');
    }) as any);

    expect(() => handleBoardClaim('T001', {})).toThrow('process.exit called');
    expect(log.error).toHaveBeenCalledWith(expect.stringContaining('WIP limit'));
    expect(board.columns['in-progress']).not.toContain('T001');

    mockExit.mockRestore();
  });

  it('allows claim when WIP limit is not reached', () => {
    const board = makeBoard(1); // only 1 task in-progress, limit is 3
    vi.mocked(loadBoard).mockReturnValue(board);
    vi.mocked(checkWipLimit).mockReturnValue(true);
    vi.mocked(findTaskFile).mockReturnValue('/tmp/test-project/MPGA/board/tasks/T001-test.md');
    vi.mocked(parseTaskFile).mockReturnValue(makeTask('todo') as any);

    handleBoardClaim('T001', {});

    expect(log.success).toHaveBeenCalledWith(expect.stringContaining('T001'));
    expect(board.columns['in-progress']).toContain('T001');
  });

  it('allows claim with --force even when WIP limit is reached', () => {
    const board = makeBoard(3); // 3 tasks in-progress, limit is 3
    vi.mocked(loadBoard).mockReturnValue(board);
    vi.mocked(checkWipLimit).mockReturnValue(false);
    vi.mocked(findTaskFile).mockReturnValue('/tmp/test-project/MPGA/board/tasks/T001-test.md');
    vi.mocked(parseTaskFile).mockReturnValue(makeTask('todo') as any);

    handleBoardClaim('T001', { force: true } as any);

    expect(log.success).toHaveBeenCalledWith(expect.stringContaining('T001'));
    expect(board.columns['in-progress']).toContain('T001');
  });
});
