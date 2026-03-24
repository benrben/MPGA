import fs from 'fs';
import path from 'path';
import { ScanResult, FileInfo } from '../core/scanner.js';
import { GraphData } from './graph-md.js';
import { MpgaConfig } from '../core/config.js';

export interface ScopeInfo {
  name: string;
  files: FileInfo[];
  exports: Array<{ symbol: string; filepath: string; kind: string }>;
  dependencies: string[];
  reverseDeps: string[];
  entryPoints: string[];
  allScopeNames: string[];
  /** Module-level comments extracted from entry point files */
  moduleSummaries: Array<{ filepath: string; summary: string }>;
  /** Frameworks/libraries detected from imports */
  detectedFrameworks: string[];
  /** Exported functions with their JSDoc descriptions */
  exportDescriptions: Array<{
    symbol: string;
    filepath: string;
    kind: string;
    description: string;
  }>;
  /** JSDoc annotations: @throws, @deprecated, etc. */
  rulesAndConstraints: Array<{ filepath: string; symbol: string; annotation: string }>;
}

interface ExportedSymbol {
  symbol: string;
  filepath: string;
  kind: string;
}

// Extract exported symbols with their kind
function extractExports(filepath: string, content: string): ExportedSymbol[] {
  const exports: ExportedSymbol[] = [];
  const seen = new Set<string>();

  // TypeScript/JS exports
  const tsRe =
    /export\s+(?:default\s+)?(?:async\s+)?(function|class|const|let|var|type|interface|enum)\s+(\w+)/g;
  let m;
  while ((m = tsRe.exec(content)) !== null) {
    const kind = m[1] === 'let' || m[1] === 'var' ? 'variable' : m[1];
    if (!seen.has(m[2])) {
      seen.add(m[2]);
      exports.push({ symbol: m[2], filepath, kind });
    }
  }

  // Python def/class at module level
  const pyRe = /^(def|class)\s+(\w+)/gm;
  while ((m = pyRe.exec(content)) !== null) {
    if (!seen.has(m[2])) {
      seen.add(m[2]);
      exports.push({ symbol: m[2], filepath, kind: m[1] });
    }
  }

  // Go func
  const goRe = /^func\s+(\w+)/gm;
  while ((m = goRe.exec(content)) !== null) {
    if (!seen.has(m[1])) {
      seen.add(m[1]);
      exports.push({ symbol: m[1], filepath, kind: 'function' });
    }
  }

  return exports;
}

// Known frameworks/libraries to detect from imports
const FRAMEWORK_MAP: Record<string, string> = {
  express: 'Express',
  fastify: 'Fastify',
  hono: 'Hono',
  koa: 'Koa',
  react: 'React',
  'react-dom': 'React',
  vue: 'Vue',
  svelte: 'Svelte',
  next: 'Next.js',
  nuxt: 'Nuxt',
  angular: 'Angular',
  commander: 'Commander',
  yargs: 'Yargs',
  inquirer: 'Inquirer',
  zod: 'Zod',
  joi: 'Joi',
  ajv: 'Ajv',
  prisma: 'Prisma',
  drizzle: 'Drizzle',
  typeorm: 'TypeORM',
  sequelize: 'Sequelize',
  vitest: 'Vitest',
  jest: 'Jest',
  mocha: 'Mocha',
  tailwindcss: 'Tailwind CSS',
  'styled-components': 'styled-components',
  graphql: 'GraphQL',
  trpc: 'tRPC',
  axios: 'Axios',
  mongoose: 'Mongoose',
  knex: 'Knex',
  flask: 'Flask',
  django: 'Django',
  fastapi: 'FastAPI',
};

/** Extract the leading module-level comment (JSDoc or // block) from file content */
export function extractModuleSummary(content: string): string | null {
  // Try JSDoc block comment at the top (before any import/code)
  const jsdocMatch = content.match(/^\s*\/\*\*([\s\S]*?)\*\//);
  if (jsdocMatch) {
    const beforeComment = content.slice(0, jsdocMatch.index ?? 0).trim();
    if (beforeComment === '') {
      const cleaned = jsdocMatch[1]
        .split('\n')
        .map((l) => l.replace(/^\s*\*\s?/, '').trim())
        .filter((l) => !l.startsWith('@') && l.length > 0)
        .join(' ')
        .trim();
      if (cleaned.length > 0) return cleaned;
    }
  }

  // Try leading // comment block
  const lines = content.split('\n');
  const commentLines: string[] = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed === '' && commentLines.length === 0) continue;
    if (trimmed.startsWith('//')) {
      commentLines.push(trimmed.replace(/^\/\/\s?/, '').trim());
    } else {
      break;
    }
  }
  if (commentLines.length > 0) {
    const joined = commentLines
      .filter((l) => l.length > 0)
      .join(' ')
      .trim();
    if (joined.length > 0) return joined;
  }

  return null;
}

/** Detect known frameworks/libraries from import statements */
export function detectFrameworks(content: string): string[] {
  const found = new Set<string>();
  const importRe = /(?:from|import|require)\s*\(?\s*['"]([^'"./][^'"]*)['"]/g;
  let m;
  while ((m = importRe.exec(content)) !== null) {
    // Get the package name (handle scoped packages like @foo/bar)
    const raw = m[1];
    const pkg = raw.startsWith('@') ? raw.split('/').slice(0, 2).join('/') : raw.split('/')[0];
    const framework = FRAMEWORK_MAP[pkg];
    if (framework) found.add(framework);
  }
  return [...found];
}

/** Extract JSDoc description for a specific exported symbol */
export function extractJSDocForExport(content: string, symbolName: string): string | null {
  // Match /** ... */ immediately before an export containing the symbol name
  const escaped = symbolName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(
    `/\\*\\*([\\s\\S]*?)\\*/\\s*export\\s+(?:default\\s+)?(?:async\\s+)?(?:function|class|const|let|var|type|interface|enum)\\s+${escaped}\\b`,
  );
  const match = content.match(re);
  if (!match) return null;

  const lines = match[1]
    .split('\n')
    .map((l) => l.replace(/^\s*\*\s?/, '').trim())
    .filter((l) => l.length > 0 && !l.startsWith('@'));

  return lines.length > 0 ? lines.join(' ').trim() : null;
}

/** Extract constraint annotations (@throws, @deprecated, @param with validation) from JSDoc */
export function extractAnnotations(content: string, symbolName: string): string[] {
  const escaped = symbolName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(
    `/\\*\\*([\\s\\S]*?)\\*/\\s*export\\s+(?:default\\s+)?(?:async\\s+)?(?:function|class|const|let|var|type|interface|enum)\\s+${escaped}\\b`,
  );
  const match = content.match(re);
  if (!match) return [];

  const annotations: string[] = [];
  const lines = match[1].split('\n').map((l) => l.replace(/^\s*\*\s?/, '').trim());
  for (const line of lines) {
    if (line.startsWith('@throws') || line.startsWith('@deprecated')) {
      annotations.push(line);
    }
  }
  return annotations;
}

// Detect entry-point files within a scope
function detectEntryPoints(files: FileInfo[]): string[] {
  const entryPatterns = [
    /(?:^|\/)index\.\w+$/,
    /(?:^|\/)main\.\w+$/,
    /(?:^|\/)app\.\w+$/,
    /(?:^|\/)server\.\w+$/,
    /(?:^|\/)cli\.\w+$/,
    /(?:^|\/)mod\.\w+$/,
    /(?:^|\/)lib\.\w+$/,
    /(?:^|\/)__init__\.py$/,
  ];
  const entries: string[] = [];
  for (const file of files) {
    if (entryPatterns.some((p) => p.test(file.filepath))) {
      entries.push(file.filepath);
    }
  }
  // If no conventional entry points, pick the largest files (likely the main ones)
  if (entries.length === 0 && files.length > 0) {
    const sorted = [...files].sort((a, b) => b.lines - a.lines);
    entries.push(sorted[0].filepath);
  }
  return entries;
}

/**
 * Determine the scope name for a file based on its path.
 * With scopeDepth='auto', finds the deepest "source-like" directory
 * (src/, lib/, core/, commands/, etc.) and uses its subdirectories as scopes.
 * With a numeric depth, uses that many path segments.
 */
export function getScopeName(filepath: string, scopeDepth: number | 'auto'): string {
  const parts = filepath.split('/');
  if (parts.length <= 1) return 'root';

  if (scopeDepth === 'auto') {
    // Find the deepest src-like directory and group by subdirectories under it
    const srcLike = ['src', 'lib', 'app', 'pkg', 'internal', 'cmd'];
    let srcIdx = -1;
    for (let i = 0; i < parts.length; i++) {
      if (srcLike.includes(parts[i])) srcIdx = i;
    }

    if (srcIdx >= 0 && srcIdx + 1 < parts.length - 1) {
      // Use the subdirectory under the src-like dir as the scope name
      // e.g. mpga-plugin/cli/src/evidence/parser.ts → "evidence"
      return parts[srcIdx + 1];
    }

    // No src-like dir found — use the top-level directory
    return parts[0];
  }

  // Numeric depth: use that many path segments
  const depth = Math.min(scopeDepth, parts.length - 1);
  return parts.slice(0, depth).join('/');
}

// Group files into scopes by directory structure
export function groupIntoScopes(
  scanResult: ScanResult,
  graph?: GraphData,
  config?: MpgaConfig,
): ScopeInfo[] {
  const { root, files } = scanResult;
  const groups = new Map<string, FileInfo[]>();
  const scopeDepth = config?.scopes?.scopeDepth ?? 'auto';

  for (const file of files) {
    const group = getScopeName(file.filepath, scopeDepth);
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group)!.push(file);
  }

  const allScopeNames = [...groups.keys()];

  // Build reverse dependency map from graph data
  const reverseDepsMap = new Map<string, Set<string>>();
  if (graph) {
    for (const dep of graph.dependencies) {
      if (!reverseDepsMap.has(dep.to)) reverseDepsMap.set(dep.to, new Set());
      reverseDepsMap.get(dep.to)!.add(dep.from);
    }
  }

  const scopes: ScopeInfo[] = [];
  for (const [name, groupFiles] of groups.entries()) {
    const allExports: ExportedSymbol[] = [];
    const deps = new Set<string>();
    const moduleSummaries: Array<{ filepath: string; summary: string }> = [];
    const allFrameworks: string[] = [];
    const exportDescriptions: Array<{
      symbol: string;
      filepath: string;
      kind: string;
      description: string;
    }> = [];
    const rulesAndConstraints: Array<{ filepath: string; symbol: string; annotation: string }> = [];

    // Compute entry points first so we can extract summaries from them
    const entryPoints = detectEntryPoints(groupFiles);
    const entryPointSet = new Set(entryPoints);

    for (const file of groupFiles) {
      const fullPath = path.join(root, file.filepath);
      if (!fs.existsSync(fullPath)) continue;
      let content: string;
      try {
        content = fs.readFileSync(fullPath, 'utf-8');
      } catch {
        continue;
      }

      const fileExports = extractExports(file.filepath, content);
      allExports.push(...fileExports);

      // Extract module summary from entry point files
      if (entryPointSet.has(file.filepath)) {
        const summary = extractModuleSummary(content);
        if (summary) moduleSummaries.push({ filepath: file.filepath, summary });
      }

      // Detect frameworks
      allFrameworks.push(...detectFrameworks(content));

      // Extract JSDoc descriptions and annotations for exports
      for (const exp of fileExports) {
        const desc = extractJSDocForExport(content, exp.symbol);
        if (desc)
          exportDescriptions.push({
            symbol: exp.symbol,
            filepath: exp.filepath,
            kind: exp.kind,
            description: desc,
          });
        const annotations = extractAnnotations(content, exp.symbol);
        for (const ann of annotations) {
          rulesAndConstraints.push({
            filepath: file.filepath,
            symbol: exp.symbol,
            annotation: ann,
          });
        }
      }

      // Detect inter-scope dependencies
      const importRe = /(?:from|import)\s+['"]([^'"]+)['"]/g;
      let m;
      while ((m = importRe.exec(content)) !== null) {
        const imp = m[1];
        if (!imp.startsWith('.')) continue;
        const resolved = path.relative(
          root,
          path.resolve(path.join(root, path.dirname(file.filepath)), imp),
        );
        const impGroup = getScopeName(resolved, scopeDepth);
        if (impGroup !== name && groups.has(impGroup)) deps.add(impGroup);
      }
    }

    const reverseDeps = reverseDepsMap.get(name) ? [...reverseDepsMap.get(name)!] : [];

    scopes.push({
      name,
      files: groupFiles,
      exports: allExports,
      dependencies: [...deps],
      reverseDeps,
      entryPoints,
      allScopeNames,
      moduleSummaries,
      detectedFrameworks: [...new Set(allFrameworks)],
      exportDescriptions,
      rulesAndConstraints,
    });
  }

  return scopes;
}

export function renderScopeMd(scope: ScopeInfo, _projectRoot: string): string {
  const now = new Date().toISOString().split('T')[0];
  const lines: string[] = [];

  // ── Summary ──
  lines.push(`# Scope: ${scope.name}`, '');
  lines.push('## Summary', '');
  lines.push(
    `The **${scope.name}** module — TREMENDOUS — ${scope.files.length} files, ${scope.files.reduce((s, f) => s + f.lines, 0).toLocaleString()} lines of the finest code you've ever seen. Believe me.`,
  );
  lines.push('');
  if (scope.moduleSummaries.length > 0) {
    for (const ms of scope.moduleSummaries) {
      lines.push(`${ms.summary}`);
    }
    lines.push('');
  } else {
    lines.push(
      '<!-- TODO: Tell the people what this GREAT module does. What\'s in, what\'s out. Keep it simple. MPGA! -->',
    );
    lines.push('');
  }

  // ── Where to start in code ──
  lines.push('## Where to start in code', '');
  if (scope.entryPoints.length > 0) {
    lines.push('These are your MAIN entry points — the best, the most important. Open them FIRST:', '');
    for (const ep of scope.entryPoints) {
      lines.push(`- [E] \`${ep}\``);
    }
  } else {
    lines.push('- <!-- TODO: Find the main entry points. The best ones. The ones everybody should be reading. -->');
  }
  lines.push('');

  // ── Context / stack / skills ──
  lines.push('## Context / stack / skills', '');
  const langSet = new Set(scope.files.map((f) => f.language));
  const langs = [...langSet].filter((l) => l !== 'other');
  if (langs.length > 0) {
    lines.push(`- **Languages:** ${langs.join(', ')}`);
  }
  const symbolKinds = new Set(scope.exports.map((e) => e.kind));
  if (symbolKinds.size > 0) {
    lines.push(`- **Symbol types:** ${[...symbolKinds].join(', ')}`);
  }
  if (scope.detectedFrameworks.length > 0) {
    lines.push(`- **Frameworks:** ${scope.detectedFrameworks.join(', ')}`);
  } else {
    lines.push('- <!-- TODO: List the frameworks. We use only the BEST. -->');
  }
  lines.push('');

  // ── Who and what triggers it ──
  lines.push('## Who and what triggers it', '');
  lines.push('<!-- TODO: Who triggers this? A lot of very important callers, believe me. Find them. -->', '');
  if (scope.reverseDeps.length > 0) {
    lines.push('**Called by these GREAT scopes (they need us, tremendously):**', '');
    for (const rd of scope.reverseDeps) {
      lines.push(`- ← ${rd}`);
    }
    lines.push('');
  }

  // ── What happens ──
  lines.push('## What happens', '');
  if (scope.exportDescriptions.length > 0) {
    for (const ed of scope.exportDescriptions) {
      lines.push(`- **${ed.symbol}** (${ed.kind}) — ${ed.description} [E] \`${ed.filepath}\``);
    }
    lines.push('');
  } else {
    lines.push(
      '<!-- TODO: What happens here? Inputs, steps, outputs. Keep it simple. Even Sleepy Copilot could understand. -->',
      '',
    );
  }

  // ── Rules and edge cases ──
  lines.push('## Rules and edge cases', '');
  if (scope.rulesAndConstraints.length > 0) {
    for (const rc of scope.rulesAndConstraints) {
      lines.push(`- \`${rc.symbol}\`: ${rc.annotation} [E] \`${rc.filepath}\``);
    }
    lines.push('');
  } else {
    lines.push(
      '<!-- TODO: The guardrails. Validation, permissions, error handling — everything that keeps this code GREAT. -->',
      '',
    );
  }

  // ── Concrete examples ──
  lines.push('## Concrete examples', '');
  lines.push('<!-- TODO: REAL examples. "When X happens, Y happens." Simple. Powerful. Like a deal. -->', '');

  // ── UI ──
  lines.push('## UI', '');
  lines.push(
    '<!-- TODO: Screens, flows, the beautiful UI. No UI? Cut this section. We don\'t keep dead weight. -->',
    '',
  );

  // ── Navigation ──
  lines.push('## Navigation', '');
  const siblings = scope.allScopeNames.filter((s) => s !== scope.name);
  if (siblings.length > 0) {
    lines.push('**Sibling scopes:**', '');
    for (const s of siblings) {
      lines.push(`- [${s}](./${s}.md)`);
    }
    lines.push('');
  }
  lines.push('**Parent:** [INDEX.md](../INDEX.md)', '');

  // ── Relationships to other areas ──
  lines.push('## Relationships', '');
  if (scope.dependencies.length > 0) {
    lines.push('**Depends on:**', '');
    for (const dep of scope.dependencies) {
      lines.push(`- → [${dep}](./${dep}.md)`);
    }
    lines.push('');
  }
  if (scope.reverseDeps.length > 0) {
    lines.push('**Depended on by:**', '');
    for (const rd of scope.reverseDeps) {
      lines.push(`- ← [${rd}](./${rd}.md)`);
    }
    lines.push('');
  }
  if (scope.dependencies.length === 0 && scope.reverseDeps.length === 0) {
    lines.push('- (no dependencies — TOTALLY INDEPENDENT. Very strong.)', '');
  }
  lines.push('<!-- TODO: What deals does this scope make with other scopes? Document them. -->', '');

  // ── Diagram ──
  lines.push('## Diagram', '');
  if (scope.dependencies.length > 0 || scope.reverseDeps.length > 0) {
    lines.push('```mermaid');
    lines.push('graph LR');
    const safeName = (n: string) => n.replace(/[^a-zA-Z0-9_]/g, '_');
    for (const dep of scope.dependencies) {
      lines.push(`    ${safeName(scope.name)} --> ${safeName(dep)}`);
    }
    for (const rd of scope.reverseDeps) {
      lines.push(`    ${safeName(rd)} --> ${safeName(scope.name)}`);
    }
    lines.push('```');
  } else {
    lines.push(
      '<!-- TODO: A BEAUTIFUL diagram. Flow, sequence, boundaries. Make it GREAT. -->',
    );
  }
  lines.push('');

  // ── Traces ──
  lines.push('## Traces', '');
  lines.push('<!-- TODO: Step-by-step traces. Follow the code like a WINNER follows a deal. Use this table:', '');
  lines.push('| Step | Layer | What happens | Evidence |');
  lines.push('|------|-------|-------------|----------|');
  lines.push('| 1 | (layer) | (description) | [E] file:line |');
  lines.push('-->', '');

  // ── Evidence index ──
  lines.push('## Evidence index', '');
  if (scope.exports.length > 0) {
    lines.push('| Claim | Evidence |');
    lines.push('|-------|----------|');
    for (const exp of scope.exports.slice(0, 40)) {
      lines.push(`| \`${exp.symbol}\` (${exp.kind}) | [E] ${exp.filepath} :: ${exp.symbol} |`);
    }
    if (scope.exports.length > 40) {
      lines.push(`| ... | ${scope.exports.length - 40} more symbols |`);
    }
  } else {
    lines.push('- (no exports detected — working behind the scenes. Very mysterious.)');
  }
  lines.push('');

  // ── Files ──
  lines.push('## Files', '');
  for (const file of scope.files.slice(0, 30)) {
    lines.push(`- \`${file.filepath}\` (${file.lines} lines, ${file.language})`);
  }
  if (scope.files.length > 30) lines.push(`- ... and ${scope.files.length - 30} more files`);
  lines.push('');

  // ── Deeper splits ──
  lines.push('## Deeper splits', '');
  lines.push(
    '<!-- TODO: Too big? Split it. Make each piece LEAN and GREAT. -->',
    '',
  );

  // ── Confidence and notes ──
  lines.push('## Confidence and notes', '');
  lines.push(`- **Confidence:** LOW (for now) — auto-generated, not yet verified. But it's going to be PERFECT.`);
  lines.push(`- **Evidence coverage:** 0/${scope.exports.length} verified`);
  lines.push(`- **Last verified:** ${now}`);
  lines.push(`- **Drift risk:** unknown`);
  lines.push('- <!-- TODO: Note anything unknown or ambiguous. We don\'t hide problems — we FIX them. -->', '');

  // ── Change history ──
  lines.push('## Change history', '');
  lines.push(`- ${now}: Initial scope generation via \`mpga sync\` — Making this scope GREAT!`);

  return lines.join('\n');
}
