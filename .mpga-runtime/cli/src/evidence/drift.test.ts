import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { runDriftCheck, healScopeFile, ScopeDriftReport } from './drift.js';

let tmpDir: string;

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'drift-test-'));
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

function mkdirp(dir: string) {
  fs.mkdirSync(dir, { recursive: true });
}

function writeFile(relativePath: string, content: string) {
  const full = path.join(tmpDir, relativePath);
  mkdirp(path.dirname(full));
  fs.writeFileSync(full, content, 'utf-8');
}

describe('runDriftCheck', () => {
  it('returns 100% health and empty scopes when MPGA/scopes/ does not exist', async () => {
    const report = await runDriftCheck(tmpDir, 80);
    expect(report.overallHealthPct).toBe(100);
    expect(report.scopes).toEqual([]);
    expect(report.totalLinks).toBe(0);
    expect(report.validLinks).toBe(0);
    expect(report.ciPass).toBe(true);
    expect(report.ciThreshold).toBe(80);
    expect(report.projectRoot).toBe(tmpDir);
    expect(report.timestamp).toBeTruthy();
  });

  it('returns 100% health when scope file has no evidence links', async () => {
    writeFile(
      'MPGA/scopes/empty.md',
      '# Empty Scope\n\nThis scope has no evidence links at all.\n',
    );

    const report = await runDriftCheck(tmpDir, 80);
    expect(report.overallHealthPct).toBe(100);
    expect(report.scopes).toHaveLength(1);
    expect(report.scopes[0].scope).toBe('empty');
    expect(report.scopes[0].totalLinks).toBe(0);
    expect(report.scopes[0].healthPct).toBe(100);
    expect(report.totalLinks).toBe(0);
    expect(report.ciPass).toBe(true);
  });

  it('reports valid links when files and symbols exist', async () => {
    // Create the source file with a function at lines 1-3
    writeFile('src/foo.ts', 'export function myFunction() {\n  return 42;\n}\n');

    // Create a scope file that references it
    writeFile('MPGA/scopes/core.md', '# Core Scope\n\n[E] src/foo.ts:1-3 :: myFunction\n');

    const report = await runDriftCheck(tmpDir, 80);
    expect(report.scopes).toHaveLength(1);
    const scope = report.scopes[0];
    expect(scope.scope).toBe('core');
    expect(scope.totalLinks).toBe(1);
    expect(scope.validLinks).toBe(1);
    expect(scope.staleLinks).toBe(0);
    expect(scope.healedLinks).toBe(0);
    expect(scope.healthPct).toBe(100);
    expect(scope.staleItems).toHaveLength(0);
    expect(report.overallHealthPct).toBe(100);
    expect(report.ciPass).toBe(true);
  });

  it('reports valid for file-only evidence link when the file exists', async () => {
    writeFile('src/bar.ts', 'export const x = 1;\n');
    writeFile('MPGA/scopes/misc.md', '# Misc\n\n[E] src/bar.ts\n');

    const report = await runDriftCheck(tmpDir, 80);
    const scope = report.scopes[0];
    expect(scope.totalLinks).toBe(1);
    expect(scope.validLinks).toBe(1);
    expect(scope.staleLinks).toBe(0);
    expect(scope.healthPct).toBe(100);
  });

  it('reports stale links when files are missing', async () => {
    // Create a scope file referencing a file that does not exist
    writeFile(
      'MPGA/scopes/broken.md',
      '# Broken Scope\n\n[E] src/nonexistent.ts:1-10 :: missingFunc\n',
    );

    const report = await runDriftCheck(tmpDir, 80);
    expect(report.scopes).toHaveLength(1);
    const scope = report.scopes[0];
    expect(scope.scope).toBe('broken');
    expect(scope.totalLinks).toBe(1);
    expect(scope.staleLinks).toBe(1);
    expect(scope.validLinks).toBe(0);
    expect(scope.healthPct).toBe(0);
    expect(scope.staleItems).toHaveLength(1);
    expect(scope.staleItems[0].reason).toContain('File not found');
    expect(scope.staleItems[0].link.filepath).toBe('src/nonexistent.ts');
    expect(report.overallHealthPct).toBe(0);
  });

  it('reports stale when file exists but symbol is not found', async () => {
    // File exists but does not contain the referenced symbol
    writeFile('src/exists.ts', 'export const unrelated = true;\n');
    writeFile('MPGA/scopes/sym.md', '# Sym\n\n[E] src/exists.ts:1-5 :: noSuchSymbol\n');

    const report = await runDriftCheck(tmpDir, 80);
    const scope = report.scopes[0];
    expect(scope.staleLinks).toBe(1);
    expect(scope.staleItems).toHaveLength(1);
    expect(scope.staleItems[0].reason).toBe('Symbol not found in file');
  });

  it('reports healed links when symbol moved to different lines', async () => {
    // The function exists but at different lines than the evidence link claims
    writeFile(
      'src/moved.ts',
      '// some header\n// another line\nexport function movedFunc() {\n  return 1;\n}\n',
    );

    // Evidence link says lines 1-3, but the function is actually at lines 3-5
    writeFile('MPGA/scopes/heal.md', '# Heal\n\n[E] src/moved.ts:1-3 :: movedFunc\n');

    const report = await runDriftCheck(tmpDir, 80);
    const scope = report.scopes[0];
    expect(scope.totalLinks).toBe(1);
    // The symbol was found elsewhere, so it should be healed (not stale)
    expect(scope.healedLinks + scope.validLinks).toBeGreaterThanOrEqual(1);
    expect(scope.staleLinks).toBe(0);
    expect(scope.healthPct).toBe(100);
  });

  it('scopeFilter limits to a single scope', async () => {
    writeFile('src/a.ts', 'export function funcA() {}\n');
    writeFile('src/b.ts', 'export function funcB() {}\n');
    writeFile('MPGA/scopes/alpha.md', '# Alpha\n\n[E] src/a.ts:1-1 :: funcA\n');
    writeFile('MPGA/scopes/beta.md', '# Beta\n\n[E] src/b.ts:1-1 :: funcB\n');

    const report = await runDriftCheck(tmpDir, 80, 'alpha');
    expect(report.scopes).toHaveLength(1);
    expect(report.scopes[0].scope).toBe('alpha');
  });

  it('scopeFilter returns empty scopes when filter matches nothing', async () => {
    writeFile('MPGA/scopes/alpha.md', '# Alpha\n\n[E] src/a.ts\n');

    const report = await runDriftCheck(tmpDir, 80, 'nonexistent');
    expect(report.scopes).toHaveLength(0);
    expect(report.overallHealthPct).toBe(100);
    expect(report.totalLinks).toBe(0);
  });

  it('ciPass is true when health >= threshold', async () => {
    writeFile('src/ok.ts', 'export function okFunc() {}\n');
    writeFile('MPGA/scopes/pass.md', '# Pass\n\n[E] src/ok.ts:1-1 :: okFunc\n');

    const report = await runDriftCheck(tmpDir, 100);
    expect(report.ciPass).toBe(true);
  });

  it('ciPass is false when health < threshold', async () => {
    // Scope references a missing file, so health will be 0%
    writeFile('MPGA/scopes/fail.md', '# Fail\n\n[E] src/missing.ts:1-10 :: gone\n');

    const report = await runDriftCheck(tmpDir, 50);
    expect(report.overallHealthPct).toBe(0);
    expect(report.ciPass).toBe(false);
  });

  it('computes overallHealthPct across multiple scopes', async () => {
    writeFile('src/good.ts', 'export function goodFunc() {}\n');
    // One scope with a valid link, one scope with a stale link
    writeFile('MPGA/scopes/good.md', '# Good\n\n[E] src/good.ts:1-1 :: goodFunc\n');
    writeFile('MPGA/scopes/bad.md', '# Bad\n\n[E] src/nope.ts:1-5 :: nope\n');

    const report = await runDriftCheck(tmpDir, 40);
    expect(report.totalLinks).toBe(2);
    // One valid (or healed) + one stale = 50%
    expect(report.overallHealthPct).toBe(50);
    expect(report.ciPass).toBe(true); // 50 >= 40
  });

  it('ignores non-.md files in scopes directory', async () => {
    writeFile('MPGA/scopes/data.json', '{"not": "a scope"}');
    writeFile('MPGA/scopes/readme.txt', 'not a scope');

    const report = await runDriftCheck(tmpDir, 80);
    expect(report.scopes).toHaveLength(0);
    expect(report.totalLinks).toBe(0);
  });

  it('filters out unknown and deprecated link types from drift check', async () => {
    writeFile(
      'MPGA/scopes/mixed.md',
      [
        '# Mixed',
        '[E] src/valid.ts',
        '[Unknown] some unknown thing',
        '[Deprecated] src/old.ts:1-5',
      ].join('\n'),
    );
    writeFile('src/valid.ts', 'export const v = 1;\n');

    const report = await runDriftCheck(tmpDir, 80);
    const scope = report.scopes[0];
    // Only the [E] link should be counted (unknown and deprecated are filtered out)
    expect(scope.totalLinks).toBe(1);
    expect(scope.validLinks).toBe(1);
  });
});

describe('healScopeFile', () => {
  it('replaces evidence link line ranges with healed values', () => {
    const scopePath = path.join(tmpDir, 'MPGA/scopes/healable.md');
    mkdirp(path.dirname(scopePath));
    const originalContent = [
      '# Healable Scope',
      '',
      'Some description here.',
      '',
      '[E] src/foo.ts:1-10 :: myFunction()',
      '[E] src/bar.ts:5-15 :: otherFunc()',
      '',
      'More text.',
    ].join('\n');
    fs.writeFileSync(scopePath, originalContent, 'utf-8');

    const report: ScopeDriftReport = {
      scope: 'healable',
      scopePath,
      totalLinks: 2,
      validLinks: 0,
      healedLinks: 2,
      staleLinks: 0,
      healthPct: 100,
      staleItems: [],
      healedItems: [
        {
          link: {
            raw: '[E] src/foo.ts:1-10 :: myFunction()',
            type: 'valid',
            filepath: 'src/foo.ts',
            startLine: 1,
            endLine: 10,
            symbol: 'myFunction',
            confidence: 1.0,
          },
          newStart: 20,
          newEnd: 35,
        },
        {
          link: {
            raw: '[E] src/bar.ts:5-15 :: otherFunc()',
            type: 'valid',
            filepath: 'src/bar.ts',
            startLine: 5,
            endLine: 15,
            symbol: 'otherFunc',
            confidence: 1.0,
          },
          newStart: 50,
          newEnd: 70,
        },
      ],
    };

    const result = healScopeFile(report);
    expect(result.healed).toBe(2);
    expect(result.content).toContain('[E] src/foo.ts:20-35 :: myFunction()');
    expect(result.content).toContain('[E] src/bar.ts:50-70 :: otherFunc()');
    // Original line ranges should be gone
    expect(result.content).not.toContain(':1-10');
    expect(result.content).not.toContain(':5-15');
  });

  it('returns healed count', () => {
    const scopePath = path.join(tmpDir, 'MPGA/scopes/count.md');
    mkdirp(path.dirname(scopePath));
    fs.writeFileSync(
      scopePath,
      '# Count\n\n[E] src/x.ts:1-5 :: alpha()\n[E] src/y.ts:10-20 :: beta()\n',
      'utf-8',
    );

    const report: ScopeDriftReport = {
      scope: 'count',
      scopePath,
      totalLinks: 2,
      validLinks: 0,
      healedLinks: 2,
      staleLinks: 0,
      healthPct: 100,
      staleItems: [],
      healedItems: [
        {
          link: {
            raw: '[E] src/x.ts:1-5 :: alpha()',
            type: 'valid',
            filepath: 'src/x.ts',
            startLine: 1,
            endLine: 5,
            symbol: 'alpha',
            confidence: 1.0,
          },
          newStart: 3,
          newEnd: 8,
        },
        {
          link: {
            raw: '[E] src/y.ts:10-20 :: beta()',
            type: 'valid',
            filepath: 'src/y.ts',
            startLine: 10,
            endLine: 20,
            symbol: 'beta',
            confidence: 1.0,
          },
          newStart: 12,
          newEnd: 25,
        },
      ],
    };

    const result = healScopeFile(report);
    expect(result.healed).toBe(2);
  });

  it('handles scope file with no healable links', () => {
    const scopePath = path.join(tmpDir, 'MPGA/scopes/noheal.md');
    mkdirp(path.dirname(scopePath));
    const content = '# No Heal\n\nJust some text, no evidence links.\n';
    fs.writeFileSync(scopePath, content, 'utf-8');

    const report: ScopeDriftReport = {
      scope: 'noheal',
      scopePath,
      totalLinks: 0,
      validLinks: 0,
      healedLinks: 0,
      staleLinks: 0,
      healthPct: 100,
      staleItems: [],
      healedItems: [],
    };

    const result = healScopeFile(report);
    expect(result.healed).toBe(0);
    expect(result.content).toBe(content);
  });

  it('preserves non-evidence content when healing', () => {
    const scopePath = path.join(tmpDir, 'MPGA/scopes/preserve.md');
    mkdirp(path.dirname(scopePath));
    const content = [
      '# Preserve Scope',
      '',
      'Important description that must survive.',
      '',
      '## Evidence',
      '[E] src/keep.ts:1-5 :: keepFunc()',
      '',
      '## Notes',
      'These notes should not change.',
    ].join('\n');
    fs.writeFileSync(scopePath, content, 'utf-8');

    const report: ScopeDriftReport = {
      scope: 'preserve',
      scopePath,
      totalLinks: 1,
      validLinks: 0,
      healedLinks: 1,
      staleLinks: 0,
      healthPct: 100,
      staleItems: [],
      healedItems: [
        {
          link: {
            raw: '[E] src/keep.ts:1-5 :: keepFunc()',
            type: 'valid',
            filepath: 'src/keep.ts',
            startLine: 1,
            endLine: 5,
            symbol: 'keepFunc',
            confidence: 1.0,
          },
          newStart: 10,
          newEnd: 20,
        },
      ],
    };

    const result = healScopeFile(report);
    expect(result.healed).toBe(1);
    expect(result.content).toContain('Important description that must survive.');
    expect(result.content).toContain('These notes should not change.');
    expect(result.content).toContain('[E] src/keep.ts:10-20 :: keepFunc()');
  });

  it('skips healed items with no filepath', () => {
    const scopePath = path.join(tmpDir, 'MPGA/scopes/nopath.md');
    mkdirp(path.dirname(scopePath));
    const content = '# No Path\n\nSome content.\n';
    fs.writeFileSync(scopePath, content, 'utf-8');

    const report: ScopeDriftReport = {
      scope: 'nopath',
      scopePath,
      totalLinks: 1,
      validLinks: 0,
      healedLinks: 1,
      staleLinks: 0,
      healthPct: 100,
      staleItems: [],
      healedItems: [
        {
          link: {
            raw: '[E] something',
            type: 'valid',
            confidence: 0.5,
            // no filepath
          },
          newStart: 1,
          newEnd: 5,
        },
      ],
    };

    const result = healScopeFile(report);
    expect(result.healed).toBe(0);
    expect(result.content).toBe(content);
  });

  it('heals evidence link without symbol', () => {
    const scopePath = path.join(tmpDir, 'MPGA/scopes/nosym.md');
    mkdirp(path.dirname(scopePath));
    const content = '# No Symbol\n\n[E] src/plain.ts:1-10\n';
    fs.writeFileSync(scopePath, content, 'utf-8');

    const report: ScopeDriftReport = {
      scope: 'nosym',
      scopePath,
      totalLinks: 1,
      validLinks: 0,
      healedLinks: 1,
      staleLinks: 0,
      healthPct: 100,
      staleItems: [],
      healedItems: [
        {
          link: {
            raw: '[E] src/plain.ts:1-10',
            type: 'valid',
            filepath: 'src/plain.ts',
            startLine: 1,
            endLine: 10,
            confidence: 1.0,
          },
          newStart: 5,
          newEnd: 15,
        },
      ],
    };

    const result = healScopeFile(report);
    expect(result.healed).toBe(1);
    expect(result.content).toContain('[E] src/plain.ts:5-15');
    expect(result.content).not.toContain(':1-10');
  });
});
