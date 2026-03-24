import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';

vi.mock('../../core/logger.js', () => ({
  log: {
    info: vi.fn(),
    success: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('./agents.js', () => ({
  SKILL_NAMES: ['sync-project', 'plan'],
  copySkillsTo: vi.fn(),
}));

import { exportClaude } from './claude.js';
import { copySkillsTo } from './agents.js';

describe('exportClaude', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-claude-test-'));
    vi.spyOn(fs, 'existsSync').mockReturnValue(false);
    vi.spyOn(fs, 'mkdirSync').mockReturnValue(undefined);
    vi.spyOn(fs, 'writeFileSync').mockReturnValue(undefined);
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
    vi.restoreAllMocks();
  });

  it('points Claude skill exports at the vendored runtime path', () => {
    exportClaude(tmpDir, '# INDEX', 'proj', '/fake/plugin', false);
    expect(copySkillsTo).toHaveBeenCalledWith(
      path.join(tmpDir, '.claude', 'skills'),
      '/fake/plugin',
      'claude',
      'node ./.mpga-runtime/cli/dist/index.js',
    );
  });
});
