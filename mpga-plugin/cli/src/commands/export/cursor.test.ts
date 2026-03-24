import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

// ─── Mocks ──────────────────────────────────────────────────────────────────

// Mock the logger so nothing leaks to stdout
vi.mock('../../core/logger.js', () => ({
  log: {
    info: vi.fn(),
    success: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock agents.ts — we control AGENTS, SKILL_NAMES, copySkillsTo, readAgentInstructions
vi.mock('./agents.js', () => ({
  AGENTS: [
    {
      slug: 'test-agent',
      name: 'mpga-test-agent',
      description: 'A test agent',
      model: 'claude-sonnet-4-6',
      readonly: false,
      isBackground: false,
      sandboxMode: 'workspace',
    },
    {
      slug: 'scout',
      name: 'mpga-scout',
      description: 'Read-only scout',
      model: 'claude-sonnet-4-6',
      readonly: true,
      isBackground: true,
      sandboxMode: 'none',
    },
  ],
  SKILL_NAMES: ['sync-project', 'plan'],
  copySkillsTo: vi.fn(),
  readAgentInstructions: vi.fn(
    (_pluginRoot: string | null, slug: string, cliPath?: string) =>
      `Instructions for ${slug}\n\n${cliPath ?? String.raw`node ${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js`} sync`,
  ),
}));

// Provide a sentinel so readAgentInstructions can reference it in its template
const CLAUDE_PLUGIN_ROOT = '${CLAUDE_PLUGIN_ROOT}';

import { exportCursor } from './cursor.js';
import { log } from '../../core/logger.js';
import { AGENTS, copySkillsTo, readAgentInstructions } from './agents.js';

const mockedCopySkillsTo = vi.mocked(copySkillsTo);
const mockedReadAgentInstructions = vi.mocked(readAgentInstructions);
const mockedLog = vi.mocked(log);

// ─── Helpers ────────────────────────────────────────────────────────────────

/** Return everything written to a path via fs.writeFileSync as a string. */
function writtenContent(filePath: string): string {
  const call = vi
    .mocked(fs.writeFileSync)
    .mock.calls.find(([p]) => (p as string).includes(filePath));
  if (!call) throw new Error(`writeFileSync never called with path containing "${filePath}"`);
  return call[1] as string;
}

// ─── Test suites ────────────────────────────────────────────────────────────

describe('exportCursor', () => {
  const projectRoot = '/fake/project';
  const mpgaDir = '/fake/project/MPGA';
  const indexContent = '# INDEX\n\n## Active milestone\nM001-alpha\n';
  const projectName = 'test-project';
  const pluginRoot = '/fake/plugin';

  beforeEach(() => {
    vi.spyOn(fs, 'mkdirSync').mockReturnValue(undefined);
    vi.spyOn(fs, 'writeFileSync').mockReturnValue(undefined);
    vi.spyOn(fs, 'existsSync').mockReturnValue(false);
    vi.spyOn(fs, 'readdirSync').mockReturnValue([]);
    mockedCopySkillsTo.mockClear();
    mockedReadAgentInstructions.mockClear();
    mockedReadAgentInstructions.mockImplementation(
      (_pluginRoot: string | null, slug: string, cliPath?: string) =>
        `Instructions for ${slug}\n\n${cliPath ?? 'node ${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js'} sync`,
    );
    vi.mocked(mockedLog.info).mockClear();
    vi.mocked(mockedLog.success).mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ── Project-level (isGlobal = false) ────────────────────────────────────

  describe('project-level export (isGlobal = false)', () => {
    it('creates .cursor/rules directory', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, false);

      expect(fs.mkdirSync).toHaveBeenCalledWith(path.join(projectRoot, '.cursor', 'rules'), {
        recursive: true,
      });
    });

    it('writes 4 MDC rule files', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, false);

      const rulesDir = path.join(projectRoot, '.cursor', 'rules');
      const writeCalls = vi
        .mocked(fs.writeFileSync)
        .mock.calls.filter(([p]) => (p as string).startsWith(rulesDir));
      expect(writeCalls.length).toBe(4);
    });

    it('generates mpga-project.mdc with YAML frontmatter and milestone', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, false);

      const content = writtenContent('mpga-project.mdc');
      expect(content).toContain('alwaysApply: true');
      expect(content).toContain('MPGA Project Context');
      expect(content).toContain('M001-alpha');
      expect(content).toContain('@MPGA/INDEX.md');
    });

    it('generates mpga-evidence.mdc with evidence protocol', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, false);

      const content = writtenContent('mpga-evidence.mdc');
      expect(content).toContain('Evidence Link Protocol');
      expect(content).toContain('[E]');
      expect(content).toContain('[Unknown]');
      expect(content).toContain('[Stale:');
      expect(content).toContain('node ./.mpga-runtime/cli/dist/index.js evidence verify');
    });

    it('generates mpga-tdd.mdc with TDD enforcement', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, false);

      const content = writtenContent('mpga-tdd.mdc');
      expect(content).toContain('TDD Protocol (mandatory)');
      expect(content).toContain('WRITE FAILING TEST FIRST');
    });

    it('generates mpga-scopes.mdc with "no scopes" fallback when dir missing', () => {
      vi.mocked(fs.existsSync).mockReturnValue(false);

      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, false);

      const content = writtenContent('mpga-scopes.mdc');
      expect(content).toContain('MPGA Scope Lookup');
      expect(content).toContain('no scopes yet');
    });

    it('generates mpga-scopes.mdc listing existing scope files', () => {
      vi.mocked(fs.existsSync).mockImplementation((p) => {
        return (p as string).includes('scopes');
      });
      vi.mocked(fs.readdirSync).mockImplementation(((p: string) => {
        if (p.includes('scopes')) {
          return ['core.md', 'board.md'] as unknown as fs.Dirent[];
        }
        return [] as unknown as fs.Dirent[];
      }) as unknown as typeof fs.readdirSync);

      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, false);

      const content = writtenContent('mpga-scopes.mdc');
      expect(content).toContain('core');
      expect(content).toContain('board');
      expect(content).toContain('@MPGA/scopes/core.md');
      expect(content).toContain('@MPGA/scopes/board.md');
    });

    it('copies skills to .cursor/skills/', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, false);

      expect(mockedCopySkillsTo).toHaveBeenCalledWith(
        path.join(projectRoot, '.cursor', 'skills'),
        pluginRoot,
        'cursor',
        'node ./.mpga-runtime/cli/dist/index.js',
      );
    });

    it('creates agent markdown files in .cursor/agents/', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, false);

      const agentsDir = path.join(projectRoot, '.cursor', 'agents');
      expect(fs.mkdirSync).toHaveBeenCalledWith(agentsDir, { recursive: true });

      // Each agent should have a written file
      for (const agent of AGENTS) {
        const content = writtenContent(`${agent.name}.md`);
        expect(content).toContain(`name: ${agent.name}`);
        expect(content).toContain(`description: ${agent.description}`);
        expect(content).toContain(`model: ${agent.model}`);
        expect(content).toContain(`readonly: ${agent.readonly}`);
        expect(content).toContain(`is_background: ${agent.isBackground}`);
      }
    });

    it('rewrites CLAUDE_PLUGIN_ROOT to the vendored runtime path in agent instructions', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, false);

      const content = writtenContent('mpga-test-agent.md');
      expect(content).toContain('node ./.mpga-runtime/cli/dist/index.js');
      expect(content).not.toContain('${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js');
    });

    it('logs success messages for rules, skills, and agents', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, false);

      expect(mockedLog.success).toHaveBeenCalledWith(expect.stringContaining('4 MDC files'));
      expect(mockedLog.success).toHaveBeenCalledWith(expect.stringContaining('skills'));
      expect(mockedLog.success).toHaveBeenCalledWith(expect.stringContaining('agents'));
    });
  });

  // ── Global export (isGlobal = true) ─────────────────────────────────────

  describe('global export (isGlobal = true)', () => {
    const origEnv = process.env.HOME;

    beforeEach(() => {
      process.env.HOME = '/fake/home';
    });

    afterEach(() => {
      process.env.HOME = origEnv;
    });

    it('logs the global cursor rules text', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, true);

      expect(mockedLog.info).toHaveBeenCalledWith(
        expect.stringContaining('Add the following to Cursor Settings'),
      );
      // Second call should contain the global rules text
      const secondCall = vi.mocked(mockedLog.info).mock.calls[1];
      expect(secondCall).toBeDefined();
      const rulesText = secondCall[0];
      expect(rulesText).toContain('MPGA/ directory');
      expect(rulesText).toContain('evidence links');
      expect(rulesText).toContain('[Unknown]');
    });

    it('copies skills to ~/.cursor/skills/', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, true);

      expect(mockedCopySkillsTo).toHaveBeenCalledWith(
        path.join('/fake/home', '.cursor', 'skills'),
        pluginRoot,
        'cursor',
        '/fake/home/.cursor/.mpga-runtime/cli/dist/index.js',
      );
    });

    it('creates agent markdown files in ~/.cursor/agents/', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, true);

      const agentsDir = path.join('/fake/home', '.cursor', 'agents');
      expect(fs.mkdirSync).toHaveBeenCalledWith(agentsDir, { recursive: true });

      for (const agent of AGENTS) {
        const content = writtenContent(`${agent.name}.md`);
        expect(content).toContain(`name: ${agent.name}`);
      }
    });

    it('logs success for skills and agents', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, true);

      expect(mockedLog.success).toHaveBeenCalledWith(expect.stringContaining('~/.cursor/skills/'));
      expect(mockedLog.success).toHaveBeenCalledWith(expect.stringContaining('~/.cursor/agents/'));
    });

    it('does NOT create project-level .cursor/rules/ directory', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, true);

      const mkdirCalls = vi.mocked(fs.mkdirSync).mock.calls.map(([p]) => p as string);
      const rulesCall = mkdirCalls.find((p) =>
        p.includes(path.join(projectRoot, '.cursor', 'rules')),
      );
      expect(rulesCall).toBeUndefined();
    });

    it('falls back to ~ when HOME is undefined', () => {
      delete process.env.HOME;

      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, true);

      expect(mockedCopySkillsTo).toHaveBeenCalledWith(
        path.join('~', '.cursor', 'skills'),
        pluginRoot,
        'cursor',
        '~/.cursor/.mpga-runtime/cli/dist/index.js',
      );

      const agentsDir = path.join('~', '.cursor', 'agents');
      expect(fs.mkdirSync).toHaveBeenCalledWith(agentsDir, { recursive: true });
    });
  });

  // ── Edge cases ──────────────────────────────────────────────────────────

  describe('edge cases', () => {
    it('handles missing milestone in indexContent', () => {
      const noMilestoneContent = '# INDEX\n\n## Scopes\n- core\n';

      exportCursor(projectRoot, mpgaDir, noMilestoneContent, projectName, pluginRoot, false);

      const content = writtenContent('mpga-project.mdc');
      expect(content).toContain('(none)');
    });

    it('handles null pluginRoot', () => {
      exportCursor(projectRoot, mpgaDir, indexContent, projectName, null, false);

      expect(mockedCopySkillsTo).toHaveBeenCalledWith(
        expect.any(String),
        null,
        'cursor',
        'npx mpga',
      );

      // Agent instructions should still be read (will return fallback text)
      expect(mockedReadAgentInstructions).toHaveBeenCalledWith(
        null,
        expect.any(String),
        'npx mpga',
      );
    });

    it('scopes mdc shows fallback when scopesDir exists but is empty', () => {
      vi.mocked(fs.existsSync).mockImplementation((p) => {
        return (p as string).includes('scopes');
      });
      vi.mocked(fs.readdirSync).mockImplementation(((p: string) => {
        if (p.includes('scopes')) {
          return [] as unknown as fs.Dirent[];
        }
        return [] as unknown as fs.Dirent[];
      }) as unknown as typeof fs.readdirSync);

      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, false);

      const content = writtenContent('mpga-scopes.mdc');
      expect(content).toContain('no scopes yet');
    });

    it('scopes mdc filters non-.md files', () => {
      vi.mocked(fs.existsSync).mockImplementation((p) => {
        return (p as string).includes('scopes');
      });
      vi.mocked(fs.readdirSync).mockImplementation(((p: string) => {
        if (p.includes('scopes')) {
          return ['core.md', 'README.txt', '.DS_Store'];
        }
        return [];
      }) as unknown as typeof fs.readdirSync);

      exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, false);

      const content = writtenContent('mpga-scopes.mdc');
      expect(content).toContain('core');
      expect(content).not.toContain('README.txt');
      expect(content).not.toContain('.DS_Store');
    });
  });
});
