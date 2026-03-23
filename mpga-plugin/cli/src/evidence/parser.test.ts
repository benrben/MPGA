import { describe, it, expect } from 'vitest';
import {
  parseEvidenceLink,
  parseEvidenceLinks,
  formatEvidenceLink,
  evidenceStats,
  EvidenceLink,
} from './parser.js';

describe('parseEvidenceLink', () => {
  it('parses a full evidence link with line range and symbol', () => {
    const result = parseEvidenceLink('[E] src/auth/jwt.ts:42-67 :: generateAccessToken()');
    expect(result).toEqual({
      raw: '[E] src/auth/jwt.ts:42-67 :: generateAccessToken()',
      type: 'valid',
      filepath: 'src/auth/jwt.ts',
      startLine: 42,
      endLine: 67,
      symbol: 'generateAccessToken',
      confidence: 1.0,
    });
  });

  it('parses an evidence link with line range only', () => {
    const result = parseEvidenceLink('[E] src/foo.ts:10-20');
    expect(result).toMatchObject({
      type: 'valid',
      filepath: 'src/foo.ts',
      startLine: 10,
      endLine: 20,
      symbol: undefined,
    });
  });

  it('parses an AST-only evidence link', () => {
    const result = parseEvidenceLink('[E] src/foo.ts :: validateToken');
    expect(result).toMatchObject({
      type: 'valid',
      filepath: 'src/foo.ts',
      startLine: undefined,
      symbol: 'validateToken',
    });
  });

  it('parses unknown links', () => {
    const result = parseEvidenceLink('[Unknown] token rotation logic');
    expect(result).toMatchObject({
      type: 'unknown',
      description: 'token rotation logic',
      confidence: 0,
    });
  });

  it('parses stale links', () => {
    const result = parseEvidenceLink('[Stale:2026-03-20] src/auth/jwt.ts:42-67');
    expect(result).toMatchObject({
      type: 'stale',
      staleDate: '2026-03-20',
      filepath: 'src/auth/jwt.ts',
      startLine: 42,
      endLine: 67,
    });
  });

  it('parses deprecated links', () => {
    const result = parseEvidenceLink('[Deprecated] src/old.ts:1-10 :: oldFunc()');
    expect(result).toMatchObject({
      type: 'deprecated',
      filepath: 'src/old.ts',
      symbol: 'oldFunc',
      confidence: 0.5,
    });
  });

  it('returns null for non-evidence lines', () => {
    expect(parseEvidenceLink('just a comment')).toBeNull();
    expect(parseEvidenceLink('## Heading')).toBeNull();
    expect(parseEvidenceLink('')).toBeNull();
  });

  it('strips backticks from parsed values', () => {
    const result = parseEvidenceLink('[E] `src/foo.ts`:10-20 :: `bar()`');
    expect(result?.filepath).toBe('src/foo.ts');
    expect(result?.symbol).toBe('bar');
  });
});

describe('parseEvidenceLinks', () => {
  it('extracts all evidence links from multiline content', () => {
    const content = `
## Evidence
[E] src/a.ts:1-10 :: funcA()
Some text
[Unknown] missing docs
[E] src/b.ts :: funcB
`;
    const links = parseEvidenceLinks(content);
    expect(links).toHaveLength(3);
    expect(links[0].type).toBe('valid');
    expect(links[1].type).toBe('unknown');
    expect(links[2].type).toBe('valid');
  });

  it('returns empty array for content with no evidence', () => {
    expect(parseEvidenceLinks('# Just a heading\nSome text.')).toEqual([]);
  });
});

describe('formatEvidenceLink', () => {
  it('formats a valid link with symbol', () => {
    const link: EvidenceLink = {
      raw: '',
      type: 'valid',
      filepath: 'src/a.ts',
      startLine: 1,
      endLine: 10,
      symbol: 'foo',
      confidence: 1.0,
    };
    expect(formatEvidenceLink(link)).toBe('[E] src/a.ts:1-10 :: foo()');
  });

  it('formats a valid link without line range', () => {
    const link: EvidenceLink = {
      raw: '',
      type: 'valid',
      filepath: 'src/a.ts',
      symbol: 'foo',
      confidence: 1.0,
    };
    expect(formatEvidenceLink(link)).toBe('[E] src/a.ts :: foo()');
  });

  it('formats unknown links', () => {
    const link: EvidenceLink = {
      raw: '',
      type: 'unknown',
      description: 'something',
      confidence: 0,
    };
    expect(formatEvidenceLink(link)).toBe('[Unknown] something');
  });

  it('formats stale links', () => {
    const link: EvidenceLink = {
      raw: '',
      type: 'stale',
      staleDate: '2026-03-20',
      filepath: 'src/a.ts',
      startLine: 1,
      endLine: 5,
      confidence: 0,
    };
    expect(formatEvidenceLink(link)).toBe('[Stale:2026-03-20] src/a.ts:1-5');
  });
});

describe('evidenceStats', () => {
  it('calculates correct statistics', () => {
    const links: EvidenceLink[] = [
      { raw: '', type: 'valid', filepath: 'a.ts', confidence: 1 },
      { raw: '', type: 'valid', filepath: 'b.ts', confidence: 1 },
      { raw: '', type: 'stale', filepath: 'c.ts', staleDate: '2026-01-01', confidence: 0 },
      { raw: '', type: 'unknown', description: 'x', confidence: 0 },
    ];
    const stats = evidenceStats(links);
    expect(stats.total).toBe(4);
    expect(stats.valid).toBe(2);
    expect(stats.stale).toBe(1);
    expect(stats.unknown).toBe(1);
    expect(stats.healthPct).toBe(50);
  });

  it('returns 100% for empty links', () => {
    expect(evidenceStats([]).healthPct).toBe(100);
  });
});
