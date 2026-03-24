/**
 * Discriminated type representing the verification status of an evidence link.
 * - `'valid'` — link target exists and matches
 * - `'unknown'` — unverified placeholder with a description
 * - `'stale'` — link target could not be found, tagged with a date
 * - `'deprecated'` — link target is explicitly marked as deprecated
 */
export type EvidenceLinkType = 'valid' | 'unknown' | 'stale' | 'deprecated';

/**
 * Parsed representation of an evidence link extracted from markdown content.
 * Evidence links tie prose claims to specific code locations.
 */
export interface EvidenceLink {
  /** The original raw text of the evidence link as it appeared in the source */
  raw: string;
  /** The verification status of this link */
  type: EvidenceLinkType;
  /** Relative file path the link points to */
  filepath?: string;
  /** Start line number of the referenced code range */
  startLine?: number;
  /** End line number of the referenced code range */
  endLine?: number;
  /** Symbol name (function, class, etc.) referenced by this link */
  symbol?: string;
  /** The kind of symbol referenced */
  symbolType?: 'function' | 'class' | 'method' | 'variable' | 'type';
  /** Human-readable description (used for 'unknown' type links) */
  description?: string;
  /** ISO date string indicating when the link was marked stale */
  staleDate?: string;
  /** ISO date string of the last successful verification */
  lastVerified?: string;
  /** Confidence score from 0 to 1 indicating trust in this link's accuracy */
  confidence: number;
}

// Patterns (legacy range-based):
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

// Patterns (symbol-based):
// [E] src/foo.ts#symbolName:170 — description
// [E] src/foo.ts#symbolName:170
// [E] src/foo.ts#symbolName — description
// [E] src/foo.ts#symbolName
// [Stale:2026-03-20] src/foo.ts#symbolName:170
// [Deprecated] src/foo.ts#symbolName:170
const EVIDENCE_SYMBOL_RE = /\[E\]\s+(\S+?)#(\w+)(?::(\d+))?\s*(?:—\s*(.+))?$/;
const STALE_SYMBOL_RE = /\[Stale:(\d{4}-\d{2}-\d{2})\]\s+(\S+?)#(\w+)(?::(\d+))?\s*(?:—\s*(.+))?$/;
const DEPRECATED_SYMBOL_RE = /\[Deprecated\]\s+(\S+?)#(\w+)(?::(\d+))?\s*(?:—\s*(.+))?$/;

// Strip markdown artifacts (backticks, trailing table pipes) from parsed values
function cleanParsed(s: string): string {
  return s
    .replace(/`/g, '')
    .replace(/\s*\|?\s*$/, '')
    .trim();
}

/**
 * Parses a single line of text to extract an evidence link, if present.
 * Supports [E], [Unknown], [Stale:DATE], and [Deprecated] link formats.
 *
 * @param line - A single line of text that may contain an evidence link
 * @returns The parsed EvidenceLink, or null if the line does not contain a recognized evidence link
 */
export function parseEvidenceLink(line: string): EvidenceLink | null {
  const raw = line.trim();
  // Strip backticks (markdown artifacts) before regex matching
  line = raw.replace(/`/g, '');

  // Try symbol-based patterns first (they contain '#' which is more specific)
  let m = EVIDENCE_SYMBOL_RE.exec(line);
  if (m) {
    return {
      raw,
      type: 'valid',
      filepath: cleanParsed(m[1]),
      symbol: cleanParsed(m[2]),
      startLine: m[3] ? parseInt(m[3]) : undefined,
      description: m[4] ? m[4].trim() : undefined,
      confidence: 1.0,
    };
  }

  m = STALE_SYMBOL_RE.exec(line);
  if (m) {
    return {
      raw,
      type: 'stale',
      staleDate: m[1],
      filepath: cleanParsed(m[2]),
      symbol: cleanParsed(m[3]),
      startLine: m[4] ? parseInt(m[4]) : undefined,
      description: m[5] ? m[5].trim() : undefined,
      confidence: 0,
    };
  }

  m = DEPRECATED_SYMBOL_RE.exec(line);
  if (m) {
    return {
      raw,
      type: 'deprecated',
      filepath: cleanParsed(m[1]),
      symbol: cleanParsed(m[2]),
      startLine: m[3] ? parseInt(m[3]) : undefined,
      description: m[4] ? m[4].trim() : undefined,
      confidence: 0.5,
    };
  }

  // Legacy range-based patterns
  m = EVIDENCE_RE.exec(line);
  if (m) {
    return {
      raw,
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
    return { raw, type: 'unknown', description: m[1], confidence: 0 };
  }

  m = STALE_RE.exec(line);
  if (m) {
    return {
      raw,
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
      raw,
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

/**
 * Parses all evidence links from a block of markdown content by splitting
 * it into lines and extracting any recognized evidence link from each line.
 *
 * @param content - Multi-line markdown content to parse
 * @returns An array of all parsed EvidenceLink objects found in the content
 */
export function parseEvidenceLinks(content: string): EvidenceLink[] {
  return content
    .split('\n')
    .map((line) => parseEvidenceLink(line))
    .filter((l): l is EvidenceLink => l !== null);
}

/**
 * Determines whether a link should use the symbol-based format.
 * Symbol-based format is used when a symbol is present and there is no endLine
 * (i.e., it has a line hint, not a line range).
 */
function isSymbolBased(link: EvidenceLink): boolean {
  return !!link.symbol && !link.endLine;
}

/**
 * Formats the symbol-based portion of an evidence link: `file#symbol:lineHint — description`.
 */
function formatSymbolRef(link: EvidenceLink): string {
  let s = `${link.filepath}#${link.symbol}`;
  if (link.startLine) s += `:${link.startLine}`;
  if (link.description) s += ` — ${link.description}`;
  return s;
}

/**
 * Formats the legacy range-based portion of an evidence link: `file:start-end :: symbol()`.
 */
function formatRangeRef(link: EvidenceLink): string {
  let s = `${link.filepath}`;
  if (link.startLine && link.endLine) s += `:${link.startLine}-${link.endLine}`;
  if (link.symbol) s += ` :: ${link.symbol}()`;
  return s;
}

/**
 * Formats an EvidenceLink back into its canonical string representation,
 * suitable for writing into markdown scope files.
 *
 * Uses symbol-based format (`file#symbol:lineHint`) when a symbol is present
 * without an endLine. Falls back to legacy range format (`file:start-end :: symbol()`)
 * for links with both startLine and endLine.
 *
 * @param link - The EvidenceLink to format
 * @returns The formatted evidence link string
 */
export function formatEvidenceLink(link: EvidenceLink): string {
  if (link.type === 'unknown') return `[Unknown] ${link.description ?? ''}`;

  const useSymbol = isSymbolBased(link);
  const ref = useSymbol ? formatSymbolRef(link) : formatRangeRef(link);

  if (link.type === 'stale') return `[Stale:${link.staleDate}] ${ref}`;
  if (link.type === 'deprecated') return `[Deprecated] ${ref}`;
  return `[E] ${ref}`;
}

/**
 * Computes aggregate statistics for a collection of evidence links,
 * counting links by type and calculating the overall health percentage.
 *
 * @param links - Array of EvidenceLink objects to compute statistics for
 * @returns An object with counts by type (`total`, `valid`, `stale`, `unknown`, `deprecated`) and `healthPct` (0-100)
 */
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
