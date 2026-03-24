import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';

// ---------------------------------------------------------------------------
// Mocks – must be declared before imports that reference them
// ---------------------------------------------------------------------------

vi.mock('../../core/logger.js', () => ({
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

vi.mock('./agents.js', () => ({
  SKILL_NAMES: ['sync-project', 'brainstorm', 'plan', 'develop', 'drift-check'],
  copySkillsTo: vi.fn(),
}));

import { exportAntigravity } from './antigravity.js';
import { log } from '../../core/logger.js';
import { SKILL_NAMES, copySkillsTo } from './agents.js';

const mockedCopySkillsTo = vi.mocked(copySkillsTo);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function defaultIndexContent(milestone?: string): string {
  return `# Project: test-project

## Identity
- **Last sync:** 2026-01-15T10:00:00Z
- **Evidence coverage:** 45%

## Active milestone
${milestone ?? 'M001-alpha'}

## Scope registry
| Scope | File count |
`;
}

// ---------------------------------------------------------------------------
// Tests: project-level (non-global) export
// ---------------------------------------------------------------------------

describe('exportAntigravity (project-level)', () => {
  let tmpDir: string;
  let mpgaDir: string;
  const pluginRoot = '/fake/plugin';

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-ag-test-'));
    mpgaDir = path.join(tmpDir, 'MPGA');
    fs.mkdirSync(mpgaDir, { recursive: true });
    vi.clearAllMocks();
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
    vi.restoreAllMocks();
  });

  it('creates GEMINI.md at project root', () => {
    exportAntigravity(
      tmpDir,
      mpgaDir,
      defaultIndexContent(),
      'test-project',
      pluginRoot,
      false,
      {},
    );

    const geminiPath = path.join(tmpDir, 'GEMINI.md');
    expect(fs.existsSync(geminiPath)).toBe(true);

    const content = fs.readFileSync(geminiPath, 'utf-8');
    expect(content).toContain('MPGA-Managed Project Context');
    expect(content).toContain('node ./.mpga-runtime/cli/dist/index.js sync');
    expect(content).toContain('MPGA/INDEX.md');
  });

  it('GEMINI.md includes the active milestone from INDEX content', () => {
    exportAntigravity(
      tmpDir,
      mpgaDir,
      defaultIndexContent('M002-beta'),
      'test-project',
      pluginRoot,
      false,
      {},
    );

    const content = fs.readFileSync(path.join(tmpDir, 'GEMINI.md'), 'utf-8');
    expect(content).toContain('M002-beta');
  });

  it('GEMINI.md falls back to (none) when no milestone section exists', () => {
    const indexWithoutMilestone = '# Project: test-project\n\n## Identity\n- stuff\n';
    exportAntigravity(
      tmpDir,
      mpgaDir,
      indexWithoutMilestone,
      'test-project',
      pluginRoot,
      false,
      {},
    );

    const content = fs.readFileSync(path.join(tmpDir, 'GEMINI.md'), 'utf-8');
    expect(content).toContain('(none)');
  });

  it('calls copySkillsTo for .agent/skills/', () => {
    exportAntigravity(
      tmpDir,
      mpgaDir,
      defaultIndexContent(),
      'test-project',
      pluginRoot,
      false,
      {},
    );

    expect(mockedCopySkillsTo).toHaveBeenCalledWith(
      path.join(tmpDir, '.agent', 'skills'),
      pluginRoot,
      'antigravity',
      'node ./.mpga-runtime/cli/dist/index.js',
    );
  });

  it('creates .antigravity/rules/ with 3 rule files', () => {
    exportAntigravity(
      tmpDir,
      mpgaDir,
      defaultIndexContent(),
      'test-project',
      pluginRoot,
      false,
      {},
    );

    const rulesDir = path.join(tmpDir, '.antigravity', 'rules');
    expect(fs.existsSync(rulesDir)).toBe(true);

    const files = fs.readdirSync(rulesDir);
    expect(files).toContain('mpga-context.md');
    expect(files).toContain('mpga-evidence.md');
    expect(files).toContain('mpga-tdd.md');
    expect(files.length).toBe(3);
  });

  it('mpga-context.md contains milestone and evidence protocol', () => {
    exportAntigravity(
      tmpDir,
      mpgaDir,
      defaultIndexContent(),
      'test-project',
      pluginRoot,
      false,
      {},
    );

    const content = fs.readFileSync(
      path.join(tmpDir, '.antigravity', 'rules', 'mpga-context.md'),
      'utf-8',
    );
    expect(content).toContain('MPGA Project Context');
    expect(content).toContain('M001-alpha');
    expect(content).toContain('Evidence protocol');
    expect(content).toContain('[E]');
    expect(content).toContain('[Unknown]');
  });

  it('mpga-evidence.md contains evidence link format', () => {
    exportAntigravity(
      tmpDir,
      mpgaDir,
      defaultIndexContent(),
      'test-project',
      pluginRoot,
      false,
      {},
    );

    const content = fs.readFileSync(
      path.join(tmpDir, '.antigravity', 'rules', 'mpga-evidence.md'),
      'utf-8',
    );
    expect(content).toContain('MPGA Evidence Protocol');
    expect(content).toContain('[E] filepath:startLine-endLine :: symbolName()');
    expect(content).toContain('[Stale:YYYY-MM-DD]');
    expect(content).toContain('node ./.mpga-runtime/cli/dist/index.js evidence heal');
  });

  it('mpga-tdd.md contains TDD protocol steps', () => {
    exportAntigravity(
      tmpDir,
      mpgaDir,
      defaultIndexContent(),
      'test-project',
      pluginRoot,
      false,
      {},
    );

    const content = fs.readFileSync(
      path.join(tmpDir, '.antigravity', 'rules', 'mpga-tdd.md'),
      'utf-8',
    );
    expect(content).toContain('RED');
    expect(content).toContain('GREEN');
    expect(content).toContain('BLUE');
    expect(content).toContain('NEVER write implementation code before a test');
    expect(content.indexOf('1. RED')).toBeLessThan(content.indexOf('2. GREEN'));
    expect(content.indexOf('2. GREEN')).toBeLessThan(content.indexOf('3. BLUE'));
  });

  it('creates .agents/workflows/ with 3 workflow files', () => {
    exportAntigravity(
      tmpDir,
      mpgaDir,
      defaultIndexContent(),
      'test-project',
      pluginRoot,
      false,
      {},
    );

    const workflowsDir = path.join(tmpDir, '.agents', 'workflows');
    expect(fs.existsSync(workflowsDir)).toBe(true);

    const files = fs.readdirSync(workflowsDir);
    expect(files).toContain('mpga-plan.md');
    expect(files).toContain('mpga-develop.md');
    expect(files).toContain('mpga-review.md');
    expect(files.length).toBe(3);
  });

  it('workflow files contain expected headings', () => {
    exportAntigravity(
      tmpDir,
      mpgaDir,
      defaultIndexContent(),
      'test-project',
      pluginRoot,
      false,
      {},
    );

    const workflowsDir = path.join(tmpDir, '.agents', 'workflows');

    const plan = fs.readFileSync(path.join(workflowsDir, 'mpga-plan.md'), 'utf-8');
    expect(plan).toContain('MPGA Plan Workflow');
    expect(plan).toContain('milestone');

    const develop = fs.readFileSync(path.join(workflowsDir, 'mpga-develop.md'), 'utf-8');
    expect(develop).toContain('MPGA Develop Workflow');
    expect(develop).toContain('failing test');

    const review = fs.readFileSync(path.join(workflowsDir, 'mpga-review.md'), 'utf-8');
    expect(review).toContain('MPGA Review Workflow');
    expect(review).toContain('Spec compliance');
    expect(review).toContain('node ./.mpga-runtime/cli/dist/index.js evidence verify');
    expect(review).not.toContain('npx mpga evidence verify');
  });

  it('calls log.success for each generated artifact', () => {
    exportAntigravity(
      tmpDir,
      mpgaDir,
      defaultIndexContent(),
      'test-project',
      pluginRoot,
      false,
      {},
    );

    // Should log: GEMINI.md, .agent/skills/, .antigravity/rules/, .agents/workflows/
    expect(log.success).toHaveBeenCalledTimes(4);
    expect(log.success).toHaveBeenCalledWith('Generated GEMINI.md');
    expect(log.success).toHaveBeenCalledWith(expect.stringContaining('.agent/skills/'));
    expect(log.success).toHaveBeenCalledWith(expect.stringContaining('.antigravity/rules/'));
    expect(log.success).toHaveBeenCalledWith(expect.stringContaining('.agents/workflows/'));
  });

  // ─── Knowledge seeding ──────────────────────────────────────────────────────

  it('does not seed knowledge items when opts.knowledge is false', () => {
    const scopesDir = path.join(mpgaDir, 'scopes');
    fs.mkdirSync(scopesDir, { recursive: true });
    fs.writeFileSync(
      path.join(scopesDir, 'core.md'),
      '# Scope: core\n[E] src/core.ts:1-10 :: main()\n',
    );

    exportAntigravity(
      tmpDir,
      mpgaDir,
      defaultIndexContent(),
      'test-project',
      pluginRoot,
      false,
      {},
    );

    const kiDir = path.join(tmpDir, '.antigravity', 'knowledge');
    // knowledge dir should NOT exist when knowledge opt not set
    expect(fs.existsSync(path.join(kiDir, 'mpga-core.md'))).toBe(false);
  });

  it('seeds knowledge items from scopes when opts.knowledge is true', () => {
    const scopesDir = path.join(mpgaDir, 'scopes');
    fs.mkdirSync(scopesDir, { recursive: true });
    fs.writeFileSync(
      path.join(scopesDir, 'core.md'),
      '# Scope: core\n[E] src/core.ts:1-10 :: main()\n[E] src/core.ts:20-30 :: init()\n',
    );
    fs.writeFileSync(path.join(scopesDir, 'utils.md'), '# Scope: utils\n');

    exportAntigravity(tmpDir, mpgaDir, defaultIndexContent(), 'test-project', pluginRoot, false, {
      knowledge: true,
    });

    const kiDir = path.join(tmpDir, '.antigravity', 'knowledge');
    expect(fs.existsSync(kiDir)).toBe(true);

    // Should produce one knowledge file per scope
    const kiFiles = fs.readdirSync(kiDir);
    expect(kiFiles).toContain('mpga-core.md');
    expect(kiFiles).toContain('mpga-utils.md');

    // core scope has evidence links
    const coreContent = fs.readFileSync(path.join(kiDir, 'mpga-core.md'), 'utf-8');
    expect(coreContent).toContain('Knowledge: core module');
    expect(coreContent).toContain('[E] src/core.ts:1-10 :: main()');
    expect(coreContent).toContain('[E] src/core.ts:20-30 :: init()');

    // utils scope has no evidence links
    const utilsContent = fs.readFileSync(path.join(kiDir, 'mpga-utils.md'), 'utf-8');
    expect(utilsContent).toContain('Knowledge: utils module');
    expect(utilsContent).toContain('run `mpga sync` to populate');
  });

  it('does not seed knowledge when scopes directory is missing', () => {
    // mpgaDir exists but no scopes/ subdirectory
    exportAntigravity(tmpDir, mpgaDir, defaultIndexContent(), 'test-project', pluginRoot, false, {
      knowledge: true,
    });

    const kiDir = path.join(tmpDir, '.antigravity', 'knowledge');
    expect(fs.existsSync(kiDir)).toBe(false);
  });

  it('logs success for knowledge seeding', () => {
    const scopesDir = path.join(mpgaDir, 'scopes');
    fs.mkdirSync(scopesDir, { recursive: true });
    fs.writeFileSync(path.join(scopesDir, 'core.md'), '# Scope: core\n');

    exportAntigravity(tmpDir, mpgaDir, defaultIndexContent(), 'test-project', pluginRoot, false, {
      knowledge: true,
    });

    expect(log.success).toHaveBeenCalledWith(expect.stringContaining('Knowledge Items'));
  });
});

// ---------------------------------------------------------------------------
// Tests: global export
// ---------------------------------------------------------------------------

describe('exportAntigravity (global)', () => {
  let tmpDir: string;
  let originalHome: string | undefined;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-ag-global-'));
    originalHome = process.env.HOME;
    process.env.HOME = tmpDir;
    vi.clearAllMocks();
  });

  afterEach(() => {
    process.env.HOME = originalHome;
    fs.rmSync(tmpDir, { recursive: true, force: true });
    vi.restoreAllMocks();
  });

  it('calls copySkillsTo for ~/.gemini/antigravity/skills/', () => {
    exportAntigravity('/unused', '/unused/MPGA', '', 'test', '/fake/plugin', true, {});

    expect(mockedCopySkillsTo).toHaveBeenCalledWith(
      path.join(tmpDir, '.gemini', 'antigravity', 'skills'),
      '/fake/plugin',
      'antigravity',
      path.join(tmpDir, '.gemini', '.mpga-runtime', 'cli', 'dist', 'index.js').replace(/\\/g, '/'),
    );
  });

  it('creates ~/.antigravity/rules/mpga-global.md', () => {
    exportAntigravity('/unused', '/unused/MPGA', '', 'test', '/fake/plugin', true, {});

    const globalRulePath = path.join(tmpDir, '.antigravity', 'rules', 'mpga-global.md');
    expect(fs.existsSync(globalRulePath)).toBe(true);

    const content = fs.readFileSync(globalRulePath, 'utf-8');
    expect(content).toContain('MPGA Global Methodology');
    expect(content).toContain('MPGA/ directory');
    expect(content).toContain('evidence links');
    expect(content).toContain('TDD');
  });

  it('mpga-global.md contains always-do and never-do sections', () => {
    exportAntigravity('/unused', '/unused/MPGA', '', 'test', '/fake/plugin', true, {});

    const content = fs.readFileSync(
      path.join(tmpDir, '.antigravity', 'rules', 'mpga-global.md'),
      'utf-8',
    );
    expect(content).toContain('Always do');
    expect(content).toContain('Never do');
    expect(content).toContain('Evidence link format');
  });

  it('logs success for skills and global rules', () => {
    exportAntigravity('/unused', '/unused/MPGA', '', 'test', '/fake/plugin', true, {});

    expect(log.success).toHaveBeenCalledTimes(2);
    expect(log.success).toHaveBeenCalledWith(
      expect.stringContaining('~/.gemini/antigravity/skills/'),
    );
    expect(log.success).toHaveBeenCalledWith(
      expect.stringContaining('~/.antigravity/rules/mpga-global.md'),
    );
  });

  it('does not create project-level files when isGlobal is true', () => {
    const projectRoot = path.join(tmpDir, 'project');
    fs.mkdirSync(projectRoot, { recursive: true });

    exportAntigravity(
      projectRoot,
      path.join(projectRoot, 'MPGA'),
      '',
      'test',
      '/fake/plugin',
      true,
      {},
    );

    // None of the project-level artifacts should exist
    expect(fs.existsSync(path.join(projectRoot, 'GEMINI.md'))).toBe(false);
    expect(fs.existsSync(path.join(projectRoot, '.antigravity', 'rules'))).toBe(false);
    expect(fs.existsSync(path.join(projectRoot, '.agents', 'workflows'))).toBe(false);
  });
});
