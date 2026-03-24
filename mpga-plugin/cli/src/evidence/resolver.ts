import fs from 'fs';
import path from 'path';
import { EvidenceLink } from './parser.js';
import { findSymbol, verifyRange } from './ast.js';

/** Confidence when only the file exists (no symbol or line range). */
const CONFIDENCE_FILE_ONLY = 0.8;
/** Confidence when the exact line range is verified. */
const CONFIDENCE_EXACT_RANGE = 1.0;
/** Confidence when the symbol is found via AST lookup. */
const CONFIDENCE_AST_ANCHOR = 0.9;
/** Confidence when the symbol is found via fuzzy text search. */
const CONFIDENCE_FUZZY_MATCH = 0.6;
/** Number of lines to include after a fuzzy match for the end-line estimate. */
const FUZZY_MATCH_LINE_LOOKAHEAD = 20;

export type ResolutionStatus = 'valid' | 'healed' | 'stale';

export interface ResolvedEvidence {
  status: ResolutionStatus;
  confidence: number;
  startLine?: number;
  endLine?: number;
  healedFrom?: string; // description of what changed
}

export function resolveEvidence(link: EvidenceLink, projectRoot: string): ResolvedEvidence {
  if (!link.filepath) {
    return { status: 'stale', confidence: 0 };
  }

  const fullPath = path.join(projectRoot, link.filepath);
  if (!fs.existsSync(fullPath)) {
    return { status: 'stale', confidence: 0 };
  }

  // Step 0: File-only link (no symbol, no line range) — file exists is enough
  if (!link.symbol && !link.startLine && !link.endLine) {
    return { status: 'valid', confidence: CONFIDENCE_FILE_ONLY };
  }

  // Step 1: Try exact line range
  if (link.startLine && link.endLine) {
    const rangeValid = verifyRange(
      link.filepath,
      link.startLine,
      link.endLine,
      link.symbol,
      projectRoot,
    );
    if (rangeValid) {
      return {
        status: 'valid',
        confidence: CONFIDENCE_EXACT_RANGE,
        startLine: link.startLine,
        endLine: link.endLine,
      };
    }
  }

  // Step 2: Try AST anchor (find symbol by name)
  if (link.symbol) {
    const location = findSymbol(link.filepath, link.symbol, projectRoot);
    if (location) {
      const healed = link.startLine !== location.startLine || link.endLine !== location.endLine;
      return {
        status: healed ? 'healed' : 'valid',
        confidence: CONFIDENCE_AST_ANCHOR,
        startLine: location.startLine,
        endLine: location.endLine,
        healedFrom: healed
          ? `line range changed: was ${link.startLine}-${link.endLine}, now ${location.startLine}-${location.endLine}`
          : undefined,
      };
    }
  }

  // Step 3: Fuzzy search (symbol name anywhere in file)
  if (link.symbol) {
    try {
      const content = fs.readFileSync(fullPath, 'utf-8');
      const lines = content.split('\n');
      for (let i = 0; i < lines.length; i++) {
        if (lines[i].includes(link.symbol)) {
          return {
            status: 'healed',
            confidence: CONFIDENCE_FUZZY_MATCH,
            startLine: i + 1,
            endLine: Math.min(i + FUZZY_MATCH_LINE_LOOKAHEAD, lines.length),
            healedFrom: `fuzzy match at line ${i + 1} (was ${link.startLine}-${link.endLine})`,
          };
        }
      }
    } catch {
      // ignore
    }
  }

  // Step 4: File exists but symbol not found
  return { status: 'stale', confidence: 0 };
}

export interface VerifyResult {
  link: EvidenceLink;
  resolved: ResolvedEvidence;
}

export function verifyAllLinks(links: EvidenceLink[], projectRoot: string): VerifyResult[] {
  return links
    .filter((l) => l.type === 'valid' || l.type === 'stale')
    .map((link) => ({ link, resolved: resolveEvidence(link, projectRoot) }));
}
