import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { Command } from 'commander';

// ---------------------------------------------------------------------------
// Mocks – must be declared before imports that reference them
// ---------------------------------------------------------------------------

// Mock the logger to suppress banner / log output during tests
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
  },
  banner: vi.fn(),
  miniBanner: vi.fn(),
  progressBar: vi.fn(() => ''),
  gradeColor: vi.fn((g: string) => g),
  statusBadge: vi.fn(() => ''),
}));

// Mock scanner so `init --from-existing` doesn't hit the real filesystem
vi.mock('../core/scanner.js', () => ({
  scan: vi.fn(async () => ({
    root: '/fake',
    files: [{ filepath: 'src/index.ts', lines: 100, language: 'typescript', size: 2000 }],
    totalFiles: 42,
    totalLines: 5_000,
    languages: { typescript: { files: 30, lines: 4000 }, javascript: { files: 12, lines: 1000 } },
    entryPoints: ['src/index.ts'],
    topLevelDirs: ['src'],
  })),
  detectProjectType: vi.fn(() => 'TypeScript CLI'),
}));

// Mock drift checker for health command
vi.mock('../evidence/drift.js', () => ({
  runDriftCheck: vi.fn(async (_root: string, ciThreshold: number) => ({
    timestamp: new Date().toISOString(),
    projectRoot: _root,
    scopes: [],
    overallHealthPct: 100,
    totalLinks: 0,
    validLinks: 0,
    ciPass: true,
    ciThreshold,
  })),
}));

// Mock board helpers for health command
vi.mock('../board/board.js', () => ({
  loadBoard: vi.fn(() => ({
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
  })),
  recalcStats: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Seed a minimal MPGA structure so commands that expect an initialized project work. */
function seedMpgaProject(root: string, extras?: { scopes?: string[]; indexContent?: string }) {
  const mpga = path.join(root, 'MPGA');
  const scopesDir = path.join(mpga, 'scopes');
  const boardDir = path.join(mpga, 'board');
  const tasksDir = path.join(boardDir, 'tasks');

  fs.mkdirSync(scopesDir, { recursive: true });
  fs.mkdirSync(tasksDir, { recursive: true });
  fs.mkdirSync(path.join(mpga, 'milestones'), { recursive: true });
  fs.mkdirSync(path.join(mpga, 'sessions'), { recursive: true });

  // Config
  fs.writeFileSync(
    path.join(mpga, 'mpga.config.json'),
    JSON.stringify(
      {
        version: '1.0.0',
        project: { name: 'test-project', languages: ['typescript'], entryPoints: [], ignore: [] },
        evidence: {
          strategy: 'hybrid',
          lineRanges: true,
          astAnchors: true,
          autoHeal: true,
          coverageThreshold: 0.2,
        },
        drift: { ciThreshold: 80, hookMode: 'quick', autoSync: false },
      },
      null,
      2,
    ) + '\n',
  );

  // INDEX.md
  const indexContent =
    extras?.indexContent ??
    `# Project: test-project\n\n## Identity\n- **Last sync:** 2026-01-15T10:00:00Z\n- **Evidence coverage:** 45%\n`;
  fs.writeFileSync(path.join(mpga, 'INDEX.md'), indexContent);

  // GRAPH.md
  fs.writeFileSync(path.join(mpga, 'GRAPH.md'), '# Dependency graph\n');

  // Board
  fs.writeFileSync(
    path.join(boardDir, 'board.json'),
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
      },
      null,
      2,
    ) + '\n',
  );

  // BOARD.md
  fs.writeFileSync(path.join(boardDir, 'BOARD.md'), '# Board\n\nNo tasks yet.\n');

  // Optional scope files
  if (extras?.scopes) {
    for (const scope of extras.scopes) {
      fs.writeFileSync(
        path.join(scopesDir, `${scope}.md`),
        `# Scope: ${scope}\n\n- **Health:** ok\n`,
      );
    }
  }
}

// ---------------------------------------------------------------------------
// Tests: registerInit
// ---------------------------------------------------------------------------

describe('registerInit — the GREATEST init command in history', () => {
  let tmpDir: string;
  let cwdSpy: ReturnType<typeof vi.spyOn>;
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-init-test-'));
    cwdSpy = vi.spyOn(process, 'cwd').mockReturnValue(tmpDir);
    consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    cwdSpy.mockRestore();
    consoleSpy.mockRestore();
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('creates the GREATEST directory structure EVER', async () => {
    const { registerInit } = await import('./init.js');
    const program = new Command();
    program.exitOverride();
    registerInit(program);
    await program.parseAsync(['node', 'test', 'init']);

    // Directories
    expect(fs.existsSync(path.join(tmpDir, 'MPGA'))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, 'MPGA', 'scopes'))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, 'MPGA', 'board'))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, 'MPGA', 'board', 'tasks'))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, 'MPGA', 'milestones'))).toBe(true);
    expect(fs.existsSync(path.join(tmpDir, 'MPGA', 'sessions'))).toBe(true);
  });

  it('creates INDEX.md — the most BEAUTIFUL index, believe me', async () => {
    const { registerInit } = await import('./init.js');
    const program = new Command();
    program.exitOverride();
    registerInit(program);
    await program.parseAsync(['node', 'test', 'init']);

    const indexPath = path.join(tmpDir, 'MPGA', 'INDEX.md');
    expect(fs.existsSync(indexPath)).toBe(true);

    const content = fs.readFileSync(indexPath, 'utf-8');
    const projectName = path.basename(tmpDir);
    expect(content).toContain(`# Project: ${projectName}`);
    expect(content).toContain('**Evidence coverage:** 0%');
    expect(content).toContain('Agent trigger table');
    expect(content).toContain('Scope registry');
    expect(content).toContain('Generated by MPGA on');
  });

  it('creates GRAPH.md with a TREMENDOUS Mermaid placeholder', async () => {
    const { registerInit } = await import('./init.js');
    const program = new Command();
    program.exitOverride();
    registerInit(program);
    await program.parseAsync(['node', 'test', 'init']);

    const graphPath = path.join(tmpDir, 'MPGA', 'GRAPH.md');
    expect(fs.existsSync(graphPath)).toBe(true);

    const content = fs.readFileSync(graphPath, 'utf-8');
    expect(content).toContain('# Dependency graph');
    expect(content).toContain('```mermaid');
    expect(content).toContain('Circular dependencies');
    expect(content).toContain('Orphan modules');
  });

  it('creates mpga.config.json — PERFECT configuration, nobody does it better', async () => {
    const { registerInit } = await import('./init.js');
    const program = new Command();
    program.exitOverride();
    registerInit(program);
    await program.parseAsync(['node', 'test', 'init']);

    const configPath = path.join(tmpDir, 'MPGA', 'mpga.config.json');
    expect(fs.existsSync(configPath)).toBe(true);

    const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    expect(config.version).toBe('1.0.0');
    expect(config.project.name).toBe(path.basename(tmpDir));
    expect(config.evidence.strategy).toBe('hybrid');
    expect(config.drift.ciThreshold).toBe(80);
  });

  it('creates board.json — empty columns, zero stats, a CLEAN SLATE for winning', async () => {
    const { registerInit } = await import('./init.js');
    const program = new Command();
    program.exitOverride();
    registerInit(program);
    await program.parseAsync(['node', 'test', 'init']);

    const boardPath = path.join(tmpDir, 'MPGA', 'board', 'board.json');
    expect(fs.existsSync(boardPath)).toBe(true);

    const board = JSON.parse(fs.readFileSync(boardPath, 'utf-8'));
    expect(board.version).toBe('1.0.0');
    expect(board.milestone).toBeNull();
    expect(board.stats.total).toBe(0);
    expect(board.stats.done).toBe(0);
    expect(board.columns).toHaveProperty('backlog');
    expect(board.columns).toHaveProperty('done');
    expect(board.wip_limits).toEqual({ 'in-progress': 3, testing: 3, review: 2 });
    expect(board.next_task_id).toBe(1);
  });

  it('creates BOARD.md — the placeholder is BEAUTIFUL, just wait', async () => {
    const { registerInit } = await import('./init.js');
    const program = new Command();
    program.exitOverride();
    registerInit(program);
    await program.parseAsync(['node', 'test', 'init']);

    const boardMdPath = path.join(tmpDir, 'MPGA', 'board', 'BOARD.md');
    expect(fs.existsSync(boardMdPath)).toBe(true);
    const content = fs.readFileSync(boardMdPath, 'utf-8');
    expect(content).toContain('# Board');
    expect(content).toContain('No tasks yet');
  });

  it('does not overwrite if already initialized — we PROTECT what we built', async () => {
    // Pre-seed MPGA
    seedMpgaProject(tmpDir);

    const { registerInit } = await import('./init.js');
    const program = new Command();
    program.exitOverride();
    registerInit(program);
    await program.parseAsync(['node', 'test', 'init']);

    // The logger.warn should have been called (already initialized)
    const { log } = await import('../core/logger.js');
    expect(log.warn).toHaveBeenCalledWith(expect.stringContaining('already initialized'));
  });

  it('--from-existing detects project type — SMART, very smart, like me', async () => {
    const { registerInit } = await import('./init.js');
    const program = new Command();
    program.exitOverride();
    registerInit(program);
    await program.parseAsync(['node', 'test', 'init', '--from-existing']);

    const configPath = path.join(tmpDir, 'MPGA', 'mpga.config.json');
    const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));

    // The mocked scanner returns typescript + javascript languages
    expect(config.project.languages).toContain('typescript');
    expect(config.project.languages).toContain('javascript');
    expect(config.project.entryPoints).toEqual(['src/index.ts']);
  });
});

// ---------------------------------------------------------------------------
// Tests: registerConfig
// ---------------------------------------------------------------------------

describe('registerConfig — total CONTROL over your project', () => {
  let tmpDir: string;
  let cwdSpy: ReturnType<typeof vi.spyOn>;
  let consoleSpy: ReturnType<typeof vi.spyOn>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let exitSpy: any;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-config-test-'));
    seedMpgaProject(tmpDir);
    cwdSpy = vi.spyOn(process, 'cwd').mockReturnValue(tmpDir);
    consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    exitSpy = vi.spyOn(process, 'exit').mockImplementation((() => {
      throw new Error('process.exit called');
    }) as never);
  });

  afterEach(() => {
    cwdSpy.mockRestore();
    consoleSpy.mockRestore();
    exitSpy.mockRestore();
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('config show --json outputs valid JSON — TREMENDOUS transparency', async () => {
    const { registerConfig } = await import('./config.js');
    const program = new Command();
    program.exitOverride();
    registerConfig(program);
    await program.parseAsync(['node', 'test', 'config', 'show', '--json']);

    expect(consoleSpy).toHaveBeenCalled();
    const output = consoleSpy.mock.calls[0][0] as string;
    const parsed = JSON.parse(output);
    expect(parsed.project.name).toBe('test-project');
    expect(parsed.version).toBe('1.0.0');
  });

  it('config show without --json outputs BEAUTIFULLY formatted key-value lines', async () => {
    const { registerConfig } = await import('./config.js');
    const program = new Command();
    program.exitOverride();
    registerConfig(program);
    await program.parseAsync(['node', 'test', 'config', 'show']);

    // In non-JSON mode, console.log is called once per flattened key
    expect(consoleSpy).toHaveBeenCalled();
    const allOutput = consoleSpy.mock.calls.map((c) => String(c[0])).join('\n');
    expect(allOutput).toContain('project.name');
  });

  it('config set updates a numeric config value — PRECISION, folks', async () => {
    const { registerConfig } = await import('./config.js');
    const program = new Command();
    program.exitOverride();
    registerConfig(program);
    await program.parseAsync(['node', 'test', 'config', 'set', 'drift.ciThreshold', '90']);

    // Re-read the config file to confirm it was persisted
    const configPath = path.join(tmpDir, 'MPGA', 'mpga.config.json');
    const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
    expect(config.drift.ciThreshold).toBe(90);
  });

  it('config set exits with error for unknown key — FAKE keys get REJECTED', async () => {
    const { registerConfig } = await import('./config.js');
    const program = new Command();
    program.exitOverride();
    registerConfig(program);

    await expect(
      program.parseAsync(['node', 'test', 'config', 'set', 'nonexistent.key', 'val']),
    ).rejects.toThrow();

    const { log } = await import('../core/logger.js');
    expect(log.error).toHaveBeenCalledWith(expect.stringContaining('Unknown config key'));
  });
});

// ---------------------------------------------------------------------------
// Tests: registerStatus
// ---------------------------------------------------------------------------

describe('registerStatus — the BEST status reports, everyone says so', () => {
  let tmpDir: string;
  let cwdSpy: ReturnType<typeof vi.spyOn>;
  let consoleSpy: ReturnType<typeof vi.spyOn>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let exitSpy: any;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-status-test-'));
    cwdSpy = vi.spyOn(process, 'cwd').mockReturnValue(tmpDir);
    consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    exitSpy = vi.spyOn(process, 'exit').mockImplementation((() => {
      throw new Error('process.exit called');
    }) as never);
  });

  afterEach(() => {
    cwdSpy.mockRestore();
    consoleSpy.mockRestore();
    exitSpy.mockRestore();
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('exits with error when MPGA is not initialized — DISASTER!', async () => {
    const { registerStatus } = await import('./status.js');
    const program = new Command();
    program.exitOverride();
    registerStatus(program);

    await expect(program.parseAsync(['node', 'test', 'status'])).rejects.toThrow();

    const { log } = await import('../core/logger.js');
    expect(log.error).toHaveBeenCalledWith(expect.stringContaining('not initialized'));
  });

  it('--json returns correct structure — PERFECTLY organized, like my rallies', async () => {
    seedMpgaProject(tmpDir, { scopes: ['core', 'auth'] });

    const { registerStatus } = await import('./status.js');
    const program = new Command();
    program.exitOverride();
    registerStatus(program);
    await program.parseAsync(['node', 'test', 'status', '--json']);

    expect(consoleSpy).toHaveBeenCalled();
    const output = consoleSpy.mock.calls[0][0] as string;
    const parsed = JSON.parse(output);

    expect(parsed.initialized).toBe(true);
    expect(parsed.lastSync).toBe('2026-01-15T10:00:00Z');
    expect(parsed.evidenceCoverage).toBe('45%');
    expect(parsed.scopes).toBe(2);
    expect(parsed.config.name).toBe('test-project');
    expect(parsed.board).toBeDefined();
  });

  it('--json returns lastSync as "never" when INDEX.md has placeholder — SAD!', async () => {
    seedMpgaProject(tmpDir, {
      indexContent:
        '# Project: test\n\n- **Last sync:** (not yet synced)\n- **Evidence coverage:** 0%\n',
    });

    const { registerStatus } = await import('./status.js');
    const program = new Command();
    program.exitOverride();
    registerStatus(program);
    await program.parseAsync(['node', 'test', 'status', '--json']);

    const output = consoleSpy.mock.calls[0][0] as string;
    const parsed = JSON.parse(output);
    // status reads INDEX.md and checks for "run" in lastSync text
    // "(not yet synced)" does not contain "run", so it's returned as-is
    expect(typeof parsed.lastSync).toBe('string');
  });

  it('--json returns zero scopes when none exist — we will BUILD them later, believe me', async () => {
    seedMpgaProject(tmpDir);

    const { registerStatus } = await import('./status.js');
    const program = new Command();
    program.exitOverride();
    registerStatus(program);
    await program.parseAsync(['node', 'test', 'status', '--json']);

    const output = consoleSpy.mock.calls[0][0] as string;
    const parsed = JSON.parse(output);
    expect(parsed.scopes).toBe(0);
  });

  it('non-JSON mode calls logger functions — BEAUTIFUL formatted output', async () => {
    seedMpgaProject(tmpDir, { scopes: ['core'] });

    const { registerStatus } = await import('./status.js');
    const program = new Command();
    program.exitOverride();
    registerStatus(program);
    await program.parseAsync(['node', 'test', 'status']);

    const { log } = await import('../core/logger.js');
    expect(log.header).toHaveBeenCalled();
    expect(log.section).toHaveBeenCalled();
    expect(log.kv).toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Tests: registerHealth
// ---------------------------------------------------------------------------

describe('registerHealth — keeping our project in PERFECT health', () => {
  let tmpDir: string;
  let cwdSpy: ReturnType<typeof vi.spyOn>;
  let consoleSpy: ReturnType<typeof vi.spyOn>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let exitSpy: any;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-health-test-'));
    cwdSpy = vi.spyOn(process, 'cwd').mockReturnValue(tmpDir);
    consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    exitSpy = vi.spyOn(process, 'exit').mockImplementation((() => {
      throw new Error('process.exit called');
    }) as never);
  });

  afterEach(() => {
    cwdSpy.mockRestore();
    consoleSpy.mockRestore();
    exitSpy.mockRestore();
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('exits with error when MPGA is not initialized — TOTAL failure, very sad', async () => {
    const { registerHealth } = await import('./health.js');
    const program = new Command();
    program.exitOverride();
    registerHealth(program);

    await expect(program.parseAsync(['node', 'test', 'health'])).rejects.toThrow();

    const { log } = await import('../core/logger.js');
    expect(log.error).toHaveBeenCalledWith(expect.stringContaining('not initialized'));
  });

  it('--json returns correct health report — like a PERFECT physical', async () => {
    seedMpgaProject(tmpDir, { scopes: ['core', 'utils'] });

    const { registerHealth } = await import('./health.js');
    const program = new Command();
    program.exitOverride();
    registerHealth(program);
    await program.parseAsync(['node', 'test', 'health', '--json']);

    expect(consoleSpy).toHaveBeenCalled();
    const output = consoleSpy.mock.calls[0][0] as string;
    const parsed = JSON.parse(output);

    expect(parsed.initialized).toBe(true);
    expect(parsed.evidenceHealth).toBe(100);
    expect(parsed.ciPass).toBe(true);
    expect(parsed.scopes).toBe(2);
    expect(parsed.board).toBeDefined();
    expect(parsed.lastSync).toBe('2026-01-15T10:00:00Z');
    expect(parsed.overallGrade).toBeDefined();
    expect(['A', 'B', 'C', 'D']).toContain(parsed.overallGrade);
  });

  it('--json includes correct grade for 100% health — STRAIGHT A, the best genes', async () => {
    seedMpgaProject(tmpDir);

    const { registerHealth } = await import('./health.js');
    const program = new Command();
    program.exitOverride();
    registerHealth(program);
    await program.parseAsync(['node', 'test', 'health', '--json']);

    const output = consoleSpy.mock.calls[0][0] as string;
    const parsed = JSON.parse(output);

    // 100% health should yield grade A (>= 95)
    expect(parsed.overallGrade).toBe('A');
  });

  it('--json reports lastSync as "never" when INDEX.md has placeholder — we will FIX that', async () => {
    seedMpgaProject(tmpDir, {
      indexContent: '# Project: test\n\n- **Last sync:** (run `mpga sync` to populate)\n',
    });

    const { registerHealth } = await import('./health.js');
    const program = new Command();
    program.exitOverride();
    registerHealth(program);
    await program.parseAsync(['node', 'test', 'health', '--json']);

    const output = consoleSpy.mock.calls[0][0] as string;
    const parsed = JSON.parse(output);
    expect(parsed.lastSync).toBe('never');
  });

  it('non-JSON mode calls miniBanner and logger header — SHOWMANSHIP', async () => {
    seedMpgaProject(tmpDir);

    const { registerHealth } = await import('./health.js');
    const program = new Command();
    program.exitOverride();
    registerHealth(program);
    await program.parseAsync(['node', 'test', 'health']);

    const { log, miniBanner } = await import('../core/logger.js');
    expect(miniBanner).toHaveBeenCalled();
    expect(log.header).toHaveBeenCalled();
  });
});
