import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { Command } from 'commander';
import { registerBoard } from './board.js';
import { registerEvidence } from './evidence.js';
import { registerDrift } from './drift.js';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('../core/config.js', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    findProjectRoot: () => (globalThis as Record<string, unknown>).__MPGA_TEST_ROOT__ as string,
    loadConfig: () => ({
      ...(actual.DEFAULT_CONFIG as Record<string, unknown>),
      drift: { ciThreshold: 80, hookMode: 'quick', autoSync: false },
    }),
  };
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

let tmpDir: string;
let logSpy: ReturnType<typeof vi.spyOn>;
let errorSpy: ReturnType<typeof vi.spyOn>;

function captured(): string {
  return logSpy.mock.calls.map((c) => c.join(' ')).join('\n');
}

function capturedErr(): string {
  return errorSpy.mock.calls.map((c) => c.join(' ')).join('\n');
}

function makeBoardJson(overrides: Record<string, unknown> = {}): string {
  return (
    JSON.stringify(
      {
        version: '1.0.0',
        milestone: null,
        updated: new Date().toISOString(),
        columns: {
          backlog: [],
          todo: [],
          'in-progress': [],
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
        next_task_id: 1,
        ...overrides,
      },
      null,
      2,
    ) + '\n'
  );
}

function makeTaskFile(id: string, title: string, column = 'backlog', priority = 'medium'): string {
  const now = new Date().toISOString();
  return [
    '---',
    `id: "${id}"`,
    `title: "${title}"`,
    `status: "active"`,
    `column: "${column}"`,
    `priority: "${priority}"`,
    `milestone: null`,
    `phase: null`,
    `created: "${now}"`,
    `updated: "${now}"`,
    `assigned: null`,
    `depends_on: []`,
    `blocks: []`,
    `scopes: []`,
    `tdd_stage: null`,
    `evidence_expected: []`,
    `evidence_produced: []`,
    `tags: []`,
    `time_estimate: "5min"`,
    '---',
    '',
    `# ${id}: ${title}`,
    '',
  ].join('\n');
}

function scaffold(): void {
  const boardDir = path.join(tmpDir, 'MPGA', 'board');
  const tasksDir = path.join(boardDir, 'tasks');
  const scopesDir = path.join(tmpDir, 'MPGA', 'scopes');
  const srcDir = path.join(tmpDir, 'src');

  fs.mkdirSync(tasksDir, { recursive: true });
  fs.mkdirSync(scopesDir, { recursive: true });
  fs.mkdirSync(srcDir, { recursive: true });

  fs.writeFileSync(path.join(boardDir, 'board.json'), makeBoardJson());

  // A source file so evidence links can resolve
  fs.writeFileSync(
    path.join(srcDir, 'utils.ts'),
    [
      'export function add(a: number, b: number): number {',
      '  return a + b;',
      '}',
      '',
      'export function subtract(a: number, b: number): number {',
      '  return a - b;',
      '}',
      '',
    ].join('\n'),
  );

  // A scope file with evidence links pointing to the source file
  fs.writeFileSync(
    path.join(scopesDir, 'core.md'),
    [
      '# Scope: core',
      '',
      '## Evidence',
      '[E] src/utils.ts:1-3 :: add()',
      '[E] src/utils.ts:5-7 :: subtract()',
      '',
      '## Known unknowns',
      '[Unknown] Need to investigate divide-by-zero handling',
      '',
    ].join('\n'),
  );
}

function makeProgram(): Command {
  const program = new Command();
  program.exitOverride();
  program.configureOutput({
    writeOut: () => {},
    writeErr: () => {},
  });
  return program;
}

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-bed-test-'));
  (globalThis as Record<string, unknown>).__MPGA_TEST_ROOT__ = tmpDir;
  scaffold();
  logSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
  errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  logSpy.mockRestore();
  errorSpy.mockRestore();
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

// ===========================================================================
// Board command tests
// ===========================================================================

describe('board show', () => {
  it('displays the board with no tasks', async () => {
    const program = makeProgram();
    registerBoard(program);

    await program.parseAsync(['node', 'mpga', 'board', 'show']);

    const output = captured();
    expect(output).toContain('Board');
    expect(output).toContain('No tasks yet');
  });

  it('displays the board with tasks', async () => {
    // Seed a task file
    const tasksDir = path.join(tmpDir, 'MPGA', 'board', 'tasks');
    fs.writeFileSync(
      path.join(tasksDir, 'T001-setup-project.md'),
      makeTaskFile('T001', 'Setup project', 'backlog'),
    );

    const boardDir = path.join(tmpDir, 'MPGA', 'board');
    fs.writeFileSync(
      path.join(boardDir, 'board.json'),
      makeBoardJson({
        columns: {
          backlog: ['T001'],
          todo: [],
          'in-progress': [],
          testing: [],
          review: [],
          done: [],
        },
        next_task_id: 2,
      }),
    );

    const program = makeProgram();
    registerBoard(program);

    await program.parseAsync(['node', 'mpga', 'board', 'show']);

    const output = captured();
    expect(output).toContain('T001');
    expect(output).toContain('Setup project');
  });

  it('outputs JSON when --json is passed', async () => {
    const tasksDir = path.join(tmpDir, 'MPGA', 'board', 'tasks');
    fs.writeFileSync(
      path.join(tasksDir, 'T001-setup.md'),
      makeTaskFile('T001', 'Setup', 'backlog'),
    );

    const boardDir = path.join(tmpDir, 'MPGA', 'board');
    fs.writeFileSync(
      path.join(boardDir, 'board.json'),
      makeBoardJson({
        columns: {
          backlog: ['T001'],
          todo: [],
          'in-progress': [],
          testing: [],
          review: [],
          done: [],
        },
        next_task_id: 2,
      }),
    );

    const program = makeProgram();
    registerBoard(program);

    await program.parseAsync(['node', 'mpga', 'board', 'show', '--json']);

    const output = captured();
    const parsed = JSON.parse(output);
    expect(parsed).toHaveProperty('board');
    expect(parsed).toHaveProperty('tasks');
    expect(Array.isArray(parsed.tasks)).toBe(true);
    expect(parsed.tasks.length).toBe(1);
    expect(parsed.tasks[0].id).toBe('T001');
  });
});

describe('board add', () => {
  it('creates a new task with default options', async () => {
    const program = makeProgram();
    registerBoard(program);

    await program.parseAsync(['node', 'mpga', 'board', 'add', 'Implement feature X']);

    // Check that a task file was created
    const tasksDir = path.join(tmpDir, 'MPGA', 'board', 'tasks');
    const taskFiles = fs.readdirSync(tasksDir).filter((f) => f.endsWith('.md'));
    expect(taskFiles.length).toBe(1);
    expect(taskFiles[0]).toMatch(/^T001-/);

    // Check the task file content
    const taskContent = fs.readFileSync(path.join(tasksDir, taskFiles[0]), 'utf-8');
    expect(taskContent).toContain('Implement feature X');
    expect(taskContent).toContain('column: "backlog"');
    expect(taskContent).toContain('priority: "medium"');

    // Check board.json was updated
    const boardJson = JSON.parse(
      fs.readFileSync(path.join(tmpDir, 'MPGA', 'board', 'board.json'), 'utf-8'),
    );
    expect(boardJson.next_task_id).toBe(2);
    expect(boardJson.columns.backlog).toContain('T001');

    // Check BOARD.md was regenerated
    expect(fs.existsSync(path.join(tmpDir, 'MPGA', 'board', 'BOARD.md'))).toBe(true);

    // Check console output
    const output = captured();
    expect(output).toContain('T001');
    expect(output).toContain('Implement feature X');
  });

  it('creates a task with custom priority and column', async () => {
    const program = makeProgram();
    registerBoard(program);

    await program.parseAsync([
      'node',
      'mpga',
      'board',
      'add',
      'Critical bugfix',
      '--priority',
      'critical',
      '--column',
      'todo',
    ]);

    const tasksDir = path.join(tmpDir, 'MPGA', 'board', 'tasks');
    const taskFiles = fs.readdirSync(tasksDir).filter((f) => f.endsWith('.md'));
    expect(taskFiles.length).toBe(1);

    const taskContent = fs.readFileSync(path.join(tasksDir, taskFiles[0]), 'utf-8');
    expect(taskContent).toContain('priority: "critical"');
    expect(taskContent).toContain('column: "todo"');

    const boardJson = JSON.parse(
      fs.readFileSync(path.join(tmpDir, 'MPGA', 'board', 'board.json'), 'utf-8'),
    );
    expect(boardJson.columns.todo).toContain('T001');
  });

  it('increments task IDs on successive adds', async () => {
    const program = makeProgram();
    registerBoard(program);

    await program.parseAsync(['node', 'mpga', 'board', 'add', 'First task']);

    const program2 = makeProgram();
    registerBoard(program2);
    await program2.parseAsync(['node', 'mpga', 'board', 'add', 'Second task']);

    const tasksDir = path.join(tmpDir, 'MPGA', 'board', 'tasks');
    const taskFiles = fs
      .readdirSync(tasksDir)
      .filter((f) => f.endsWith('.md'))
      .sort();
    expect(taskFiles.length).toBe(2);
    expect(taskFiles[0]).toMatch(/^T001-/);
    expect(taskFiles[1]).toMatch(/^T002-/);
  });
});

describe('board move', () => {
  it('moves a task between columns', async () => {
    // Seed a task
    const tasksDir = path.join(tmpDir, 'MPGA', 'board', 'tasks');
    fs.writeFileSync(
      path.join(tasksDir, 'T001-my-task.md'),
      makeTaskFile('T001', 'My task', 'backlog'),
    );

    const boardDir = path.join(tmpDir, 'MPGA', 'board');
    fs.writeFileSync(
      path.join(boardDir, 'board.json'),
      makeBoardJson({
        columns: {
          backlog: ['T001'],
          todo: [],
          'in-progress': [],
          testing: [],
          review: [],
          done: [],
        },
        next_task_id: 2,
      }),
    );

    const program = makeProgram();
    registerBoard(program);

    await program.parseAsync(['node', 'mpga', 'board', 'move', 'T001', 'todo']);

    // Verify the task file was updated
    const taskContent = fs.readFileSync(path.join(tasksDir, 'T001-my-task.md'), 'utf-8');
    expect(taskContent).toContain('column: "todo"');

    // Verify board.json was updated
    const boardJson = JSON.parse(fs.readFileSync(path.join(boardDir, 'board.json'), 'utf-8'));
    expect(boardJson.columns.todo).toContain('T001');
    expect(boardJson.columns.backlog).not.toContain('T001');

    // Verify console output
    const output = captured();
    expect(output).toContain('T001');
    expect(output).toContain('todo');
  });

  it('moves a task to in-progress', async () => {
    const tasksDir = path.join(tmpDir, 'MPGA', 'board', 'tasks');
    fs.writeFileSync(
      path.join(tasksDir, 'T001-my-task.md'),
      makeTaskFile('T001', 'My task', 'todo'),
    );

    const boardDir = path.join(tmpDir, 'MPGA', 'board');
    fs.writeFileSync(
      path.join(boardDir, 'board.json'),
      makeBoardJson({
        columns: {
          backlog: [],
          todo: ['T001'],
          'in-progress': [],
          testing: [],
          review: [],
          done: [],
        },
        next_task_id: 2,
      }),
    );

    const program = makeProgram();
    registerBoard(program);

    await program.parseAsync(['node', 'mpga', 'board', 'move', 'T001', 'in-progress']);

    const taskContent = fs.readFileSync(path.join(tasksDir, 'T001-my-task.md'), 'utf-8');
    expect(taskContent).toContain('column: "in-progress"');
  });

  it('regenerates BOARD.md after move', async () => {
    const tasksDir = path.join(tmpDir, 'MPGA', 'board', 'tasks');
    fs.writeFileSync(
      path.join(tasksDir, 'T001-my-task.md'),
      makeTaskFile('T001', 'My task', 'backlog'),
    );

    const boardDir = path.join(tmpDir, 'MPGA', 'board');
    fs.writeFileSync(
      path.join(boardDir, 'board.json'),
      makeBoardJson({
        columns: {
          backlog: ['T001'],
          todo: [],
          'in-progress': [],
          testing: [],
          review: [],
          done: [],
        },
        next_task_id: 2,
      }),
    );

    const program = makeProgram();
    registerBoard(program);

    await program.parseAsync(['node', 'mpga', 'board', 'move', 'T001', 'done']);

    const boardMd = fs.readFileSync(path.join(boardDir, 'BOARD.md'), 'utf-8');
    expect(boardMd).toContain('T001');
    expect(boardMd).toContain('Done');
  });
});

// ===========================================================================
// Evidence command tests
// ===========================================================================

describe('evidence verify', () => {
  it('returns valid drift report JSON with --json flag', async () => {
    const program = makeProgram();
    registerEvidence(program);

    await program.parseAsync(['node', 'mpga', 'evidence', 'verify', '--json']);

    const output = captured();
    // Filter for the JSON output line (the one that starts with '{')
    const jsonLines = logSpy.mock.calls.filter((c) => {
      const s = String(c[0]);
      return s.trimStart().startsWith('{');
    });
    expect(jsonLines.length).toBeGreaterThanOrEqual(1);

    const report = JSON.parse(String(jsonLines[0][0]));
    expect(report).toHaveProperty('timestamp');
    expect(report).toHaveProperty('projectRoot');
    expect(report).toHaveProperty('scopes');
    expect(report).toHaveProperty('overallHealthPct');
    expect(report).toHaveProperty('totalLinks');
    expect(report).toHaveProperty('validLinks');
    expect(report).toHaveProperty('ciPass');
    expect(report).toHaveProperty('ciThreshold');
    expect(Array.isArray(report.scopes)).toBe(true);

    // Our scope file has 2 evidence links
    expect(report.totalLinks).toBe(2);
  });

  it('shows health percentage in non-JSON mode', async () => {
    const program = makeProgram();
    registerEvidence(program);

    await program.parseAsync(['node', 'mpga', 'evidence', 'verify']);

    const output = captured();
    expect(output).toContain('Evidence Verification');
    expect(output).toContain('core');
  });
});

describe('evidence add', () => {
  it('appends evidence link to scope file', async () => {
    const program = makeProgram();
    registerEvidence(program);

    await program.parseAsync([
      'node',
      'mpga',
      'evidence',
      'add',
      'core',
      '[E] src/utils.ts:10-15 :: multiply()',
    ]);

    const scopeContent = fs.readFileSync(path.join(tmpDir, 'MPGA', 'scopes', 'core.md'), 'utf-8');

    // The link should have been inserted before "## Known unknowns"
    expect(scopeContent).toContain('[E] src/utils.ts:10-15 :: multiply()');
    const knownIndex = scopeContent.indexOf('## Known unknowns');
    const linkIndex = scopeContent.indexOf('[E] src/utils.ts:10-15 :: multiply()');
    expect(linkIndex).toBeLessThan(knownIndex);

    const output = captured();
    expect(output).toContain('Added evidence link');
    expect(output).toContain('core');
  });

  it('adds [E] prefix when link does not start with [', async () => {
    const program = makeProgram();
    registerEvidence(program);

    await program.parseAsync(['node', 'mpga', 'evidence', 'add', 'core', 'src/utils.ts:1-3']);

    const scopeContent = fs.readFileSync(path.join(tmpDir, 'MPGA', 'scopes', 'core.md'), 'utf-8');
    expect(scopeContent).toContain('[E] src/utils.ts:1-3');
  });

  it('errors when scope does not exist', async () => {
    const program = makeProgram();
    registerEvidence(program);

    // Commander exitOverride throws on process.exit
    await expect(
      program.parseAsync(['node', 'mpga', 'evidence', 'add', 'nonexistent', '[E] src/foo.ts:1-5']),
    ).rejects.toThrow();

    const output = capturedErr();
    expect(output).toContain('nonexistent');
  });
});

// ===========================================================================
// Drift command tests
// ===========================================================================

describe('drift', () => {
  it('returns valid report with --json flag', async () => {
    const program = makeProgram();
    registerDrift(program);

    await program.parseAsync(['node', 'mpga', 'drift', '--json']);

    const jsonLines = logSpy.mock.calls.filter((c) => {
      const s = String(c[0]);
      return s.trimStart().startsWith('{');
    });
    expect(jsonLines.length).toBeGreaterThanOrEqual(1);

    const report = JSON.parse(String(jsonLines[0][0]));
    expect(report).toHaveProperty('timestamp');
    expect(report).toHaveProperty('projectRoot');
    expect(report).toHaveProperty('scopes');
    expect(report).toHaveProperty('overallHealthPct');
    expect(report).toHaveProperty('totalLinks');
    expect(report).toHaveProperty('validLinks');
    expect(report).toHaveProperty('ciPass');
    expect(report).toHaveProperty('ciThreshold');

    // Our scope file has 2 valid evidence links
    expect(report.totalLinks).toBe(2);
    expect(typeof report.overallHealthPct).toBe('number');
  });

  it('shows minimal output with --quick flag', async () => {
    const program = makeProgram();
    registerDrift(program);

    await program.parseAsync(['node', 'mpga', 'drift', '--quick']);

    // With --quick and no stale links, there should be very little output
    // (only stale warnings are logged in quick mode)
    const output = captured();
    // Should NOT contain the full report header
    expect(output).not.toContain('MPGA Drift Report');
  });

  it('shows full report without --quick or --json', async () => {
    const program = makeProgram();
    registerDrift(program);

    await program.parseAsync(['node', 'mpga', 'drift']);

    const output = captured();
    expect(output).toContain('MPGA Drift Report');
    expect(output).toContain('core');
  });

  it('reports stale links when source file is missing', async () => {
    // Remove the source file so the evidence links become stale
    fs.unlinkSync(path.join(tmpDir, 'src', 'utils.ts'));

    const program = makeProgram();
    registerDrift(program);

    await program.parseAsync(['node', 'mpga', 'drift', '--json']);

    const jsonLines = logSpy.mock.calls.filter((c) => {
      const s = String(c[0]);
      return s.trimStart().startsWith('{');
    });
    const report = JSON.parse(String(jsonLines[0][0]));

    expect(report.totalLinks).toBe(2);
    expect(report.validLinks).toBe(0);
    expect(report.overallHealthPct).toBe(0);
    expect(report.ciPass).toBe(false);

    // The scope should have stale items
    const coreScope = report.scopes.find((s: Record<string, unknown>) => s.scope === 'core');
    expect(coreScope).toBeDefined();
    expect(coreScope.staleLinks).toBe(2);
    expect(coreScope.staleItems.length).toBe(2);
  });

  it('detects stale links with --quick and warns', async () => {
    // Remove the source file to produce stale links
    fs.unlinkSync(path.join(tmpDir, 'src', 'utils.ts'));

    const program = makeProgram();
    registerDrift(program);

    await program.parseAsync(['node', 'mpga', 'drift', '--quick']);

    const output = captured();
    expect(output).toContain('Drift detected');
    expect(output).toContain('stale');
  });

  it('respects --scope filter', async () => {
    // Add another scope file
    fs.writeFileSync(
      path.join(tmpDir, 'MPGA', 'scopes', 'other.md'),
      ['# Scope: other', '', '[E] src/nonexistent.ts:1-5', ''].join('\n'),
    );

    const program = makeProgram();
    registerDrift(program);

    await program.parseAsync(['node', 'mpga', 'drift', '--json', '--scope', 'core']);

    const jsonLines = logSpy.mock.calls.filter((c) => {
      const s = String(c[0]);
      return s.trimStart().startsWith('{');
    });
    const report = JSON.parse(String(jsonLines[0][0]));

    // Only core scope should be in the report
    expect(report.scopes.length).toBe(1);
    expect(report.scopes[0].scope).toBe('core');
  });
});
