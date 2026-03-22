import fs from 'fs';
import path from 'path';
import { ScanResult } from '../core/scanner.js';
import { MpgaConfig } from '../core/config.js';

export interface Dependency {
  from: string;
  to: string;
}

export interface GraphData {
  dependencies: Dependency[];
  circular: Array<[string, string]>;
  orphans: string[];
  modules: string[];
}

// Extract imports from a file using regex (fast, no AST needed for basic graph)
function extractImports(filepath: string, content: string, projectRoot: string): string[] {
  const imports: string[] = [];
  // TypeScript/JS: import ... from '...' or require('...')
  const importRe = /(?:import\s+(?:.+?\s+from\s+)?['"]([^'"]+)['"]|require\(['"]([^'"]+)['"]\))/g;
  let m;
  while ((m = importRe.exec(content)) !== null) {
    const dep = m[1] ?? m[2];
    if (dep && dep.startsWith('.')) {
      // Relative import — resolve to a module name
      const resolved = path.resolve(path.dirname(path.join(projectRoot, filepath)), dep);
      const rel = path.relative(projectRoot, resolved);
      imports.push(rel);
    }
  }
  // Python: from . import or import
  const pyImportRe = /^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))/gm;
  while ((m = pyImportRe.exec(content)) !== null) {
    const dep = m[1] ?? m[2];
    if (dep) imports.push(dep);
  }
  return imports;
}

/**
 * Resolve a filepath to its scope/module name using the same logic as groupIntoScopes.
 * This keeps the graph consistent with scope documents.
 */
function getModuleName(filepath: string, scopeDepth: number | 'auto' = 'auto'): string {
  const parts = filepath.split('/');
  if (parts.length <= 1) return path.basename(filepath, path.extname(filepath));

  if (scopeDepth === 'auto') {
    const srcLike = ['src', 'lib', 'app', 'pkg', 'internal', 'cmd'];
    let srcIdx = -1;
    for (let i = 0; i < parts.length; i++) {
      if (srcLike.includes(parts[i])) srcIdx = i;
    }
    if (srcIdx >= 0 && srcIdx + 1 < parts.length - 1) {
      return parts[srcIdx + 1];
    }
    return parts[0];
  }

  const depth = Math.min(scopeDepth, parts.length - 1);
  return parts.slice(0, depth).join('/');
}

export async function buildGraph(scanResult: ScanResult, config?: MpgaConfig): Promise<GraphData> {
  const { root, files } = scanResult;
  const scopeDepth = config?.scopes?.scopeDepth ?? 'auto';
  const moduleDeps = new Map<string, Set<string>>();
  const modules = new Set<string>();

  for (const file of files) {
    const mod = getModuleName(file.filepath, scopeDepth);
    modules.add(mod);
    if (!moduleDeps.has(mod)) moduleDeps.set(mod, new Set());

    const fullPath = path.join(root, file.filepath);
    if (!fs.existsSync(fullPath)) continue;

    let content: string;
    try {
      content = fs.readFileSync(fullPath, 'utf-8');
    } catch {
      continue;
    }

    const imports = extractImports(file.filepath, content, root);
    for (const imp of imports) {
      const impMod = getModuleName(imp, scopeDepth);
      if (impMod && impMod !== mod) {
        moduleDeps.get(mod)!.add(impMod);
      }
    }
  }

  // Build dependency list
  const dependencies: Dependency[] = [];
  for (const [from, tos] of moduleDeps.entries()) {
    for (const to of tos) {
      if (modules.has(to)) {
        dependencies.push({ from, to });
      }
    }
  }

  // Detect circular deps (simple DFS)
  const circular: Array<[string, string]> = [];
  for (const { from, to } of dependencies) {
    // Check if there's also a to→from path
    const reverse = dependencies.some(d => d.from === to && d.to === from);
    if (reverse) {
      const already = circular.some(([a, b]) => (a === to && b === from) || (a === from && b === to));
      if (!already) circular.push([from, to]);
    }
  }

  // Find orphans (files with no imports and no importers)
  const hasImporters = new Set(dependencies.map(d => d.to));
  const hasImports = new Set(dependencies.map(d => d.from));
  const orphans = files
    .filter(f => {
      const mod = f.filepath; // use exact filepath for orphan detection
      return !hasImporters.has(path.basename(mod, path.extname(mod))) &&
             !hasImports.has(path.basename(mod, path.extname(mod)));
    })
    .slice(0, 10) // cap to avoid huge lists
    .map(f => f.filepath);

  return { dependencies, circular, orphans, modules: [...modules] };
}

export function renderGraphMd(graph: GraphData): string {
  const lines: string[] = ['# Dependency graph', ''];

  lines.push('## Module dependencies', '');
  if (graph.dependencies.length === 0) {
    lines.push('(no inter-module dependencies detected)');
  } else {
    for (const { from, to } of graph.dependencies) {
      lines.push(`${from} → ${to}`);
    }
  }

  lines.push('', '## Circular dependencies');
  if (graph.circular.length === 0) {
    lines.push('(none detected)');
  } else {
    for (const [a, b] of graph.circular) {
      lines.push(`⚠ ${a} ↔ ${b}`);
    }
  }

  lines.push('', '## Orphan modules');
  if (graph.orphans.length === 0) {
    lines.push('(none detected)');
  } else {
    for (const o of graph.orphans) lines.push(`- ${o}`);
  }

  lines.push('', '## Mermaid export', '```mermaid', 'graph TD');
  if (graph.dependencies.length === 0) {
    lines.push('    (no dependencies)');
  } else {
    const seen = new Set<string>();
    for (const { from, to } of graph.dependencies.slice(0, 30)) {
      const key = `${from}-->${to}`;
      if (!seen.has(key)) {
        seen.add(key);
        lines.push(`    ${from.replace(/[^a-zA-Z0-9_]/g, '_')} --> ${to.replace(/[^a-zA-Z0-9_]/g, '_')}`);
      }
    }
  }
  lines.push('```', '');

  return lines.join('\n');
}
