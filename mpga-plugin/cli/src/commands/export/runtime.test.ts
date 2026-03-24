import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import {
  copyVendoredRuntime,
  globalVendoredCliCommand,
  projectVendoredCliCommand,
} from './runtime.js';

describe('runtime export helper', () => {
  let tmpDir: string;
  let pluginRoot: string;
  let projectRoot: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-runtime-test-'));
    pluginRoot = path.join(tmpDir, 'plugin');
    projectRoot = path.join(tmpDir, 'project');
    fs.mkdirSync(path.join(pluginRoot, 'bin'), { recursive: true });
    fs.mkdirSync(path.join(pluginRoot, 'scripts'), { recursive: true });
    fs.mkdirSync(path.join(pluginRoot, 'cli', 'src'), { recursive: true });
    fs.writeFileSync(path.join(pluginRoot, 'bin', 'mpga.sh'), '#!/usr/bin/env bash\n');
    fs.writeFileSync(path.join(pluginRoot, 'scripts', 'setup.sh'), '#!/usr/bin/env bash\n');
    fs.writeFileSync(path.join(pluginRoot, 'cli', 'package.json'), '{"name":"mpga"}\n');
    fs.writeFileSync(path.join(pluginRoot, 'cli', 'package-lock.json'), '{"lockfileVersion":3}\n');
    fs.writeFileSync(path.join(pluginRoot, 'cli', 'tsconfig.json'), '{}\n');
    fs.writeFileSync(path.join(pluginRoot, 'cli', 'src', 'index.ts'), 'export {};\n');
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('copies bin, scripts, and cli assets into .mpga-runtime with a manifest', () => {
    const runtimeDir = copyVendoredRuntime(projectRoot, pluginRoot);
    expect(runtimeDir).toBe(path.join(projectRoot, '.mpga-runtime'));
    expect(fs.existsSync(path.join(runtimeDir!, 'bin', 'mpga.sh'))).toBe(true);
    expect(fs.existsSync(path.join(runtimeDir!, 'scripts', 'setup.sh'))).toBe(true);
    expect(fs.existsSync(path.join(runtimeDir!, 'cli', 'src', 'index.ts'))).toBe(true);
    expect(fs.existsSync(path.join(runtimeDir!, 'manifest.json'))).toBe(true);
  });

  it('computes project and global vendored cli commands', () => {
    expect(projectVendoredCliCommand()).toBe('node ./.mpga-runtime/cli/dist/index.js');
    expect(globalVendoredCliCommand('/tmp/tool-root')).toBe(
      '/tmp/tool-root/.mpga-runtime/cli/dist/index.js',
    );
  });
});
