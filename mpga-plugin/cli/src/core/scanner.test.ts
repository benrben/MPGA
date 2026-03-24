import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { detectLanguage, countLines, scan, detectProjectType } from './scanner.js';
import type { ScanResult } from './scanner.js';

describe('detectLanguage', () => {
  it('returns "other" for unknown extension', () => {
    expect(detectLanguage('file.xyz')).toBe('other');
  });

  it('maps .ts to typescript', () => {
    expect(detectLanguage('src/index.ts')).toBe('typescript');
  });

  it('maps .tsx to typescript', () => {
    expect(detectLanguage('App.tsx')).toBe('typescript');
  });

  it('maps .js to javascript', () => {
    expect(detectLanguage('lib/utils.js')).toBe('javascript');
  });

  it('maps .mjs to javascript', () => {
    expect(detectLanguage('module.mjs')).toBe('javascript');
  });

  it('maps .py to python', () => {
    expect(detectLanguage('main.py')).toBe('python');
  });

  it('maps .go to go', () => {
    expect(detectLanguage('cmd/server.go')).toBe('go');
  });

  it('maps .rs to rust', () => {
    expect(detectLanguage('src/lib.rs')).toBe('rust');
  });

  it('maps .sh to shell', () => {
    expect(detectLanguage('deploy.sh')).toBe('shell');
  });

  it('maps .yaml and .yml to yaml', () => {
    expect(detectLanguage('config.yaml')).toBe('yaml');
    expect(detectLanguage('ci.yml')).toBe('yaml');
  });

  it('is case-insensitive on extension', () => {
    expect(detectLanguage('FILE.TS')).toBe('typescript');
  });

  it('handles files with no extension', () => {
    expect(detectLanguage('Makefile')).toBe('other');
  });
});

describe('countLines', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-scanner-test-'));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('counts lines in a file', () => {
    const fp = path.join(tmpDir, 'test.txt');
    fs.writeFileSync(fp, 'line1\nline2\nline3\n');
    expect(countLines(fp)).toBe(4); // trailing newline creates empty 4th element
  });

  it('returns 1 for a single-line file with no newline', () => {
    const fp = path.join(tmpDir, 'single.txt');
    fs.writeFileSync(fp, 'hello');
    expect(countLines(fp)).toBe(1);
  });

  it('returns 0 for a nonexistent file', () => {
    expect(countLines(path.join(tmpDir, 'nope.txt'))).toBe(0);
  });

  it('returns 1 for an empty file', () => {
    const fp = path.join(tmpDir, 'empty.txt');
    fs.writeFileSync(fp, '');
    expect(countLines(fp)).toBe(1); // ''.split('\n') => ['']
  });

  it('returns 0 for an unreadable file', () => {
    const fp = path.join(tmpDir, 'noperm.txt');
    fs.writeFileSync(fp, 'content');
    fs.chmodSync(fp, 0o000);
    expect(countLines(fp)).toBe(0);
    fs.chmodSync(fp, 0o644); // restore for cleanup
  });
});

describe('detectProjectType', () => {
  function makeScanResult(
    languages: Record<string, { files: number; lines: number }>,
    filePaths: string[] = [],
  ): ScanResult {
    return {
      root: '/tmp',
      files: filePaths.map((fp) => ({ filepath: fp, lines: 10, language: 'other', size: 100 })),
      totalFiles: filePaths.length,
      totalLines: filePaths.length * 10,
      languages,
      entryPoints: [],
      topLevelDirs: [],
    };
  }

  it('returns "Unknown" when no languages', () => {
    expect(detectProjectType(makeScanResult({}))).toBe('Unknown');
  });

  it('detects Next.js', () => {
    const result = makeScanResult({ typescript: { files: 5, lines: 500 } }, [
      'src/index.ts',
      'next.config.js',
    ]);
    expect(detectProjectType(result)).toBe('Next.js');
  });

  it('detects React', () => {
    const result = makeScanResult({ typescript: { files: 5, lines: 500 } }, [
      'src/App.tsx',
      'node_modules/react/index.js',
    ]);
    expect(detectProjectType(result)).toBe('React');
  });

  it('detects Node.js API (express)', () => {
    const result = makeScanResult({ typescript: { files: 3, lines: 300 } }, [
      'src/server.ts',
      'node_modules/express/index.js',
    ]);
    expect(detectProjectType(result)).toBe('Node.js API');
  });

  it('detects plain TypeScript', () => {
    const result = makeScanResult({ typescript: { files: 3, lines: 300 } }, ['src/index.ts']);
    expect(detectProjectType(result)).toBe('TypeScript');
  });

  it('detects Django', () => {
    const result = makeScanResult({ python: { files: 10, lines: 1000 } }, [
      'manage.py',
      'myapp/django/settings.py',
    ]);
    expect(detectProjectType(result)).toBe('Django');
  });

  it('detects plain Python', () => {
    const result = makeScanResult({ python: { files: 5, lines: 500 } }, ['main.py']);
    expect(detectProjectType(result)).toBe('Python');
  });

  it('detects Go', () => {
    const result = makeScanResult({ go: { files: 5, lines: 500 } }, ['cmd/main.go']);
    expect(detectProjectType(result)).toBe('Go');
  });

  it('detects Rust', () => {
    const result = makeScanResult({ rust: { files: 3, lines: 300 } }, ['src/main.rs']);
    expect(detectProjectType(result)).toBe('Rust');
  });

  it('detects Java', () => {
    const result = makeScanResult({ java: { files: 10, lines: 1000 } }, ['src/Main.java']);
    expect(detectProjectType(result)).toBe('Java');
  });
});

describe('scan', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-scan-test-'));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('scans an empty directory', async () => {
    const result = await scan(tmpDir, []);
    expect(result.root).toBe(tmpDir);
    expect(result.files).toEqual([]);
    expect(result.totalFiles).toBe(0);
    expect(result.totalLines).toBe(0);
    expect(result.languages).toEqual({});
  });

  it('finds files and computes languages', async () => {
    fs.writeFileSync(path.join(tmpDir, 'index.ts'), 'const x = 1;\n');
    fs.writeFileSync(
      path.join(tmpDir, 'util.ts'),
      'export function foo() {}\nexport function bar() {}\n',
    );
    fs.writeFileSync(path.join(tmpDir, 'style.css'), 'body {}'); // not in glob

    const result = await scan(tmpDir, []);
    expect(result.totalFiles).toBe(2);
    expect(result.languages.typescript).toEqual({ files: 2, lines: 5 }); // 2 + 3
    expect(result.files.every((f) => f.language === 'typescript')).toBe(true);
  });

  it('respects ignore patterns', async () => {
    fs.mkdirSync(path.join(tmpDir, 'node_modules'), { recursive: true });
    fs.writeFileSync(path.join(tmpDir, 'node_modules', 'lib.ts'), 'x');
    fs.writeFileSync(path.join(tmpDir, 'app.ts'), 'y\n');

    const result = await scan(tmpDir, ['node_modules']);
    expect(result.totalFiles).toBe(1);
    expect(result.files[0].filepath).toBe('app.ts');
  });

  it('detects entry points', async () => {
    fs.mkdirSync(path.join(tmpDir, 'src'), { recursive: true });
    fs.writeFileSync(path.join(tmpDir, 'src', 'index.ts'), 'main');

    const result = await scan(tmpDir, []);
    expect(result.entryPoints).toContain('src/index.ts');
  });

  it('lists top-level directories excluding ignored and dotfiles', async () => {
    fs.mkdirSync(path.join(tmpDir, 'src'));
    fs.mkdirSync(path.join(tmpDir, 'lib'));
    fs.mkdirSync(path.join(tmpDir, '.git'));
    fs.mkdirSync(path.join(tmpDir, 'node_modules'));

    const result = await scan(tmpDir, ['node_modules']);
    expect(result.topLevelDirs).toContain('src');
    expect(result.topLevelDirs).toContain('lib');
    expect(result.topLevelDirs).not.toContain('.git');
    expect(result.topLevelDirs).not.toContain('node_modules');
  });

  it('computes file size', async () => {
    const content = 'hello world\n';
    fs.writeFileSync(path.join(tmpDir, 'hello.ts'), content);

    const result = await scan(tmpDir, []);
    expect(result.files[0].size).toBe(Buffer.byteLength(content));
  });

  it('excludes non-code file extensions', async () => {
    fs.writeFileSync(path.join(tmpDir, 'readme.md'), '# Hello');
    fs.writeFileSync(path.join(tmpDir, 'style.css'), 'body {}');
    fs.writeFileSync(path.join(tmpDir, 'data.csv'), 'a,b');
    fs.writeFileSync(path.join(tmpDir, 'app.ts'), 'x');

    const result = await scan(tmpDir, []);
    expect(result.totalFiles).toBe(1);
    expect(result.files[0].filepath).toBe('app.ts');
  });

  it('deduplicates entry points', async () => {
    // index.ts matches both 'index.*' and could match other patterns
    fs.writeFileSync(path.join(tmpDir, 'index.ts'), 'main');

    const result = await scan(tmpDir, []);
    const indexCount = result.entryPoints.filter((e) => e === 'index.ts').length;
    expect(indexCount).toBe(1);
  });
});
