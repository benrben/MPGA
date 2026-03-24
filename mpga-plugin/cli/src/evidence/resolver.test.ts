import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { resolveEvidence, verifyAllLinks } from './resolver.js';
import { EvidenceLink } from './parser.js';

let tmpDir: string;

beforeEach(() => {
  tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'resolver-test-'));
});

afterEach(() => {
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

function makeLink(overrides: Partial<EvidenceLink> = {}): EvidenceLink {
  return {
    raw: '[E] test',
    type: 'valid',
    confidence: 1.0,
    ...overrides,
  };
}

function writeFile(relativePath: string, content: string): void {
  const fullPath = path.join(tmpDir, relativePath);
  fs.mkdirSync(path.dirname(fullPath), { recursive: true });
  fs.writeFileSync(fullPath, content, 'utf-8');
}

describe('resolveEvidence', () => {
  it('returns stale with confidence 0 when no filepath is provided', () => {
    const link = makeLink({ filepath: undefined });
    const result = resolveEvidence(link, tmpDir);
    expect(result.status).toBe('stale');
    expect(result.confidence).toBe(0);
  });

  it('returns stale with confidence 0 when file does not exist', () => {
    const link = makeLink({ filepath: 'nonexistent/file.ts' });
    const result = resolveEvidence(link, tmpDir);
    expect(result.status).toBe('stale');
    expect(result.confidence).toBe(0);
  });

  it('returns valid with confidence 0.8 for file-only link (no symbol, no line range)', () => {
    writeFile('src/utils.ts', 'export const x = 1;\n');
    const link = makeLink({ filepath: 'src/utils.ts' });
    const result = resolveEvidence(link, tmpDir);
    expect(result.status).toBe('valid');
    expect(result.confidence).toBe(0.8);
  });

  it('returns valid with confidence 1.0 when line range matches symbol', () => {
    const source = [
      'const a = 1;',
      'export function greet(name: string) {',
      '  return `Hello, ${name}`;',
      '}',
      'const b = 2;',
    ].join('\n');
    writeFile('src/greet.ts', source);

    const link = makeLink({
      filepath: 'src/greet.ts',
      startLine: 2,
      endLine: 4,
      symbol: 'greet',
    });
    const result = resolveEvidence(link, tmpDir);
    expect(result.status).toBe('valid');
    expect(result.confidence).toBe(1.0);
    expect(result.startLine).toBe(2);
    expect(result.endLine).toBe(4);
  });

  it('returns healed with confidence 0.9 when lines shifted but symbol found via AST', () => {
    // The link claims the function is at lines 2-4, but we put it at lines 5-7
    // so verifyRange will fail, then findSymbol will locate it at new position
    const source = [
      '// comment line 1',
      '// comment line 2',
      '// comment line 3',
      '',
      'export function greet(name: string) {',
      '  return `Hello, ${name}`;',
      '}',
    ].join('\n');
    writeFile('src/greet.ts', source);

    const link = makeLink({
      filepath: 'src/greet.ts',
      startLine: 2,
      endLine: 4,
      symbol: 'greet',
    });
    const result = resolveEvidence(link, tmpDir);
    expect(result.status).toBe('healed');
    expect(result.confidence).toBe(0.9);
    expect(result.startLine).toBe(5);
    expect(result.healedFrom).toContain('line range changed');
    expect(result.healedFrom).toContain('was 2-4');
  });

  it('returns healed with confidence 0.6 via fuzzy text match when AST cannot find symbol', () => {
    // Use a symbol name that the regex-based AST extractor won't pick up
    // as a top-level declaration, but that appears as text in the file.
    // A string inside a comment or non-standard pattern works for this.
    const source = [
      '// This file has some logic',
      'const obj = {',
      '  mySpecialHandler: (x: number) => x * 2,',
      '};',
      'export default obj;',
    ].join('\n');
    writeFile('src/handler.ts', source);

    const link = makeLink({
      filepath: 'src/handler.ts',
      startLine: 10,
      endLine: 15,
      symbol: 'mySpecialHandler',
    });
    const result = resolveEvidence(link, tmpDir);
    expect(result.status).toBe('healed');
    expect(result.confidence).toBe(0.6);
    expect(result.startLine).toBe(3);
    expect(result.healedFrom).toContain('fuzzy match at line 3');
    expect(result.healedFrom).toContain('was 10-15');
  });

  it('returns stale when symbol is completely gone from the file', () => {
    const source = ['export function unrelatedFunction() {', '  return 42;', '}'].join('\n');
    writeFile('src/other.ts', source);

    const link = makeLink({
      filepath: 'src/other.ts',
      startLine: 1,
      endLine: 3,
      symbol: 'totallyMissingSymbol',
    });
    const result = resolveEvidence(link, tmpDir);
    expect(result.status).toBe('stale');
    expect(result.confidence).toBe(0);
  });

  it('returns valid with confidence 1.0 for line range without symbol', () => {
    const source = ['const a = 1;', 'const b = 2;', 'const c = 3;'].join('\n');
    writeFile('src/constants.ts', source);

    const link = makeLink({
      filepath: 'src/constants.ts',
      startLine: 1,
      endLine: 3,
    });
    const result = resolveEvidence(link, tmpDir);
    // verifyRange returns true when symbol is undefined and range exists
    expect(result.status).toBe('valid');
    expect(result.confidence).toBe(1.0);
  });

  it('returns valid (not healed) when AST finds symbol at exact same lines', () => {
    const source = ['export function doWork() {', '  return true;', '}'].join('\n');
    writeFile('src/work.ts', source);

    // First, verify what AST actually reports for this file
    // The function starts at line 1, block ends around line 3
    const link = makeLink({
      filepath: 'src/work.ts',
      startLine: 1,
      endLine: 3,
      symbol: 'doWork',
    });
    const result = resolveEvidence(link, tmpDir);
    // verifyRange should pass since lines 1-3 contain "doWork"
    expect(result.status).toBe('valid');
    expect(result.confidence).toBe(1.0);
  });

  it('handles file with only a symbol and no line range (AST lookup path)', () => {
    const source = ['export function compute(x: number) {', '  return x * x;', '}'].join('\n');
    writeFile('src/compute.ts', source);

    const link = makeLink({
      filepath: 'src/compute.ts',
      symbol: 'compute',
    });
    const result = resolveEvidence(link, tmpDir);
    // No startLine/endLine on the link, so it won't attempt verifyRange.
    // It will go to AST lookup since symbol is set.
    // AST will find it; since link has no startLine/endLine, healed check
    // compares undefined !== location.startLine → healed
    expect(result.status).toBe('healed');
    expect(result.confidence).toBe(0.9);
    expect(result.startLine).toBe(1);
  });
});

describe('verifyAllLinks', () => {
  it('filters out links that are not valid or stale type', () => {
    writeFile('src/a.ts', 'export const a = 1;\n');
    writeFile('src/b.ts', 'export const b = 2;\n');

    const links: EvidenceLink[] = [
      makeLink({ type: 'valid', filepath: 'src/a.ts' }),
      makeLink({ type: 'unknown', description: 'some unknown thing' }),
      makeLink({ type: 'deprecated', filepath: 'src/b.ts' }),
      makeLink({ type: 'stale', filepath: 'src/b.ts', staleDate: '2026-01-01' }),
    ];

    const results = verifyAllLinks(links, tmpDir);
    // Only 'valid' and 'stale' type links should be processed
    expect(results).toHaveLength(2);
    expect(results[0].link.type).toBe('valid');
    expect(results[1].link.type).toBe('stale');
  });

  it('returns resolved evidence for each processed link', () => {
    writeFile('src/exists.ts', 'export const x = 1;\n');

    const links: EvidenceLink[] = [
      makeLink({ type: 'valid', filepath: 'src/exists.ts' }),
      makeLink({ type: 'valid', filepath: 'src/missing.ts' }),
    ];

    const results = verifyAllLinks(links, tmpDir);
    expect(results).toHaveLength(2);
    expect(results[0].resolved.status).toBe('valid');
    expect(results[0].resolved.confidence).toBe(0.8);
    expect(results[1].resolved.status).toBe('stale');
    expect(results[1].resolved.confidence).toBe(0);
  });

  it('returns empty array when given no links', () => {
    const results = verifyAllLinks([], tmpDir);
    expect(results).toEqual([]);
  });

  it('processes a batch of mixed links correctly', () => {
    const source = [
      'export function alpha() {',
      '  return 1;',
      '}',
      '',
      'export function beta() {',
      '  return 2;',
      '}',
    ].join('\n');
    writeFile('src/funcs.ts', source);

    const links: EvidenceLink[] = [
      // valid type, file-only → resolved valid 0.8
      makeLink({ type: 'valid', filepath: 'src/funcs.ts' }),
      // valid type, correct range and symbol → resolved valid 1.0
      makeLink({
        type: 'valid',
        filepath: 'src/funcs.ts',
        startLine: 1,
        endLine: 3,
        symbol: 'alpha',
      }),
      // stale type, symbol completely missing → resolved stale
      makeLink({
        type: 'stale',
        filepath: 'src/funcs.ts',
        startLine: 1,
        endLine: 3,
        symbol: 'gamma',
        staleDate: '2026-01-01',
      }),
      // unknown type → filtered out
      makeLink({ type: 'unknown', description: 'not checked' }),
      // deprecated type → filtered out
      makeLink({ type: 'deprecated', filepath: 'src/funcs.ts' }),
    ];

    const results = verifyAllLinks(links, tmpDir);
    expect(results).toHaveLength(3);

    expect(results[0].resolved.status).toBe('valid');
    expect(results[0].resolved.confidence).toBe(0.8);

    expect(results[1].resolved.status).toBe('valid');
    expect(results[1].resolved.confidence).toBe(1.0);

    expect(results[2].resolved.status).toBe('stale');
    expect(results[2].resolved.confidence).toBe(0);
  });

  it('preserves the original link object in each result', () => {
    writeFile('src/x.ts', 'const x = 1;\n');

    const link = makeLink({ type: 'valid', filepath: 'src/x.ts', raw: '[E] src/x.ts' });
    const results = verifyAllLinks([link], tmpDir);

    expect(results[0].link).toBe(link); // same reference
    expect(results[0].link.raw).toBe('[E] src/x.ts');
  });
});
