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

// We only mock findProjectRoot; the rest of config.js uses real implementations.
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

import { completeActiveMilestone } from './milestone.js';
import { loadBoard } from '../board/board.js';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeBoardJson(overrides: Record<string, unknown> = {}): string {
  return (
    JSON.stringify(
      {
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
        ...overrides,
      },
      null,
      2,
    ) + '\n'
  );
}

/** Seed a minimal MPGA project structure in a temp dir. */
function seedProject(
  root: string,
  opts: { milestone?: string; milestones?: string[]; withSummary?: string[] } = {},
) {
  const boardDir = path.join(root, 'MPGA', 'board');
  const tasksDir = path.join(boardDir, 'tasks');
  const milestonesDir = path.join(root, 'MPGA', 'milestones');

  fs.mkdirSync(tasksDir, { recursive: true });
  fs.mkdirSync(milestonesDir, { recursive: true });

  fs.writeFileSync(
    path.join(boardDir, 'board.json'),
    makeBoardJson({ milestone: opts.milestone ?? null }),
  );
  fs.writeFileSync(path.join(boardDir, 'BOARD.md'), '# Board\n\nNo tasks yet.\n');

  // Create milestone directories
  for (const m of opts.milestones ?? []) {
    const mDir = path.join(milestonesDir, m);
    fs.mkdirSync(mDir, { recursive: true });
  }

  // Write SUMMARY.md for completed milestones
  for (const m of opts.withSummary ?? []) {
    const summaryPath = path.join(milestonesDir, m, 'SUMMARY.md');
    fs.writeFileSync(summaryPath, `# ${m} — Summary\n`);
  }
}

// ---------------------------------------------------------------------------
// Tests: completeActiveMilestone (existing tests preserved)
// ---------------------------------------------------------------------------

describe('completeActiveMilestone', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-milestone-'));
    const boardDir = path.join(tmpDir, 'MPGA', 'board');
    const tasksDir = path.join(boardDir, 'tasks');
    const milestoneDir = path.join(tmpDir, 'MPGA', 'milestones', 'M001-test');
    fs.mkdirSync(tasksDir, { recursive: true });
    fs.mkdirSync(milestoneDir, { recursive: true });
    fs.writeFileSync(
      path.join(boardDir, 'board.json'),
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
        },
        null,
        2,
      ) + '\n',
    );
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('clears board.milestone and persists board.json after completion', () => {
    const result = completeActiveMilestone(tmpDir);
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.milestoneSlug).toBe('M001-test');

    const boardDir = path.join(tmpDir, 'MPGA', 'board');
    const board = loadBoard(boardDir);
    expect(board.milestone).toBeNull();

    const raw = fs.readFileSync(path.join(boardDir, 'board.json'), 'utf-8');
    const parsed = JSON.parse(raw) as { milestone: string | null };
    expect(parsed.milestone).toBeNull();
  });

  it('writes SUMMARY.md under the milestone directory', () => {
    const result = completeActiveMilestone(tmpDir);
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.milestoneSlug).toBe('M001-test');
    const summaryPath = path.join(tmpDir, 'MPGA', 'milestones', 'M001-test', 'SUMMARY.md');
    expect(fs.existsSync(summaryPath)).toBe(true);
    const body = fs.readFileSync(summaryPath, 'utf-8');
    expect(body).toContain('M001-test');
    expect(body).toContain('Tasks completed:');
  });

  it('returns error when no active milestone', () => {
    const boardDir = path.join(tmpDir, 'MPGA', 'board');
    const board = loadBoard(boardDir);
    board.milestone = null;
    fs.writeFileSync(path.join(boardDir, 'board.json'), JSON.stringify(board, null, 2) + '\n');

    const result = completeActiveMilestone(tmpDir);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error).toBe('no_active_milestone');
  });

  it('writes SUMMARY.md with today date and stats', () => {
    const result = completeActiveMilestone(tmpDir);
    expect(result.ok).toBe(true);
    const summaryPath = path.join(tmpDir, 'MPGA', 'milestones', 'M001-test', 'SUMMARY.md');
    const body = fs.readFileSync(summaryPath, 'utf-8');
    const today = new Date().toISOString().split('T')[0];
    expect(body).toContain(`Completed: ${today}`);
    expect(body).toContain('Evidence links produced:');
    expect(body).toContain('Outcome');
  });

  it('regenerates BOARD.md after completion', () => {
    completeActiveMilestone(tmpDir);
    const boardMdPath = path.join(tmpDir, 'MPGA', 'board', 'BOARD.md');
    expect(fs.existsSync(boardMdPath)).toBe(true);
    const content = fs.readFileSync(boardMdPath, 'utf-8');
    // After clearing milestone, BOARD.md should say "No active milestone"
    expect(content).toContain('No active milestone');
  });
});

// ---------------------------------------------------------------------------
// Tests: registerMilestone — milestone new
// ---------------------------------------------------------------------------

describe('registerMilestone — milestone new', () => {
  let tmpDir: string;
  let consoleSpy: ReturnType<typeof vi.spyOn>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let exitSpy: any;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-ms-new-'));
    seedProject(tmpDir);
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

  it('creates milestone directory with slugified name', async () => {
    const { registerMilestone } = await import('./milestone.js');
    const program = new Command();
    program.exitOverride();
    registerMilestone(program);
    await program.parseAsync(['node', 'test', 'milestone', 'new', 'My Cool Feature']);

    const milestonesDir = path.join(tmpDir, 'MPGA', 'milestones');
    const dirs = fs.readdirSync(milestonesDir);
    const milestoneDir = dirs.find((d) => d.startsWith('M001'));
    expect(milestoneDir).toBeDefined();
    expect(milestoneDir).toBe('M001-my-cool-feature');
  });

  it('creates PLAN.md with milestone name and template', async () => {
    const { registerMilestone } = await import('./milestone.js');
    const program = new Command();
    program.exitOverride();
    registerMilestone(program);
    await program.parseAsync(['node', 'test', 'milestone', 'new', 'Auth Refactor']);

    const milestonesDir = path.join(tmpDir, 'MPGA', 'milestones');
    const dirs = fs.readdirSync(milestonesDir);
    const milestoneDir = dirs.find((d) => d.startsWith('M001'));
    expect(milestoneDir).toBeDefined();

    const planPath = path.join(milestonesDir, milestoneDir!, 'PLAN.md');
    expect(fs.existsSync(planPath)).toBe(true);
    const content = fs.readFileSync(planPath, 'utf-8');
    expect(content).toContain('Auth Refactor');
    expect(content).toContain('Objective');
    expect(content).toContain('Tasks');
    expect(content).toContain('Acceptance criteria');
  });

  it('creates CONTEXT.md with milestone name and template', async () => {
    const { registerMilestone } = await import('./milestone.js');
    const program = new Command();
    program.exitOverride();
    registerMilestone(program);
    await program.parseAsync(['node', 'test', 'milestone', 'new', 'Data Pipeline']);

    const milestonesDir = path.join(tmpDir, 'MPGA', 'milestones');
    const dirs = fs.readdirSync(milestonesDir);
    const milestoneDir = dirs.find((d) => d.startsWith('M001'));
    expect(milestoneDir).toBeDefined();

    const contextPath = path.join(milestonesDir, milestoneDir!, 'CONTEXT.md');
    expect(fs.existsSync(contextPath)).toBe(true);
    const content = fs.readFileSync(contextPath, 'utf-8');
    expect(content).toContain('Data Pipeline');
    expect(content).toContain('Background');
    expect(content).toContain('Constraints');
    expect(content).toContain('Dependencies');
    expect(content).toContain('Decisions');
  });

  it('links the new milestone to the board', async () => {
    const { registerMilestone } = await import('./milestone.js');
    const program = new Command();
    program.exitOverride();
    registerMilestone(program);
    await program.parseAsync(['node', 'test', 'milestone', 'new', 'Test Link']);

    const boardDir = path.join(tmpDir, 'MPGA', 'board');
    const board = loadBoard(boardDir);
    expect(board.milestone).toBe('M001-test-link');
  });

  it('increments milestone IDs for subsequent milestones', async () => {
    // Create first milestone by seeding directory
    const milestonesDir = path.join(tmpDir, 'MPGA', 'milestones');
    fs.mkdirSync(path.join(milestonesDir, 'M001-first'), { recursive: true });

    const { registerMilestone } = await import('./milestone.js');
    const program = new Command();
    program.exitOverride();
    registerMilestone(program);
    await program.parseAsync(['node', 'test', 'milestone', 'new', 'Second']);

    const dirs = fs.readdirSync(milestonesDir).sort();
    expect(dirs).toContain('M001-first');
    const secondDir = dirs.find((d) => d.startsWith('M002'));
    expect(secondDir).toBe('M002-second');
  });

  it('calls log.success after creation', async () => {
    const { registerMilestone } = await import('./milestone.js');
    const { log } = await import('../core/logger.js');
    const program = new Command();
    program.exitOverride();
    registerMilestone(program);
    await program.parseAsync(['node', 'test', 'milestone', 'new', 'Success Test']);

    expect(log.success).toHaveBeenCalledWith(expect.stringContaining('Created milestone'));
  });
});

// ---------------------------------------------------------------------------
// Tests: registerMilestone — milestone list
// ---------------------------------------------------------------------------

describe('registerMilestone — milestone list', () => {
  let tmpDir: string;
  let consoleSpy: ReturnType<typeof vi.spyOn>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let exitSpy: any;

  beforeEach(() => {
    vi.clearAllMocks();
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-ms-list-'));
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

  it('shows info message when no milestones exist', async () => {
    seedProject(tmpDir);
    const { registerMilestone } = await import('./milestone.js');
    const { log } = await import('../core/logger.js');
    const program = new Command();
    program.exitOverride();
    registerMilestone(program);
    await program.parseAsync(['node', 'test', 'milestone', 'list']);

    expect(log.info).toHaveBeenCalledWith(expect.stringContaining('No milestones yet'));
  });

  it('lists active milestones with table output', async () => {
    seedProject(tmpDir, { milestones: ['M001-alpha', 'M002-beta'] });
    const { registerMilestone } = await import('./milestone.js');
    const { log } = await import('../core/logger.js');
    const program = new Command();
    program.exitOverride();
    registerMilestone(program);
    await program.parseAsync(['node', 'test', 'milestone', 'list']);

    expect(log.header).toHaveBeenCalledWith('Milestones');
    expect(log.table).toHaveBeenCalledTimes(1);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const tableArg = (log.table as any).mock.calls[0][0] as string[][];
    // Header row + 2 data rows
    expect(tableArg.length).toBe(3);
    expect(tableArg[0]).toEqual(['ID', 'Name', 'Status', 'Created']);
    // Check milestone IDs
    expect(tableArg[1][0]).toBe('M001');
    expect(tableArg[2][0]).toBe('M002');
  });

  it('marks completed milestones (those with SUMMARY.md) correctly', async () => {
    seedProject(tmpDir, {
      milestones: ['M001-done-thing', 'M002-active-thing'],
      withSummary: ['M001-done-thing'],
    });
    vi.resetModules();
    const { registerMilestone } = await import('./milestone.js');
    const { log } = await import('../core/logger.js');
    const program = new Command();
    program.exitOverride();
    registerMilestone(program);
    await program.parseAsync(['node', 'test', 'milestone', 'list']);

    expect(log.table).toHaveBeenCalledTimes(1);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const tableArg = (log.table as any).mock.calls[0][0] as string[][];
    // M001 should be complete, M002 should be active
    const m001Row = tableArg.find((r) => r[0] === 'M001');
    const m002Row = tableArg.find((r) => r[0] === 'M002');
    expect(m001Row).toBeDefined();
    expect(m002Row).toBeDefined();
    expect(m001Row![2]).toContain('complete');
    expect(m002Row![2]).toContain('active');
  });
});

// ---------------------------------------------------------------------------
// Tests: registerMilestone — milestone status
// ---------------------------------------------------------------------------

describe('registerMilestone — milestone status', () => {
  let tmpDir: string;
  let consoleSpy: ReturnType<typeof vi.spyOn>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let exitSpy: any;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-ms-status-'));
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

  it('exits with error when no board exists', async () => {
    // Don't seed any project — no board.json
    fs.mkdirSync(path.join(tmpDir, 'MPGA'), { recursive: true });

    const { registerMilestone } = await import('./milestone.js');
    const { log } = await import('../core/logger.js');
    const program = new Command();
    program.exitOverride();
    registerMilestone(program);

    await expect(program.parseAsync(['node', 'test', 'milestone', 'status'])).rejects.toThrow();

    expect(log.error).toHaveBeenCalledWith(expect.stringContaining('No board found'));
  });

  it('shows info message when no active milestone', async () => {
    seedProject(tmpDir, { milestone: undefined });
    const { registerMilestone } = await import('./milestone.js');
    const { log } = await import('../core/logger.js');
    const program = new Command();
    program.exitOverride();
    registerMilestone(program);
    await program.parseAsync(['node', 'test', 'milestone', 'status']);

    expect(log.info).toHaveBeenCalledWith(expect.stringContaining('No active milestone'));
  });

  it('shows progress for active milestone', async () => {
    seedProject(tmpDir, { milestone: 'M001-cool-feature' });
    const { registerMilestone } = await import('./milestone.js');
    const { log } = await import('../core/logger.js');
    const program = new Command();
    program.exitOverride();
    registerMilestone(program);
    await program.parseAsync(['node', 'test', 'milestone', 'status']);

    expect(log.header).toHaveBeenCalledWith(expect.stringContaining('M001-cool-feature'));
    // console.log is called with progress stats
    expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Progress'));
    expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('In flight'));
    expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Blocked'));
    expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Evidence'));
  });
});

// ---------------------------------------------------------------------------
// Tests: registerMilestone — milestone complete
// ---------------------------------------------------------------------------

describe('registerMilestone — milestone complete', () => {
  let tmpDir: string;
  let consoleSpy: ReturnType<typeof vi.spyOn>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let exitSpy: any;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-ms-complete-'));
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

  it('completes an active milestone and shows success message', async () => {
    seedProject(tmpDir, { milestone: 'M001-finish-me', milestones: ['M001-finish-me'] });

    const { registerMilestone } = await import('./milestone.js');
    const { log } = await import('../core/logger.js');
    const program = new Command();
    program.exitOverride();
    registerMilestone(program);
    await program.parseAsync(['node', 'test', 'milestone', 'complete']);

    expect(log.success).toHaveBeenCalledWith(expect.stringContaining('M001-finish-me'));
    expect(log.success).toHaveBeenCalledWith(expect.stringContaining('marked complete'));

    // Verify SUMMARY.md was written
    const summaryPath = path.join(tmpDir, 'MPGA', 'milestones', 'M001-finish-me', 'SUMMARY.md');
    expect(fs.existsSync(summaryPath)).toBe(true);

    // Verify board.milestone is now null
    const board = loadBoard(path.join(tmpDir, 'MPGA', 'board'));
    expect(board.milestone).toBeNull();
  });

  it('exits with error when no active milestone to complete', async () => {
    seedProject(tmpDir);

    const { registerMilestone } = await import('./milestone.js');
    const { log } = await import('../core/logger.js');
    const program = new Command();
    program.exitOverride();
    registerMilestone(program);

    await expect(program.parseAsync(['node', 'test', 'milestone', 'complete'])).rejects.toThrow();

    expect(log.error).toHaveBeenCalledWith(expect.stringContaining('No active milestone'));
  });
});
