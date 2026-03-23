import fs from 'fs';
import path from 'path';
import { EvidenceLink, parseEvidenceLinks } from './parser.js';
import { verifyAllLinks } from './resolver.js';

export interface ScopeDriftReport {
  scope: string;
  scopePath: string;
  totalLinks: number;
  validLinks: number;
  healedLinks: number;
  staleLinks: number;
  healthPct: number;
  staleItems: Array<{ link: EvidenceLink; reason: string }>;
  healedItems: Array<{ link: EvidenceLink; newStart: number; newEnd: number }>;
}

export interface DriftReport {
  timestamp: string;
  projectRoot: string;
  scopes: ScopeDriftReport[];
  overallHealthPct: number;
  totalLinks: number;
  validLinks: number;
  ciPass: boolean;
  ciThreshold: number;
}

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

// Heal stale links by updating line ranges based on AST resolution
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
