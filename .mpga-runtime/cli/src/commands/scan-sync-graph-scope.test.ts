import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { Command } from 'commander';

vi.mock('../core/config.js', async (importOriginal) => {
  const actual = (await importOriginal()) as any;
  return {
    ...actual,
    findProjectRoot: vi.fn(),
  };
});

// ── Helpers ─────────────────────────────────────────────────────

let tmpDir: string;
let logSpy: ReturnType<typeof vi.spyOn>;
let errorSpy: ReturnType<typeof vi.spyOn>;

function createMpgaStructure(): void {
  const mpgaDir = path.join(tmpDir, 'MPGA');
  const scopesDir = path.join(mpgaDir, 'scopes');
  fs.mkdirSync(scopesDir, { recursive: true });
}

function writeConfig(): void {
  const config = {
    version: '1.0.0',
    project: {
      name: 'test-project',
      languages: ['typescript'],
      entryPoints: [],
      ignore: ['node_modules', 'dist', '.git', 'MPGA/'],
    },
  };
  fs.writeFileSync(path.join(tmpDir, 'mpga.config.json'), JSON.stringify(config, null, 2));
}

function writeSampleTsFiles(): void {
  const srcDir = path.join(tmpDir, 'src');
  fs.mkdirSync(srcDir, { recursive: true });

  fs.writeFileSync(
    path.join(srcDir, 'index.ts'),
    `export function main(): void {\n  console.log('hello');\n}\n`,
  );
  fs.writeFileSync(
    path.join(srcDir, 'utils.ts'),
    `export function add(a: number, b: number): number {\n  return a + b;\n}\n`,
  );
}

function writeGraphMd(): void {
  const mpgaDir = path.join(tmpDir, 'MPGA');
  fs.mkdirSync(mpgaDir, { recursive: true });
  fs.writeFileSync(
    path.join(mpgaDir, 'GRAPH.md'),
    '# Dependency graph\n\n## Module dependencies\n\n(no inter-module dependencies detected)\n',
  );
}

function writeScopeFile(name: string, content?: string): void {
  const scopesDir = path.join(tmpDir, 'MPGA', 'scopes');
  fs.mkdirSync(scopesDir, { recursive: true });
  const body =
    content ??
    `# Scope: ${name}\n\n## Summary\nTest scope\n\n## Confidence and notes\n- **Health:** ✓ fresh\n- **Last verified:** 2026-01-01\n`;
  fs.writeFileSync(path.join(scopesDir, `${name}.md`), body);
}

async function runCommand(register: (program: Command) => void, args: string[]): Promise<void> {
  const program = new Command();
  program.exitOverride();
  register(program);
  await program.parseAsync(['node', 'test', ...args]);
}

// ── Setup / Teardown ────────────────────────────────────────────

beforeEach(async () => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-cmd-test-'));
  const { findProjectRoot } = await import('../core/config.js');
  (findProjectRoot as any).mockReturnValue(tmpDir);
  logSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
  errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
  logSpy.mockRestore();
  errorSpy.mockRestore();
  vi.restoreAllMocks();
});

// ═══════════════════════════════════════════════════════════════
// scan
// ═══════════════════════════════════════════════════════════════

describe('scan command', () => {
  it('scan --json returns valid ScanResult JSON with files and languages', async () => {
    const { registerScan } = await import('./scan.js');
    writeConfig();
    writeSampleTsFiles();

    await runCommand(registerScan, ['scan', '--json']);

    // Find the console.log call that has the JSON
    const jsonCall = logSpy.mock.calls.find((call) => {
      try {
        const parsed = JSON.parse(call[0] as string);
        return parsed && typeof parsed === 'object' && 'files' in parsed;
      } catch {
        return false;
      }
    });

    expect(jsonCall).toBeDefined();
    const result = JSON.parse(jsonCall![0] as string);
    expect(result).toHaveProperty('files');
    expect(result).toHaveProperty('totalFiles');
    expect(result).toHaveProperty('totalLines');
    expect(result).toHaveProperty('languages');
    expect(result.totalFiles).toBeGreaterThanOrEqual(2);
    expect(result.languages).toHaveProperty('typescript');
  });

  it('scan finds TypeScript files in temp directory', async () => {
    const { registerScan } = await import('./scan.js');
    writeConfig();
    writeSampleTsFiles();

    await runCommand(registerScan, ['scan', '--json']);

    const jsonCall = logSpy.mock.calls.find((call) => {
      try {
        const parsed = JSON.parse(call[0] as string);
        return parsed && typeof parsed === 'object' && 'files' in parsed;
      } catch {
        return false;
      }
    });

    expect(jsonCall).toBeDefined();
    const result = JSON.parse(jsonCall![0] as string);
    const tsFiles = result.files.filter(
      (f: { filepath: string; language: string }) => f.language === 'typescript',
    );
    expect(tsFiles.length).toBeGreaterThanOrEqual(2);
    const filePaths = tsFiles.map((f: { filepath: string }) => f.filepath);
    expect(filePaths).toContain('src/index.ts');
    expect(filePaths).toContain('src/utils.ts');
  });
});

// ═══════════════════════════════════════════════════════════════
// sync
// ═══════════════════════════════════════════════════════════════

describe('sync command', () => {
  it('sync creates GRAPH.md, scopes, and INDEX.md', async () => {
    const { registerSync } = await import('./sync.js');
    writeConfig();
    writeSampleTsFiles();
    createMpgaStructure();

    await runCommand(registerSync, ['sync']);

    const mpgaDir = path.join(tmpDir, 'MPGA');
    expect(fs.existsSync(path.join(mpgaDir, 'GRAPH.md'))).toBe(true);
    expect(fs.existsSync(path.join(mpgaDir, 'INDEX.md'))).toBe(true);

    const graphContent = fs.readFileSync(path.join(mpgaDir, 'GRAPH.md'), 'utf-8');
    expect(graphContent).toContain('Dependency graph');

    const indexContent = fs.readFileSync(path.join(mpgaDir, 'INDEX.md'), 'utf-8');
    expect(indexContent).toContain('test-project');

    // Scopes dir should contain at least one scope
    const scopesDir = path.join(mpgaDir, 'scopes');
    expect(fs.existsSync(scopesDir)).toBe(true);
    const scopeFiles = fs.readdirSync(scopesDir).filter((f) => f.endsWith('.md'));
    expect(scopeFiles.length).toBeGreaterThanOrEqual(1);
  });

  it('sync errors when MPGA not initialized', async () => {
    const { registerSync } = await import('./sync.js');
    writeConfig();
    // Do NOT create MPGA dir

    const exitSpy = vi.spyOn(process, 'exit').mockImplementation((() => {
      throw new Error('process.exit');
    }) as any);

    try {
      await runCommand(registerSync, ['sync']);
    } catch {
      // Expected — process.exit throws
    }

    expect(exitSpy).toHaveBeenCalledWith(1);
    // Check that the error message was logged
    const errorCalls = errorSpy.mock.calls.map((c) => c.join(' ')).join(' ');
    expect(errorCalls).toContain('MPGA not initialized');
    exitSpy.mockRestore();
  });
});

// ═══════════════════════════════════════════════════════════════
// graph
// ═══════════════════════════════════════════════════════════════

describe('graph command', () => {
  it('graph show prints GRAPH.md content', async () => {
    const { registerGraph } = await import('./graph.js');
    writeConfig();
    writeGraphMd();

    await runCommand(registerGraph, ['graph', 'show']);

    const allOutput = logSpy.mock.calls.map((c) => c.join(' ')).join('\n');
    expect(allOutput).toContain('Dependency graph');
    expect(allOutput).toContain('Module dependencies');
  });

  it('graph show errors when GRAPH.md does not exist', async () => {
    const { registerGraph } = await import('./graph.js');
    writeConfig();
    // Do NOT write GRAPH.md

    const exitSpy = vi.spyOn(process, 'exit').mockImplementation((() => {
      throw new Error('process.exit');
    }) as any);

    try {
      await runCommand(registerGraph, ['graph', 'show']);
    } catch {
      // Expected — process.exit throws
    }

    expect(exitSpy).toHaveBeenCalledWith(1);
    const errorCalls = errorSpy.mock.calls.map((c) => c.join(' ')).join(' ');
    expect(errorCalls).toContain('GRAPH.md not found');
    exitSpy.mockRestore();
  });
});

// ═══════════════════════════════════════════════════════════════
// scope
// ═══════════════════════════════════════════════════════════════

describe('scope command', () => {
  it('scope add creates a new scope markdown file', async () => {
    const { registerScope } = await import('./scope.js');
    createMpgaStructure();

    await runCommand(registerScope, ['scope', 'add', 'my-new-scope']);

    const scopePath = path.join(tmpDir, 'MPGA', 'scopes', 'my-new-scope.md');
    expect(fs.existsSync(scopePath)).toBe(true);
    const content = fs.readFileSync(scopePath, 'utf-8');
    expect(content).toContain('# Scope: my-new-scope');
    expect(content).toContain('## Summary');
    expect(content).toContain('## Evidence index');
  });

  it('scope add errors when scope already exists', async () => {
    const { registerScope } = await import('./scope.js');
    createMpgaStructure();
    writeScopeFile('existing-scope');

    const exitSpy = vi.spyOn(process, 'exit').mockImplementation((() => {
      throw new Error('process.exit');
    }) as any);

    try {
      await runCommand(registerScope, ['scope', 'add', 'existing-scope']);
    } catch {
      // Expected — process.exit throws
    }

    expect(exitSpy).toHaveBeenCalledWith(1);
    const errorCalls = errorSpy.mock.calls.map((c) => c.join(' ')).join(' ');
    expect(errorCalls).toContain('already exists');
    exitSpy.mockRestore();
  });

  it('scope remove archives a scope file', async () => {
    const { registerScope } = await import('./scope.js');
    createMpgaStructure();
    writeScopeFile('to-remove');

    const scopePath = path.join(tmpDir, 'MPGA', 'scopes', 'to-remove.md');
    expect(fs.existsSync(scopePath)).toBe(true);

    await runCommand(registerScope, ['scope', 'remove', 'to-remove']);

    // Original file should be gone
    expect(fs.existsSync(scopePath)).toBe(false);

    // Should be archived
    const archiveDir = path.join(tmpDir, 'MPGA', 'milestones', '_archived-scopes');
    expect(fs.existsSync(archiveDir)).toBe(true);
    const archived = fs.readdirSync(archiveDir);
    expect(archived.length).toBe(1);
    expect(archived[0]).toMatch(/^to-remove-\d+\.md$/);
  });

  it('scope list shows scopes without crashing', async () => {
    const { registerScope } = await import('./scope.js');
    createMpgaStructure();
    writeScopeFile('alpha');
    writeScopeFile('beta');

    // Should not throw
    await runCommand(registerScope, ['scope', 'list']);

    // Verify some output was produced (the header or table rows)
    expect(logSpy).toHaveBeenCalled();
  });
});
