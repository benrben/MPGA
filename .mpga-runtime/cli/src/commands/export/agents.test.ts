import { describe, expect, it, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { copySkillsTo, readAgentInstructions, rewriteCliReferences } from './agents.js';

describe('export agent/skill CLI rewriting', () => {
  let tmpDir: string;
  let pluginRoot: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-export-agents-'));
    pluginRoot = path.join(tmpDir, 'plugin');
    fs.mkdirSync(path.join(pluginRoot, 'skills', 'rally'), { recursive: true });
    fs.mkdirSync(path.join(pluginRoot, 'agents'), { recursive: true });
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('rewrites both placeholder and hardcoded npx CLI references when vendoring skills', () => {
    fs.writeFileSync(
      path.join(pluginRoot, 'skills', 'rally', 'SKILL.md'),
      [
        'Run node ${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js sync',
        `Or run node ${pluginRoot.replace(/\\/g, '/')}/cli/dist/index.js board live --serve --open`,
        'Then run npx mpga export --all',
        '',
      ].join('\n'),
    );

    const targetDir = path.join(tmpDir, 'target-skills');
    copySkillsTo(targetDir, pluginRoot, 'claude', 'node ./.mpga-runtime/cli/dist/index.js');

    const content = fs.readFileSync(path.join(targetDir, 'mpga-rally', 'SKILL.md'), 'utf-8');
    expect(content).toContain('node ./.mpga-runtime/cli/dist/index.js sync');
    expect(content).toContain('node ./.mpga-runtime/cli/dist/index.js board live --serve --open');
    expect(content).toContain('node ./.mpga-runtime/cli/dist/index.js export --all');
    expect(content).not.toContain('npx mpga');
    expect(content).not.toContain('${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js');
  });

  it('rewrites both placeholder and hardcoded npx CLI references in agent instructions', () => {
    fs.writeFileSync(
      path.join(pluginRoot, 'agents', 'campaigner.md'),
      [
        '# Agent: campaigner',
        '',
        'Use node ${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js sync',
        `Fallback: node ${pluginRoot.replace(/\\/g, '/')}/cli/dist/index.js init --from-existing`,
        'Fallback: npx mpga init --from-existing',
        '',
      ].join('\n'),
    );

    const content = readAgentInstructions(
      pluginRoot,
      'campaigner',
      'node ./.mpga-runtime/cli/dist/index.js',
    );

    expect(content).toContain('node ./.mpga-runtime/cli/dist/index.js sync');
    expect(content).toContain('node ./.mpga-runtime/cli/dist/index.js init --from-existing');
    expect(content).not.toContain('npx mpga');
    expect(content).not.toContain('${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js');
  });

  it('falls back to npx mpga when no vendored path is provided', () => {
    const content = rewriteCliReferences(
      'Use node ${CLAUDE_PLUGIN_ROOT}/cli/dist/index.js drift --quick',
    );
    expect(content).toContain('npx mpga drift --quick');
  });
});
