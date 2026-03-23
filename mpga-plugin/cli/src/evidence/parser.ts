export type EvidenceLinkType = 'valid' | 'unknown' | 'stale' | 'deprecated';

export interface EvidenceLink {
  raw: string;
  type: EvidenceLinkType;
  filepath?: string;
  startLine?: number;
  endLine?: number;
  symbol?: string;
  symbolType?: 'function' | 'class' | 'method' | 'variable' | 'type';
  description?: string;
  staleDate?: string;
  lastVerified?: string;
  confidence: number;
}

// Patterns:
// [E] src/foo.ts:10-20 :: symbolName()
// [E] src/foo.ts:10-20
// [E] src/foo.ts :: symbolName
// [Unknown] description
// [Stale:2026-03-20] src/foo.ts:10-20
// [Deprecated] src/foo.ts:10-20
const EVIDENCE_RE = /\[E\]\s+(\S+?)(?::(\d+)-(\d+))?\s*(?:::\s*(.+))?$/;
const UNKNOWN_RE = /\[Unknown\]\s+(.+)$/;
const STALE_RE = /\[Stale:(\d{4}-\d{2}-\d{2})\]\s+(\S+?)(?::(\d+)-(\d+))?\s*(?:::\s*(.+))?$/;
const DEPRECATED_RE = /\[Deprecated\]\s+(\S+?)(?::(\d+)-(\d+))?\s*(?:::\s*(.+))?$/;

// Strip markdown artifacts (backticks, trailing table pipes) from parsed values
function cleanParsed(s: string): string {
  return s
    .replace(/`/g, '')
    .replace(/\s*\|?\s*$/, '')
    .trim();
}

export function parseEvidenceLink(line: string): EvidenceLink | null {
  line = line.trim();

  let m = EVIDENCE_RE.exec(line);
  if (m) {
    return {
      raw: line,
      type: 'valid',
      filepath: cleanParsed(m[1]),
      startLine: m[2] ? parseInt(m[2]) : undefined,
      endLine: m[3] ? parseInt(m[3]) : undefined,
      symbol: m[4] ? cleanParsed(m[4]).replace(/\(\)$/, '') : undefined,
      confidence: 1.0,
    };
  }

  m = UNKNOWN_RE.exec(line);
  if (m) {
    return { raw: line, type: 'unknown', description: m[1], confidence: 0 };
  }

  m = STALE_RE.exec(line);
  if (m) {
    return {
      raw: line,
      type: 'stale',
      staleDate: m[1],
      filepath: cleanParsed(m[2]),
      startLine: m[3] ? parseInt(m[3]) : undefined,
      endLine: m[4] ? parseInt(m[4]) : undefined,
      symbol: m[5] ? cleanParsed(m[5]).replace(/\(\)$/, '') : undefined,
      confidence: 0,
    };
  }

  m = DEPRECATED_RE.exec(line);
  if (m) {
    return {
      raw: line,
      type: 'deprecated',
      filepath: cleanParsed(m[1]),
      startLine: m[2] ? parseInt(m[2]) : undefined,
      endLine: m[3] ? parseInt(m[3]) : undefined,
      symbol: m[4] ? cleanParsed(m[4]).replace(/\(\)$/, '') : undefined,
      confidence: 0.5,
    };
  }

  return null;
}

export function parseEvidenceLinks(content: string): EvidenceLink[] {
  return content
    .split('\n')
    .map((line) => parseEvidenceLink(line))
    .filter((l): l is EvidenceLink => l !== null);
}

export function formatEvidenceLink(link: EvidenceLink): string {
  if (link.type === 'unknown') return `[Unknown] ${link.description ?? ''}`;
  if (link.type === 'stale') {
    let s = `[Stale:${link.staleDate}] ${link.filepath}`;
    if (link.startLine && link.endLine) s += `:${link.startLine}-${link.endLine}`;
    if (link.symbol) s += ` :: ${link.symbol}()`;
    return s;
  }
  if (link.type === 'deprecated') {
    let s = `[Deprecated] ${link.filepath}`;
    if (link.startLine && link.endLine) s += `:${link.startLine}-${link.endLine}`;
    if (link.symbol) s += ` :: ${link.symbol}()`;
    return s;
  }
  // valid
  let s = `[E] ${link.filepath}`;
  if (link.startLine && link.endLine) s += `:${link.startLine}-${link.endLine}`;
  if (link.symbol) s += ` :: ${link.symbol}()`;
  return s;
}

export function evidenceStats(links: EvidenceLink[]): {
  total: number;
  valid: number;
  stale: number;
  unknown: number;
  deprecated: number;
  healthPct: number;
} {
  const total = links.length;
  const valid = links.filter((l) => l.type === 'valid').length;
  const stale = links.filter((l) => l.type === 'stale').length;
  const unknown = links.filter((l) => l.type === 'unknown').length;
  const deprecated = links.filter((l) => l.type === 'deprecated').length;
  const healthPct = total === 0 ? 100 : Math.round((valid / total) * 100);
  return { total, valid, stale, unknown, deprecated, healthPct };
}
