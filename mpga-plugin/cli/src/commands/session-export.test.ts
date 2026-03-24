import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { Command } from 'commander';
import { registerSession } from './session.js';
import { registerExport } from './export.js';

// Mock findProjectRoot and loadConfig so commands operate on our tmpDir
vi.mock('../core/config.js', () => ({
  findProjectRoot: vi.fn(),
  loadConfig: vi.fn(),
}));

import { findProjectRoot, loadConfig } from '../core/config.js';

const mockedFindProjectRoot = vi.mocked(findProjectRoot);
const mockedLoadConfig = vi.mocked(loadConfig);

/** Create a Commander program with exitOverride so parseAsync throws instead of calling process.exit */
function createProgram(): Command {
  const program = new Command();
  program.exitOverride();
  return program;
}

/** Minimal board.json payload */
function minimalBoard(overrides: Record<string, unknown> = {}): string {
  return JSON.stringify(
    {
      version: '1.0.0',
      milestone: 'M001-alpha',
      updated: new Date().toISOString(),
      columns: {
        backlog: [],
        todo: ['T002'],
        'in-progress': ['T001'],
        testing: [],
        review: [],
        done: [],
      },
      stats: {
        total: 2,
        done: 0,
        in_flight: 1,
        blocked: 0,
        progress_pct: 0,
        evidence_produced: 0,
        evidence_expected: 0,
      },
      wip_limits: { 'in-progress': 3, testing: 3, review: 2 },
      next_task_id: 3,
      ...overrides,
    },
    null,
    2,
  );
}

/** Gray-matter compatible task frontmatter */
function taskFrontmatter(
  id: string,
  title: string,
  column: string,
  extra: Record<string, unknown> = {},
): string {
  return `---
id: ${JSON.stringify(id)}
title: ${JSON.stringify(title)}
column: ${JSON.stringify(column)}
status: "active"
priority: "medium"
milestone: "M001-alpha"
created: "2026-01-01T00:00:00.000Z"
updated: "2026-01-01T00:00:00.000Z"
assigned: ${extra.assigned ? JSON.stringify(extra.assigned) : 'null'}
depends_on: []
blocks: []
scopes: []
tdd_stage: ${extra.tdd_stage ? JSON.stringify(extra.tdd_stage) : 'null'}
evidence_expected: []
evidence_produced: []
tags: []
time_estimate: "15min"
---

# ${id}: ${title}
`;
}

// ─── Session command tests ───────────────────────────────────────────────────

describe('session handoff', () => {
  let tmpDir: string;
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-session-'));
    mockedFindProjectRoot.mockReturnValue(tmpDir);

    // Set up board structure
    const boardDir = path.join(tmpDir, 'MPGA', 'board');
    const tasksDir = path.join(boardDir, 'tasks');
    const sessionsDir = path.join(tmpDir, 'MPGA', 'sessions');
    fs.mkdirSync(tasksDir, { recursive: true });
    fs.mkdirSync(sessionsDir, { recursive: true });

    // Write board.json
    fs.writeFileSync(path.join(boardDir, 'board.json'), minimalBoard());

    // Write task files
    fs.writeFileSync(
      path.join(tasksDir, 'T001-implement-parser.md'),
      taskFrontmatter('T001', 'Implement parser', 'in-progress', {
        tdd_stage: 'green',
        assigned: 'agent',
      }),
    );
    fs.writeFileSync(
      path.join(tasksDir, 'T002-add-tests.md'),
      taskFrontmatter('T002', 'Add tests', 'todo'),
    );

    consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
    vi.restoreAllMocks();
  });

  it('creates a handoff file in MPGA/sessions/', async () => {
    const program = createProgram();
    registerSession(program);
    await program.parseAsync(['session', 'handoff'], { from: 'user' });

    const sessionsDir = path.join(tmpDir, 'MPGA', 'sessions');
    const files = fs.readdirSync(sessionsDir).filter((f) => f.endsWith('-handoff.md'));
    expect(files.length).toBe(1);
  });

  it('handoff file contains correct board state', async () => {
    const program = createProgram();
    registerSession(program);
    await program.parseAsync(['session', 'handoff', '--accomplished', 'Fixed the parser'], {
      from: 'user',
    });

    const sessionsDir = path.join(tmpDir, 'MPGA', 'sessions');
    const files = fs.readdirSync(sessionsDir).filter((f) => f.endsWith('-handoff.md'));
    const content = fs.readFileSync(path.join(sessionsDir, files[0]), 'utf-8');

    expect(content).toContain('# Session Handoff');
    expect(content).toContain('Fixed the parser');
    expect(content).toContain('M001-alpha');
    expect(content).toContain('0/2 tasks done');
  });

  it('handoff file includes in-progress tasks', async () => {
    const program = createProgram();
    registerSession(program);
    await program.parseAsync(['session', 'handoff'], { from: 'user' });

    const sessionsDir = path.join(tmpDir, 'MPGA', 'sessions');
    const files = fs.readdirSync(sessionsDir).filter((f) => f.endsWith('-handoff.md'));
    const content = fs.readFileSync(path.join(sessionsDir, files[0]), 'utf-8');

    expect(content).toContain('T001');
    expect(content).toContain('Implement parser');
    expect(content).toContain('in-progress');
    expect(content).toContain('1 task(s)');
  });
});

describe('session log', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-session-log-'));
    mockedFindProjectRoot.mockReturnValue(tmpDir);
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
    vi.restoreAllMocks();
  });

  it('creates session-log.md with first entry', async () => {
    const program = createProgram();
    registerSession(program);
    await program.parseAsync(['session', 'log', 'Decided to use factory pattern'], {
      from: 'user',
    });

    const logPath = path.join(tmpDir, 'MPGA', 'sessions', 'session-log.md');
    expect(fs.existsSync(logPath)).toBe(true);

    const content = fs.readFileSync(logPath, 'utf-8');
    expect(content).toContain('# Session Log');
    expect(content).toContain('Decided to use factory pattern');
  });

  it('appends to existing session-log.md', async () => {
    // Create the sessions dir and an initial log file
    const sessionsDir = path.join(tmpDir, 'MPGA', 'sessions');
    fs.mkdirSync(sessionsDir, { recursive: true });
    fs.writeFileSync(
      path.join(sessionsDir, 'session-log.md'),
      '# Session Log\n\n- 2026-01-01T00:00:00.000Z: First entry\n',
    );

    const program = createProgram();
    registerSession(program);
    await program.parseAsync(['session', 'log', 'Second entry here'], { from: 'user' });

    const content = fs.readFileSync(path.join(sessionsDir, 'session-log.md'), 'utf-8');
    expect(content).toContain('First entry');
    expect(content).toContain('Second entry here');

    // The file should have exactly two timestamped entries
    const entryLines = content.split('\n').filter((line) => /^- \d{4}-/.test(line));
    expect(entryLines.length).toBe(2);
  });
});

describe('session resume', () => {
  let tmpDir: string;
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-session-resume-'));
    mockedFindProjectRoot.mockReturnValue(tmpDir);
    consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
    vi.restoreAllMocks();
  });

  it('shows most recent handoff content', async () => {
    const sessionsDir = path.join(tmpDir, 'MPGA', 'sessions');
    fs.mkdirSync(sessionsDir, { recursive: true });

    // Write two handoff files with different dates
    fs.writeFileSync(
      path.join(sessionsDir, '2026-01-01-10-00-00-handoff.md'),
      '# Session Handoff — 2026-01-01\nOlder handoff content\n',
    );
    fs.writeFileSync(
      path.join(sessionsDir, '2026-01-02-14-30-00-handoff.md'),
      '# Session Handoff — 2026-01-02\nLatest handoff content\n',
    );

    const program = createProgram();
    registerSession(program);
    await program.parseAsync(['session', 'resume'], { from: 'user' });

    // console.log should have been called with the latest handoff content
    const allOutput = consoleSpy.mock.calls.map((c) => c.join(' ')).join('\n');
    expect(allOutput).toContain('Latest handoff content');
    expect(allOutput).toContain('2026-01-02');
  });

  it('shows info message when no handoffs exist', async () => {
    // No sessions directory at all
    const program = createProgram();
    registerSession(program);
    await program.parseAsync(['session', 'resume'], { from: 'user' });

    const allOutput = consoleSpy.mock.calls.map((c) => c.join(' ')).join('\n');
    expect(allOutput).toContain('No session handoffs found');
  });
});

describe('session budget', () => {
  let tmpDir: string;
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-session-budget-'));
    mockedFindProjectRoot.mockReturnValue(tmpDir);
    consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
    vi.restoreAllMocks();
  });

  it('reports correct line counts for INDEX.md and scope docs', async () => {
    const mpgaDir = path.join(tmpDir, 'MPGA');
    const scopesDir = path.join(mpgaDir, 'scopes');
    fs.mkdirSync(scopesDir, { recursive: true });

    // Write INDEX.md with 10 lines
    fs.writeFileSync(path.join(mpgaDir, 'INDEX.md'), Array(10).fill('line').join('\n'));

    // Write two scope docs: 5 lines and 8 lines
    fs.writeFileSync(path.join(scopesDir, 'core.md'), Array(5).fill('scope-line').join('\n'));
    fs.writeFileSync(path.join(scopesDir, 'board.md'), Array(8).fill('scope-line').join('\n'));

    const program = createProgram();
    registerSession(program);
    await program.parseAsync(['session', 'budget'], { from: 'user' });

    const allOutput = consoleSpy.mock.calls.map((c) => c.join(' ')).join('\n');

    // INDEX.md should show 10 lines
    expect(allOutput).toContain('INDEX.md');
    expect(allOutput).toContain('10');
    expect(allOutput).toContain('Tier 1 (hot)');

    // Scope docs should appear with Tier 2
    expect(allOutput).toContain('scopes/core.md');
    expect(allOutput).toContain('scopes/board.md');
    expect(allOutput).toContain('Tier 2 (warm)');

    // Total should be 10 + 5 + 8 = 23 lines
    expect(allOutput).toContain('23 lines');
  });
});

// ─── Export command tests ────────────────────────────────────────────────────

describe('export --claude', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-export-'));
    mockedFindProjectRoot.mockReturnValue(tmpDir);
    mockedLoadConfig.mockReturnValue({
      version: '1.0.0',
      project: {
        name: 'test-project',
        languages: ['typescript'],
        entryPoints: ['src/index.ts'],
        ignore: ['node_modules'],
      },
      evidence: {
        strategy: 'hybrid',
        lineRanges: true,
        astAnchors: true,
        autoHeal: false,
        coverageThreshold: 60,
      },
      drift: {
        ciThreshold: 15,
        hookMode: 'quick',
        autoSync: false,
      },
      tiers: {
        hotMaxLines: 300,
        warmMaxLinesPerScope: 200,
        coldAutoArchiveAfterDays: 30,
      },
      milestone: {
        branchStrategy: 'worktree',
        autoAdvance: false,
        squashOnComplete: false,
      },
      agents: {
        tddCycle: true,
        explorationCycle: true,
        researchBeforePlan: true,
      },
      scopes: {
        scopeDepth: 'auto' as const,
        maxFilesPerScope: 30,
      },
      board: {
        columns: ['backlog', 'todo', 'in-progress', 'testing', 'review', 'done'],
        customColumns: [],
        wipLimits: { 'in-progress': 3, testing: 3, review: 2 },
        autoTransitions: true,
        archiveOnMilestoneComplete: true,
        taskIdPrefix: 'T',
        defaultPriority: 'medium' as const,
        defaultTimeEstimate: '5min',
        showTddStage: true,
        showEvidenceStatus: true,
        githubSync: false,
      },
    } as ReturnType<typeof loadConfig>);

    // Minimal MPGA directory with INDEX.md
    const mpgaDir = path.join(tmpDir, 'MPGA');
    fs.mkdirSync(mpgaDir, { recursive: true });
    fs.writeFileSync(
      path.join(mpgaDir, 'INDEX.md'),
      '# INDEX\n\n## Active milestone\nM001-alpha\n',
    );

    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
    vi.restoreAllMocks();
  });

  it('creates CLAUDE.md at project root', async () => {
    const program = createProgram();
    registerExport(program);
    await program.parseAsync(['export', '--claude'], { from: 'user' });

    const claudeMdPath = path.join(tmpDir, 'CLAUDE.md');
    expect(fs.existsSync(claudeMdPath)).toBe(true);

    const content = fs.readFileSync(claudeMdPath, 'utf-8');
    expect(content).toContain('MPGA-Managed Project Context');
    expect(content).toContain('M001-alpha');
  });

  it('creates .claude/skills/ directory structure', async () => {
    const program = createProgram();
    registerExport(program);
    await program.parseAsync(['export', '--claude'], { from: 'user' });

    const skillsDir = path.join(tmpDir, '.claude', 'skills');
    expect(fs.existsSync(skillsDir)).toBe(true);

    // Each skill should get its own subdirectory
    const skillDirs = fs.readdirSync(skillsDir);
    expect(skillDirs.length).toBeGreaterThan(0);

    // Skills should be prefixed with mpga-
    for (const dir of skillDirs) {
      expect(dir).toMatch(/^mpga-/);
    }
  });
});

describe('AGENTS metadata validity', () => {
  it('every agent has required fields', async () => {
    // Dynamically import the source to access the AGENTS array
    // Since AGENTS is not exported, we validate through the export command behavior.
    // Instead, verify the well-known agent slugs that the session/export commands rely on.
    const expectedSlugs = [
      'red-dev',
      'green-dev',
      'blue-dev',
      'scout',
      'architect',
      'auditor',
      'researcher',
      'reviewer',
      'verifier',
    ];

    // Read the agents source file and verify each slug appears in the AGENTS array
    const exportSource = fs.readFileSync(path.join(__dirname, 'export', 'agents.ts'), 'utf-8');

    for (const slug of expectedSlugs) {
      expect(exportSource).toContain(`slug: '${slug}'`);
    }

    // Verify each agent has the required metadata fields
    const requiredFields = [
      'slug',
      'name',
      'description',
      'model',
      'readonly',
      'isBackground',
      'sandboxMode',
    ];
    for (const field of requiredFields) {
      // Each field should appear at least once per agent (9 agents)
      const matches = exportSource.match(new RegExp(`${field}:`, 'g'));
      expect(matches).not.toBeNull();
      expect(matches!.length).toBeGreaterThanOrEqual(expectedSlugs.length);
    }
  });
});
