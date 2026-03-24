import fs from 'fs';
import path from 'path';
import { EvidenceLink, parseEvidenceLinks } from './parser.js';
import { verifyAllLinks } from './resolver.js';

/**
 * Drift report for a single scope file, summarizing evidence link health
 * and listing any stale or healed items found during verification.
 */
export interface ScopeDriftReport {
  /** Name of the scope (derived from the filename without extension) */
  scope: string;
  /** Absolute path to the scope markdown file */
  scopePath: string;
  /** Total number of evidence links checked in this scope */
  totalLinks: number;
  /** Number of links whose targets were found exactly as specified */
  validLinks: number;
  /** Number of links that were stale but could be auto-healed via AST lookup */
  healedLinks: number;
  /** Number of links whose targets could not be resolved */
  staleLinks: number;
  /** Health percentage: (valid + healed) / total * 100 */
  healthPct: number;
  /** Links that could not be resolved, with the reason for failure */
  staleItems: Array<{ link: EvidenceLink; reason: string }>;
  /** Links that were healed, with updated line ranges */
  healedItems: Array<{ link: EvidenceLink; newStart: number; newEnd: number }>;
}

/**
 * Aggregate drift report across all scopes in a project, including
 * overall health metrics and CI pass/fail status.
 */
export interface DriftReport {
  /** ISO timestamp of when the drift check was performed */
  timestamp: string;
  /** Absolute path to the project root directory */
  projectRoot: string;
  /** Per-scope drift reports */
  scopes: ScopeDriftReport[];
  /** Overall health percentage across all scopes */
  overallHealthPct: number;
  /** Total number of evidence links across all scopes */
  totalLinks: number;
  /** Total number of valid (including healed) links across all scopes */
  validLinks: number;
  /** Whether the overall health meets or exceeds the CI threshold */
  ciPass: boolean;
  /** The minimum health percentage required for CI to pass */
  ciThreshold: number;
}

/**
 * Runs a drift check across all scope files in the project, verifying that
 * evidence links still point to valid code locations.
 *
 * @param projectRoot - Absolute path to the project root directory
 * @param ciThreshold - Minimum health percentage (0-100) required for CI to pass
 * @param scopeFilter - Optional scope name to limit the check to a single scope file
 * @returns A DriftReport containing per-scope results and aggregate health metrics
 */
export async function runDriftCheck(
  projectRoot: string,
  ciThreshold: number,
  scopeFilter?: string,
): Promise<DriftReport> {
  const mpgaDir = path.join(projectRoot, 'MPGA');
  const scopesDir = path.join(mpgaDir, 'scopes');

  const now = new Date().toISOString();
  const reports: ScopeDriftReport[] = [];

  if (!fs.existsSync(scopesDir)) {
    return {
      timestamp: now,
      projectRoot,
      scopes: [],
      overallHealthPct: 100,
      totalLinks: 0,
      validLinks: 0,
      ciPass: true,
      ciThreshold,
    };
  }

  const scopeFiles = fs
    .readdirSync(scopesDir)
    .filter((f) => f.endsWith('.md'))
    .filter((f) => !scopeFilter || f === `${scopeFilter}.md`);

  for (const scopeFile of scopeFiles) {
    const scopeName = scopeFile.replace('.md', '');
    const scopePath = path.join(scopesDir, scopeFile);
    const content = fs.readFileSync(scopePath, 'utf-8');
    const links = parseEvidenceLinks(content).filter(
      (l) => l.type === 'valid' || l.type === 'stale',
    );

    const results = verifyAllLinks(links, projectRoot);

    const valid = results.filter((r) => r.resolved.status === 'valid').length;
    const healed = results.filter((r) => r.resolved.status === 'healed').length;
    const stale = results.filter((r) => r.resolved.status === 'stale').length;
    const total = results.length;
    const healthPct = total === 0 ? 100 : Math.round(((valid + healed) / total) * 100);

    const staleItems = results
      .filter((r) => r.resolved.status === 'stale')
      .map((r) => {
        const fullPath = r.link.filepath ? path.join(projectRoot, r.link.filepath) : null;
        const fileExists = fullPath ? fs.existsSync(fullPath) : false;
        const reason = !r.link.filepath
          ? 'No filepath in evidence link'
          : !fileExists
            ? `File not found: ${r.link.filepath}`
            : `Symbol not found in file`;
        return { link: r.link, reason };
      });

    const healedItems = results
      .filter((r) => r.resolved.status === 'healed')
      .map((r) => ({
        link: r.link,
        newStart: r.resolved.startLine ?? 0,
        newEnd: r.resolved.endLine ?? 0,
      }));

    reports.push({
      scope: scopeName,
      scopePath,
      totalLinks: total,
      validLinks: valid,
      healedLinks: healed,
      staleLinks: stale,
      healthPct,
      staleItems,
      healedItems,
    });
  }

  const totalLinks = reports.reduce((s, r) => s + r.totalLinks, 0);
  const validLinks = reports.reduce((s, r) => s + r.validLinks + r.healedLinks, 0);
  const overallHealthPct = totalLinks === 0 ? 100 : Math.round((validLinks / totalLinks) * 100);

  return {
    timestamp: now,
    projectRoot,
    scopes: reports,
    overallHealthPct,
    totalLinks,
    validLinks,
    ciPass: overallHealthPct >= ciThreshold,
    ciThreshold,
  };
}

/**
 * Heals stale evidence links in a scope file by replacing their line ranges
 * with updated values determined by AST resolution.
 *
 * @param report - The ScopeDriftReport containing healed items with updated line ranges
 * @returns An object with `healed` (number of links successfully updated) and `content` (the updated file content)
 */
export function healScopeFile(report: ScopeDriftReport): { healed: number; content: string } {
  const content = fs.readFileSync(report.scopePath, 'utf-8');
  let updated = content;
  let healed = 0;

  // Sort by symbol length descending to prevent shorter symbols from matching inside longer ones
  const sortedItems = [...report.healedItems].sort(
    (a, b) => (b.link.symbol?.length ?? 0) - (a.link.symbol?.length ?? 0),
  );
  for (const item of sortedItems) {
    const newLink = `[E] ${item.link.filepath}:${item.newStart}-${item.newEnd}${item.link.symbol ? ` :: ${item.link.symbol}()` : ''}`;
    // Match the original evidence link in the file, accounting for markdown table pipes and backticks
    if (!item.link.filepath) continue;
    const fp = item.link.filepath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const sym = item.link.symbol ? item.link.symbol.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') : null;
    const rangePattern =
      item.link.startLine && item.link.endLine
        ? `:${item.link.startLine}-${item.link.endLine}`
        : '(?::\\d+-\\d+)?';
    const symPattern = sym ? `\\s*::\\s*${sym}\\s*(?:\\(\\))?` : '(?:\\s*::\\s*\\S+(?:\\(\\))?)?';
    const re = new RegExp(`\\[E\\]\\s+\`?${fp}\`?${rangePattern}${symPattern}`);
    const match = re.exec(updated);
    if (match) {
      updated = updated.replace(match[0], newLink);
      healed++;
    }
  }

  return { healed, content: updated };
}
