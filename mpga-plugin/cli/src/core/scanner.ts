import fs from 'fs';
import path from 'path';
import fg from 'fast-glob';

export interface FileInfo {
  filepath: string;
  lines: number;
  language: string;
  size: number;
}

export interface ScanResult {
  root: string;
  files: FileInfo[];
  totalFiles: number;
  totalLines: number;
  languages: Record<string, { files: number; lines: number }>;
  entryPoints: string[];
  topLevelDirs: string[];
}

const LANGUAGE_MAP: Record<string, string> = {
  ts: 'typescript',
  tsx: 'typescript',
  js: 'javascript',
  jsx: 'javascript',
  mjs: 'javascript',
  cjs: 'javascript',
  py: 'python',
  go: 'go',
  rs: 'rust',
  java: 'java',
  cs: 'csharp',
  rb: 'ruby',
  php: 'php',
  swift: 'swift',
  kt: 'kotlin',
  sh: 'shell',
  bash: 'shell',
  sql: 'sql',
  md: 'markdown',
  json: 'json',
  yaml: 'yaml',
  yml: 'yaml',
  toml: 'toml',
};

const ENTRY_PATTERNS = [
  'src/index.*',
  'src/main.*',
  'index.*',
  'main.*',
  'app.*',
  'server.*',
  'cmd/main.*',
];

export function detectLanguage(filepath: string): string {
  const ext = path.extname(filepath).slice(1).toLowerCase();
  return LANGUAGE_MAP[ext] ?? 'other';
}

export function countLines(filepath: string): number {
  try {
    const content = fs.readFileSync(filepath, 'utf-8');
    return content.split('\n').length;
  } catch {
    return 0;
  }
}

export async function scan(
  projectRoot: string,
  ignore: string[],
  deep = false,
): Promise<ScanResult> {
  const ignorePatterns = ignore.map((p) => `**/${p}/**`).concat(ignore);

  const globs = deep
    ? ['**/*.{ts,tsx,js,jsx,mjs,cjs,py,go,rs,java,cs,rb,php,swift,kt,sh,sql}']
    : ['**/*.{ts,tsx,js,jsx,mjs,cjs,py,go,rs,java,cs,rb,php,swift,kt,sh,sql}'];

  const rawFiles = await fg(globs, {
    cwd: projectRoot,
    ignore: ignorePatterns,
    onlyFiles: true,
    absolute: false,
  });

  const files: FileInfo[] = rawFiles.map((rel) => {
    const abs = path.join(projectRoot, rel);
    const lines = countLines(abs);
    const language = detectLanguage(rel);
    const size = fs.statSync(abs).size;
    return { filepath: rel, lines, language, size };
  });

  const languages: Record<string, { files: number; lines: number }> = {};
  for (const f of files) {
    if (!languages[f.language]) languages[f.language] = { files: 0, lines: 0 };
    languages[f.language].files++;
    languages[f.language].lines += f.lines;
  }

  const totalLines = files.reduce((s, f) => s + f.lines, 0);

  // Detect entry points
  const entryPoints: string[] = [];
  for (const pattern of ENTRY_PATTERNS) {
    const matches = await fg(pattern, { cwd: projectRoot, onlyFiles: true });
    entryPoints.push(...matches);
  }

  // Top-level dirs
  const topLevelDirs = fs.existsSync(projectRoot)
    ? fs
        .readdirSync(projectRoot, { withFileTypes: true })
        .filter((e) => e.isDirectory() && !ignore.includes(e.name) && !e.name.startsWith('.'))
        .map((e) => e.name)
    : [];

  return {
    root: projectRoot,
    files,
    totalFiles: files.length,
    totalLines,
    languages,
    entryPoints: [...new Set(entryPoints)],
    topLevelDirs,
  };
}

export function detectProjectType(scanResult: ScanResult): string {
  const { languages, files } = scanResult;
  const hasFile = (pattern: string) => files.some((f) => f.filepath.includes(pattern));

  if (languages.typescript && hasFile('next.config')) return 'Next.js';
  if (languages.typescript && hasFile('react')) return 'React';
  if (languages.typescript && (hasFile('express') || hasFile('fastify') || hasFile('koa')))
    return 'Node.js API';
  if (languages.typescript) return 'TypeScript';
  if (languages.python && hasFile('django')) return 'Django';
  if (languages.python && hasFile('fastapi')) return 'FastAPI';
  if (languages.python && hasFile('flask')) return 'Flask';
  if (languages.python) return 'Python';
  if (languages.go) return 'Go';
  if (languages.rust) return 'Rust';
  if (languages.java) return 'Java';
  return 'Unknown';
}

export function getTopLanguage(scanResult: ScanResult): string {
  const { languages } = scanResult;
  let topLang = 'unknown';
  let topLines = 0;
  for (const [lang, stats] of Object.entries(languages)) {
    if (stats.lines > topLines) {
      topLines = stats.lines;
      topLang = lang;
    }
  }
  return topLang;
}
