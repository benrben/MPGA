import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';

// Mock the agents module so we control AGENTS, SKILL_NAMES, copySkillsTo, readAgentInstructions
vi.mock('./agents.js', () => ({
  AGENTS: [
    {
      slug: 'test-agent',
      name: 'mpga-test-agent',
      description: 'A test agent for unit tests',
      model: 'claude-sonnet-4-6',
      readonly: false,
      isBackground: false,
      sandboxMode: 'workspace',
    },
    {
      slug: 'readonly-agent',
      name: 'mpga-readonly-agent',
      description: 'A read-only "quoted" agent',
      model: 'claude-opus-4-6',
      readonly: true,
      isBackground: true,
      sandboxMode: 'none',
    },
  ],
  SKILL_NAMES: ['sync-project', 'plan'],
  copySkillsTo: vi.fn(),
  readAgentInstructions: vi.fn((_pluginRoot: string | null, slug: string, cliPath?: string) => {
    return `Instructions for ${slug}\nUse ${cliPath ?? 'node ${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js'} sync`;
  }),
}));

import { exportCodex } from './codex.js';
import { AGENTS, SKILL_NAMES, copySkillsTo, readAgentInstructions } from './agents.js';

const mockedCopySkillsTo = vi.mocked(copySkillsTo);
const mockedReadAgentInstructions = vi.mocked(readAgentInstructions);

describe('exportCodex', () => {
  let tmpDir: string;
  const originalHome = process.env.HOME;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-codex-test-'));
    // Set HOME to tmpDir so global exports go into our temp dir
    process.env.HOME = tmpDir;

    // Suppress log output
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    process.env.HOME = originalHome;
    fs.rmSync(tmpDir, { recursive: true, force: true });
    vi.restoreAllMocks();
    vi.clearAllMocks();
  });

  // ─── Project-level (non-global) export ──────────────────────────────────────

  describe('project-level export (isGlobal = false)', () => {
    let projectRoot: string;
    let mpgaDir: string;

    beforeEach(() => {
      projectRoot = path.join(tmpDir, 'my-project');
      mpgaDir = path.join(projectRoot, 'MPGA');
      fs.mkdirSync(mpgaDir, { recursive: true });
    });

    it('creates root AGENTS.md with project content', () => {
      const indexContent = '## File registry\n- src/index.ts\n';
      exportCodex(projectRoot, mpgaDir, indexContent, 'my-project', null, false);

      const agentsMdPath = path.join(projectRoot, 'AGENTS.md');
      expect(fs.existsSync(agentsMdPath)).toBe(true);

      const content = fs.readFileSync(agentsMdPath, 'utf-8');
      expect(content).toContain('MPGA');
      expect(content).toContain('Evidence link protocol');
      expect(content).toContain('TDD protocol');
      expect(content).toContain(indexContent);
    });

    it('creates MPGA/AGENTS.md navigation guide', () => {
      exportCodex(projectRoot, mpgaDir, '', 'my-project', null, false);

      const mpgaAgentsMd = path.join(mpgaDir, 'AGENTS.md');
      expect(fs.existsSync(mpgaAgentsMd)).toBe(true);

      const content = fs.readFileSync(mpgaAgentsMd, 'utf-8');
      expect(content).toContain('MPGA Knowledge Layer');
      expect(content).toContain('Tier 1');
      expect(content).toContain('Tier 2');
      expect(content).toContain('INDEX.md');
      expect(content).toContain('GRAPH.md');
    });

    it('generates subdirectory AGENTS.md files for scopes with matching src dirs', () => {
      // Set up scopes dir with a scope file
      const scopesDir = path.join(mpgaDir, 'scopes');
      fs.mkdirSync(scopesDir, { recursive: true });
      fs.writeFileSync(
        path.join(scopesDir, 'core.md'),
        '# Core\n[E] src/core/index.ts:1-10 :: main()\n[E] src/core/util.ts:5-20 :: helper()\n',
      );

      // Create matching src/core directory
      const srcCoreDir = path.join(projectRoot, 'src', 'core');
      fs.mkdirSync(srcCoreDir, { recursive: true });

      exportCodex(projectRoot, mpgaDir, '', 'my-project', null, false);

      const subdirAgentsMd = path.join(srcCoreDir, 'AGENTS.md');
      expect(fs.existsSync(subdirAgentsMd)).toBe(true);

      const content = fs.readFileSync(subdirAgentsMd, 'utf-8');
      expect(content).toContain('core Module');
      expect(content).toContain('MPGA/scopes/core.md');
      expect(content).toContain('[E] src/core/index.ts:1-10 :: main()');
    });

    it('skips subdirectory AGENTS.md when matching src dir does not exist', () => {
      const scopesDir = path.join(mpgaDir, 'scopes');
      fs.mkdirSync(scopesDir, { recursive: true });
      fs.writeFileSync(path.join(scopesDir, 'missing.md'), '# Missing\n');

      // Do NOT create src/missing directory
      exportCodex(projectRoot, mpgaDir, '', 'my-project', null, false);

      const subdirAgentsMd = path.join(projectRoot, 'src', 'missing', 'AGENTS.md');
      expect(fs.existsSync(subdirAgentsMd)).toBe(false);
    });

    it('shows fallback text when scope has no evidence links', () => {
      const scopesDir = path.join(mpgaDir, 'scopes');
      fs.mkdirSync(scopesDir, { recursive: true });
      fs.writeFileSync(path.join(scopesDir, 'empty.md'), '# Empty scope\nNo evidence here.\n');

      const srcEmptyDir = path.join(projectRoot, 'src', 'empty');
      fs.mkdirSync(srcEmptyDir, { recursive: true });

      exportCodex(projectRoot, mpgaDir, '', 'my-project', null, false);

      const content = fs.readFileSync(path.join(srcEmptyDir, 'AGENTS.md'), 'utf-8');
      expect(content).toContain('mpga sync');
    });

    it('calls copySkillsTo with correct arguments for project-level export', () => {
      exportCodex(projectRoot, mpgaDir, '', 'my-project', '/some/plugin', false);

      const expectedSkillsDir = path.join(projectRoot, '.codex', 'skills');
      expect(mockedCopySkillsTo).toHaveBeenCalledWith(
        expectedSkillsDir,
        '/some/plugin',
        'codex',
        'node ./.mpga-runtime/cli/dist/index.js',
      );
    });

    it('creates .codex/agents/ with TOML files for each agent', () => {
      exportCodex(projectRoot, mpgaDir, '', 'my-project', '/some/plugin', false);

      const agentsDir = path.join(projectRoot, '.codex', 'agents');
      expect(fs.existsSync(agentsDir)).toBe(true);

      for (const agent of AGENTS) {
        const tomlPath = path.join(agentsDir, `${agent.name}.toml`);
        expect(fs.existsSync(tomlPath)).toBe(true);

        const content = fs.readFileSync(tomlPath, 'utf-8');
        expect(content).toContain(`name = "${agent.name}"`);
        expect(content).toContain(`model = "${agent.model}"`);
        expect(content).toContain(`sandbox_mode = "${agent.sandboxMode}"`);
        expect(content).toContain('developer_instructions = """');
      }
    });

    it('TOML agent files replace local CLI references with vendored runtime path', () => {
      exportCodex(projectRoot, mpgaDir, '', 'my-project', '/some/plugin', false);

      const tomlPath = path.join(projectRoot, '.codex', 'agents', 'mpga-test-agent.toml');
      const content = fs.readFileSync(tomlPath, 'utf-8');

      expect(content).toContain('node ./.mpga-runtime/cli/dist/index.js');
      expect(content).not.toContain('${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js');
    });

    it('TOML agent files escape double quotes in description', () => {
      exportCodex(projectRoot, mpgaDir, '', 'my-project', null, false);

      // The "readonly-agent" has quotes in its description
      const tomlPath = path.join(projectRoot, '.codex', 'agents', 'mpga-readonly-agent.toml');
      const content = fs.readFileSync(tomlPath, 'utf-8');

      expect(content).toContain('description = "A read-only \\"quoted\\" agent"');
    });

    it('does not generate subdir AGENTS.md when scopes dir does not exist', () => {
      // No scopes dir at all
      exportCodex(projectRoot, mpgaDir, '', 'my-project', null, false);

      // Should not throw, and should still create root AGENTS.md
      expect(fs.existsSync(path.join(projectRoot, 'AGENTS.md'))).toBe(true);
    });
  });

  // ─── Global export ──────────────────────────────────────────────────────────

  describe('global export (isGlobal = true)', () => {
    it('creates ~/.codex/ directory', () => {
      exportCodex('/unused', '/unused/MPGA', '', 'proj', null, true);

      const codexDir = path.join(tmpDir, '.codex');
      expect(fs.existsSync(codexDir)).toBe(true);
    });

    it('writes AGENTS.md to ~/.codex/', () => {
      exportCodex('/unused', '/unused/MPGA', '', 'proj', null, true);

      const agentsMd = path.join(tmpDir, '.codex', 'AGENTS.md');
      expect(fs.existsSync(agentsMd)).toBe(true);

      const content = fs.readFileSync(agentsMd, 'utf-8');
      expect(content).toContain('MPGA Methodology (Global)');
      expect(content).toContain('Evidence over claims');
      expect(content).toContain('TDD is mandatory');
    });

    it('calls copySkillsTo with ~/.codex/skills/ path', () => {
      exportCodex('/unused', '/unused/MPGA', '', 'proj', '/plugin', true);

      const expectedSkillsDir = path.join(tmpDir, '.codex', 'skills');
      expect(mockedCopySkillsTo).toHaveBeenCalledWith(
        expectedSkillsDir,
        '/plugin',
        'codex',
        `${path.join(tmpDir, '.codex', '.mpga-runtime', 'cli', 'dist', 'index.js').replace(/\\/g, '/')}`,
      );
    });

    it('creates ~/.codex/agents/ with TOML files for each agent', () => {
      exportCodex('/unused', '/unused/MPGA', '', 'proj', '/plugin', true);

      const agentsDir = path.join(tmpDir, '.codex', 'agents');
      expect(fs.existsSync(agentsDir)).toBe(true);

      for (const agent of AGENTS) {
        const tomlPath = path.join(agentsDir, `${agent.name}.toml`);
        expect(fs.existsSync(tomlPath)).toBe(true);

        const content = fs.readFileSync(tomlPath, 'utf-8');
        expect(content).toContain(`name = "${agent.name}"`);
        expect(content).toContain(`description = "`);
        expect(content).toContain(`sandbox_mode = "${agent.sandboxMode}"`);
        expect(content).toContain('developer_instructions = """');
      }
    });

    it('uses ~ as fallback when HOME is undefined', () => {
      delete process.env.HOME;
      // This should not throw — it falls back to '~'
      expect(() => {
        exportCodex('/unused', '/unused/MPGA', '', 'proj', null, true);
      }).not.toThrow();
    });
  });

  // ─── TOML generation edge cases ─────────────────────────────────────────────

  describe('TOML generation', () => {
    it('escapes backslashes in agent instructions', () => {
      mockedReadAgentInstructions.mockReturnValueOnce('path\\to\\file');
      // second agent call
      mockedReadAgentInstructions.mockReturnValueOnce('simple instructions');

      const projectRoot = path.join(tmpDir, 'proj');
      const mpgaDir = path.join(projectRoot, 'MPGA');
      fs.mkdirSync(mpgaDir, { recursive: true });

      exportCodex(projectRoot, mpgaDir, '', 'proj', '/plugin', false);

      const tomlPath = path.join(projectRoot, '.codex', 'agents', 'mpga-test-agent.toml');
      const content = fs.readFileSync(tomlPath, 'utf-8');

      // Backslashes should be doubled for TOML
      expect(content).toContain('path\\\\to\\\\file');
    });

    it('escapes triple quotes in agent instructions', () => {
      mockedReadAgentInstructions.mockReturnValueOnce('Here is """triple quoted""" text');
      mockedReadAgentInstructions.mockReturnValueOnce('simple instructions');

      const projectRoot = path.join(tmpDir, 'proj');
      const mpgaDir = path.join(projectRoot, 'MPGA');
      fs.mkdirSync(mpgaDir, { recursive: true });

      exportCodex(projectRoot, mpgaDir, '', 'proj', '/plugin', false);

      const tomlPath = path.join(projectRoot, '.codex', 'agents', 'mpga-test-agent.toml');
      const content = fs.readFileSync(tomlPath, 'utf-8');

      // Triple quotes should be escaped
      expect(content).not.toMatch(/"""\s*triple/);
      expect(content).toContain('\\"\\"\\"');
    });

    it('readAgentInstructions is called with pluginRoot and slug', () => {
      const projectRoot = path.join(tmpDir, 'proj');
      const mpgaDir = path.join(projectRoot, 'MPGA');
      fs.mkdirSync(mpgaDir, { recursive: true });

      exportCodex(projectRoot, mpgaDir, '', 'proj', '/my/plugin', false);

      expect(mockedReadAgentInstructions).toHaveBeenCalledWith(
        '/my/plugin',
        'test-agent',
        'node ./.mpga-runtime/cli/dist/index.js',
      );
      expect(mockedReadAgentInstructions).toHaveBeenCalledWith(
        '/my/plugin',
        'readonly-agent',
        'node ./.mpga-runtime/cli/dist/index.js',
      );
    });
  });

  // ─── Content verification ──────────────────────────────────────────────────

  describe('generated content verification', () => {
    it('root AGENTS.md contains verification commands section', () => {
      const projectRoot = path.join(tmpDir, 'proj');
      const mpgaDir = path.join(projectRoot, 'MPGA');
      fs.mkdirSync(mpgaDir, { recursive: true });

      exportCodex(projectRoot, mpgaDir, '', 'proj', '/plugin', false);

      const content = fs.readFileSync(path.join(projectRoot, 'AGENTS.md'), 'utf-8');
      expect(content).toContain('npm test');
      expect(content).toContain('node ./.mpga-runtime/cli/dist/index.js evidence verify');
      expect(content).toContain('node ./.mpga-runtime/cli/dist/index.js board show');
    });

    it('root AGENTS.md contains timestamp', () => {
      const projectRoot = path.join(tmpDir, 'proj');
      const mpgaDir = path.join(projectRoot, 'MPGA');
      fs.mkdirSync(mpgaDir, { recursive: true });

      exportCodex(projectRoot, mpgaDir, '', 'proj', null, false);

      const content = fs.readFileSync(path.join(projectRoot, 'AGENTS.md'), 'utf-8');
      expect(content).toContain('Generated by MPGA');
    });

    it('MPGA AGENTS.md contains evidence link format documentation', () => {
      const projectRoot = path.join(tmpDir, 'proj');
      const mpgaDir = path.join(projectRoot, 'MPGA');
      fs.mkdirSync(mpgaDir, { recursive: true });

      exportCodex(projectRoot, mpgaDir, '', 'proj', null, false);

      const content = fs.readFileSync(path.join(mpgaDir, 'AGENTS.md'), 'utf-8');
      expect(content).toContain('[E] filepath:startLine-endLine');
      expect(content).toContain('[Unknown]');
      expect(content).toContain('[Stale:');
    });

    it('global AGENTS.md contains workflow steps', () => {
      exportCodex('/unused', '/unused/MPGA', '', 'proj', '/plugin', true);

      const content = fs.readFileSync(path.join(tmpDir, '.codex', 'AGENTS.md'), 'utf-8');
      expect(content).toContain('Read MPGA/INDEX.md');
      expect(content).toContain(
        path.join(tmpDir, '.codex', '.mpga-runtime', 'cli', 'dist', 'index.js'),
      );
    });

    it('subdirectory AGENTS.md limits evidence links to 5', () => {
      const projectRoot = path.join(tmpDir, 'proj');
      const mpgaDir = path.join(projectRoot, 'MPGA');
      const scopesDir = path.join(mpgaDir, 'scopes');
      fs.mkdirSync(scopesDir, { recursive: true });

      // Create a scope with more than 5 evidence links
      const links = Array.from({ length: 8 }, (_, i) => `[E] src/big/file${i}.ts:1-10 :: fn${i}()`);
      fs.writeFileSync(path.join(scopesDir, 'big.md'), `# Big\n${links.join('\n')}\n`);

      const srcBigDir = path.join(projectRoot, 'src', 'big');
      fs.mkdirSync(srcBigDir, { recursive: true });

      exportCodex(projectRoot, mpgaDir, '', 'proj', null, false);

      const content = fs.readFileSync(path.join(srcBigDir, 'AGENTS.md'), 'utf-8');
      // Should only have at most 5 evidence link lines
      const evidenceLines = content.split('\n').filter((l) => l.includes('[E]'));
      expect(evidenceLines.length).toBeLessThanOrEqual(5);
    });
  });
});
