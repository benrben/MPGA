import fs from 'fs';
import path from 'path';
import { ScanResult, detectProjectType, getTopLanguage } from '../core/scanner.js';
import { MpgaConfig } from '../core/config.js';
import { ScopeInfo } from './scope-md.js';

export function renderIndexMd(
  scanResult: ScanResult,
  config: MpgaConfig,
  scopes: ScopeInfo[],
  activeMilestone: string | null,
  evidenceCoverage: number
): string {
  const now = new Date().toISOString();
  const projectType = detectProjectType(scanResult);
  const { totalFiles, totalLines, languages } = scanResult;

  const langSummary = Object.entries(languages)
    .sort((a, b) => b[1].lines - a[1].lines)
    .map(([lang, stats]) => `${lang} (${Math.round((stats.lines / totalLines) * 100)}%)`)
    .join(', ');

  const lines: string[] = [];

  lines.push(`# Project: ${config.project.name}`, '');
  lines.push('## Identity');
  lines.push(`- **Type:** ${projectType}`);
  lines.push(`- **Size:** ~${totalLines.toLocaleString()} lines across ${totalFiles} files`);
  lines.push(`- **Languages:** ${langSummary}`);
  lines.push(`- **Last sync:** ${now}`);
  lines.push(`- **Evidence coverage:** ${Math.round(evidenceCoverage * 100)}% (target: ${Math.round(config.evidence.coverageThreshold * 100)}%)`);
  lines.push('');

  // Key files table — top 10 by size
  lines.push('## Key files');
  lines.push('| File | Role | Evidence |');
  lines.push('|------|------|----------|');
  const roleMap = config.knowledgeLayer?.keyFileRoles ?? {};
  const topFiles = [...scanResult.files].sort((a, b) => b.lines - a.lines).slice(0, 10);
  for (const f of topFiles) {
    const role = roleMap[f.filepath] ?? '(describe role)';
    lines.push(`| ${f.filepath} | ${role} | [E] ${f.filepath}:1-${Math.min(50, f.lines)} |`);
  }
  lines.push('');

  lines.push('## Conventions');
  const customConventions = config.knowledgeLayer?.conventions?.filter((c) => c.trim().length > 0);
  if (customConventions && customConventions.length > 0) {
    for (const c of customConventions) {
      lines.push(`- ${c}`);
    }
  } else {
    lines.push('- (Add your project conventions here)');
    lines.push('- (e.g. "All API routes follow REST naming: /api/v1/<resource>")');
  }
  lines.push('');

  lines.push('## Agent trigger table');
  lines.push('| Task pattern | Agent | Scopes to load |');
  lines.push('|-------------|-------|-----------------|');
  lines.push('| "add/modify authentication" | green-dev → red-dev → blue-dev | auth, database |');
  lines.push('| "explore how X works" | scout | (auto-detect) |');
  lines.push('| "plan feature X" | researcher → architect | (auto-detect) |');
  lines.push('| "fix bug in X" | scout → green-dev → red-dev | (auto-detect) |');
  lines.push('| "refactor X" | architect → blue-dev | (auto-detect) |');
  lines.push('');

  lines.push('## Scope registry');
  lines.push('| Scope | Status | Evidence links | Last verified |');
  lines.push('|-------|--------|---------------|---------------|');
  const today = now.split('T')[0];
  for (const scope of scopes) {
    lines.push(`| ${scope.name} | ✓ fresh | 0/${scope.exports.length} | ${today} |`);
  }
  lines.push('');

  lines.push('## Active milestone');
  lines.push(`- ${activeMilestone ?? '(none)'}`);
  lines.push('');

  lines.push('## Known unknowns');
  lines.push('- [ ] (run `mpga evidence verify` to detect unknowns)');

  return lines.join('\n') + '\n';
}
