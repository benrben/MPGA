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

// Mock child_process for git commands
const mockExecSync = vi.fn<(cmd: string) => Buffer>(() => Buffer.from(''));
vi.mock('child_process', () => ({
  execSync: (...args: unknown[]) => mockExecSync(args[0] as string),
}));

// ---------------------------------------------------------------------------
// Imports (after mocks)
// ---------------------------------------------------------------------------

import { registerPr } from './pr.js';
import { log } from '../core/logger.js';

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
  opts: { milestone?: string; tasks?: Array<{ id: string; title: string; overrides?: Record<string, unknown> }> } = {},
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
  registerPr(program);
  return program;
}

// ---------------------------------------------------------------------------
// Tests: pr command
// ---------------------------------------------------------------------------

describe('pr command', () => {
  let tmpDir: string;
  let consoleSpy: ReturnType<typeof vi.spyOn>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let exitSpy: any;

  beforeEach(() => {
    vi.clearAllMocks();
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-pr-'));
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

  it('exits with error when MPGA is not initialized', async () => {
    const program = createProgram();
    await expect(program.parseAsync(['node', 'test', 'pr'])).rejects.toThrow();
    expect(log.error).toHaveBeenCalledWith(expect.stringContaining('not initialized'));
  });

  it('generates PR description with branch name and commits', async () => {
    seedProject(tmpDir);
    mockExecSync.mockImplementation((cmd: string) => {
      if (cmd.includes('rev-parse --abbrev-ref HEAD')) return Buffer.from('feat/add-auth\n');
      if (cmd.includes('merge-base')) return Buffer.from('abc123\n');
      if (cmd.includes('git log')) return Buffer.from('abc456 Add authentication module\ndef789 Add login tests\n');
      if (cmd.includes('git diff --name-only')) return Buffer.from('src/auth.ts\nsrc/auth.test.ts\n');
      return Buffer.from('');
    });

    const program = createProgram();
    await program.parseAsync(['node', 'test', 'pr']);

    const allOutput = consoleSpy.mock.calls.map((c) => String(c[0])).join('\n');
    expect(allOutput).toContain('feat/add-auth');
    expect(allOutput).toContain('Add authentication module');
    expect(allOutput).toContain('Add login tests');
  });

  it('includes affected scopes in PR description', async () => {
    seedProject(tmpDir);
    // Create scope files
    const scopesDir = path.join(tmpDir, 'MPGA', 'scopes');
    fs.mkdirSync(scopesDir, { recursive: true });
    fs.writeFileSync(path.join(scopesDir, 'src-auth.md'), '# auth scope\n');

    mockExecSync.mockImplementation((cmd: string) => {
      if (cmd.includes('rev-parse --abbrev-ref HEAD')) return Buffer.from('feat/auth\n');
      if (cmd.includes('merge-base')) return Buffer.from('abc123\n');
      if (cmd.includes('git log')) return Buffer.from('abc456 Update auth\n');
      if (cmd.includes('git diff --name-only')) return Buffer.from('src/auth/login.ts\n');
      return Buffer.from('');
    });

    const program = createProgram();
    await program.parseAsync(['node', 'test', 'pr']);

    const allOutput = consoleSpy.mock.calls.map((c) => String(c[0])).join('\n');
    expect(allOutput).toContain('src/auth/login.ts');
  });

  it('includes evidence links from done tasks', async () => {
    seedProject(tmpDir, {
      tasks: [
        {
          id: 'T001',
          title: 'Implement auth',
          overrides: {
            column: 'done',
            evidence_produced: ['[E] src/auth.ts — login handler'],
          },
        },
      ],
    });
    mockExecSync.mockImplementation((cmd: string) => {
      if (cmd.includes('rev-parse --abbrev-ref HEAD')) return Buffer.from('feat/auth\n');
      if (cmd.includes('merge-base')) return Buffer.from('abc123\n');
      if (cmd.includes('git log')) return Buffer.from('abc456 Add auth\n');
      if (cmd.includes('git diff --name-only')) return Buffer.from('src/auth.ts\n');
      return Buffer.from('');
    });

    const program = createProgram();
    await program.parseAsync(['node', 'test', 'pr']);

    const allOutput = consoleSpy.mock.calls.map((c) => String(c[0])).join('\n');
    expect(allOutput).toContain('[E] src/auth.ts');
  });

  it('handles git command failures gracefully', async () => {
    seedProject(tmpDir);
    mockExecSync.mockImplementation(() => {
      throw new Error('not a git repository');
    });

    const program = createProgram();
    await expect(program.parseAsync(['node', 'test', 'pr'])).rejects.toThrow();
    expect(log.error).toHaveBeenCalledWith(expect.stringContaining('git'));
  });
});

// ---------------------------------------------------------------------------
// Tests: decision command
// ---------------------------------------------------------------------------

describe('decision command', () => {
  let tmpDir: string;
  let consoleSpy: ReturnType<typeof vi.spyOn>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let exitSpy: any;

  beforeEach(() => {
    vi.clearAllMocks();
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-decision-'));
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

  it('exits with error when MPGA is not initialized', async () => {
    const program = createProgram();
    await expect(
      program.parseAsync(['node', 'test', 'decision', 'Use PostgreSQL']),
    ).rejects.toThrow();
    expect(log.error).toHaveBeenCalledWith(expect.stringContaining('not initialized'));
  });

  it('creates ADR file in MPGA/decisions directory', async () => {
    const mpgaDir = path.join(tmpDir, 'MPGA');
    fs.mkdirSync(mpgaDir, { recursive: true });

    const program = createProgram();
    await program.parseAsync(['node', 'test', 'decision', 'Use PostgreSQL']);

    const decisionsDir = path.join(mpgaDir, 'decisions');
    expect(fs.existsSync(decisionsDir)).toBe(true);

    const files = fs.readdirSync(decisionsDir);
    expect(files.length).toBe(1);

    const today = new Date().toISOString().split('T')[0];
    expect(files[0]).toContain(today);
    expect(files[0]).toContain('use-postgresql');
    expect(files[0]).toMatch(/\.md$/);
  });

  it('ADR file contains all required template sections', async () => {
    const mpgaDir = path.join(tmpDir, 'MPGA');
    fs.mkdirSync(mpgaDir, { recursive: true });

    const program = createProgram();
    await program.parseAsync(['node', 'test', 'decision', 'Use PostgreSQL']);

    const decisionsDir = path.join(mpgaDir, 'decisions');
    const files = fs.readdirSync(decisionsDir);
    const content = fs.readFileSync(path.join(decisionsDir, files[0]), 'utf-8');

    expect(content).toContain('# ADR: Use PostgreSQL');
    expect(content).toContain('## Status');
    expect(content).toContain('Proposed');
    expect(content).toContain('## Context');
    expect(content).toContain('## Decision');
    expect(content).toContain('## Consequences');
  });

  it('creates ADR with slugified filename', async () => {
    const mpgaDir = path.join(tmpDir, 'MPGA');
    fs.mkdirSync(mpgaDir, { recursive: true });

    const program = createProgram();
    await program.parseAsync(['node', 'test', 'decision', 'Switch to Event-Driven Architecture']);

    const decisionsDir = path.join(mpgaDir, 'decisions');
    const files = fs.readdirSync(decisionsDir);
    expect(files[0]).toContain('switch-to-event-driven-architecture');
  });

  it('logs success message with file path', async () => {
    const mpgaDir = path.join(tmpDir, 'MPGA');
    fs.mkdirSync(mpgaDir, { recursive: true });

    const program = createProgram();
    await program.parseAsync(['node', 'test', 'decision', 'Use Redis']);

    expect(log.success).toHaveBeenCalledWith(expect.stringContaining('ADR created'));
  });

  it('numbers ADRs sequentially', async () => {
    const mpgaDir = path.join(tmpDir, 'MPGA');
    const decisionsDir = path.join(mpgaDir, 'decisions');
    fs.mkdirSync(decisionsDir, { recursive: true });
    // Pre-create an existing ADR
    fs.writeFileSync(
      path.join(decisionsDir, '001-2026-03-20-existing-decision.md'),
      '# ADR: Existing\n',
    );

    const program = createProgram();
    await program.parseAsync(['node', 'test', 'decision', 'New Decision']);

    const files = fs.readdirSync(decisionsDir).sort();
    expect(files.length).toBe(2);
    // The new file should have a higher number
    expect(files[1]).toMatch(/^002-/);
  });
});
