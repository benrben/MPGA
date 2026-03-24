import fs from 'fs';
import path from 'path';

export interface SymbolLocation {
  name: string;
  type: 'function' | 'class' | 'method' | 'variable' | 'type';
  startLine: number;
  endLine: number;
}

/** Maximum number of lines to scan forward when finding the end of a code block. */
const MAX_BLOCK_SCAN_LINES = 200;

// Language detection by file extension
export function detectLanguage(filepath: string): string {
  const ext = path.extname(filepath).toLowerCase();
  const map: Record<string, string> = {
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.mjs': 'javascript',
    '.py': 'python',
    '.go': 'go',
    '.rs': 'rust',
    '.java': 'java',
    '.cs': 'csharp',
    '.rb': 'ruby',
    '.php': 'php',
  };
  return map[ext] ?? 'unknown';
}

// Regex-based symbol extraction (fast fallback for all languages)
function extractSymbolsRegex(content: string, language: string): SymbolLocation[] {
  const lines = content.split('\n');
  const symbols: SymbolLocation[] = [];

  const patterns: Array<{ re: RegExp; type: SymbolLocation['type']; langs: string[] }> = [
    // TypeScript/JavaScript
    {
      re: /^(?:export\s+)?(?:async\s+)?function\s+(\w+)/,
      type: 'function',
      langs: ['typescript', 'javascript'],
    },
    {
      re: /^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)/,
      type: 'class',
      langs: ['typescript', 'javascript'],
    },
    {
      re: /^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(/,
      type: 'function',
      langs: ['typescript', 'javascript'],
    },
    {
      re: /^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function/,
      type: 'function',
      langs: ['typescript', 'javascript'],
    },
    {
      re: /^(?:export\s+)?(?:const|let|var)\s+(\w+)/,
      type: 'variable',
      langs: ['typescript', 'javascript'],
    },
    {
      re: /^(?:export\s+)?(?:type|interface)\s+(\w+)/,
      type: 'type',
      langs: ['typescript', 'javascript'],
    },
    // Method patterns (inside class)
    {
      re: /^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*(?::\s*\w+\s*)?{/,
      type: 'method',
      langs: ['typescript', 'javascript'],
    },
    // Python
    { re: /^def\s+(\w+)/, type: 'function', langs: ['python'] },
    { re: /^class\s+(\w+)/, type: 'class', langs: ['python'] },
    { re: /^\s{4}def\s+(\w+)/, type: 'method', langs: ['python'] },
    // Go
    { re: /^func\s+(?:\([^)]+\)\s+)?(\w+)/, type: 'function', langs: ['go'] },
    { re: /^type\s+(\w+)\s+struct/, type: 'class', langs: ['go'] },
    { re: /^type\s+(\w+)\s+interface/, type: 'type', langs: ['go'] },
    // Rust
    { re: /^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)/, type: 'function', langs: ['rust'] },
    { re: /^(?:pub\s+)?struct\s+(\w+)/, type: 'class', langs: ['rust'] },
    { re: /^(?:pub\s+)?trait\s+(\w+)/, type: 'type', langs: ['rust'] },
    // Java/C#
    {
      re: /(?:public|private|protected|static|\s)+\w+\s+(\w+)\s*\(/,
      type: 'function',
      langs: ['java', 'csharp'],
    },
    {
      re: /(?:public|private|protected)?\s+(?:abstract\s+)?class\s+(\w+)/,
      type: 'class',
      langs: ['java', 'csharp'],
    },
    { re: /(?:public\s+)?interface\s+(\w+)/, type: 'type', langs: ['java', 'csharp'] },
  ];

  const relevantPatterns = patterns.filter((p) => p.langs.includes(language));

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    for (const { re, type } of relevantPatterns) {
      const m = re.exec(line);
      if (m && m[1] && !m[1].match(/^(if|for|while|switch|return|const|let|var)$/)) {
        // Find end of block (simple heuristic: next same-indent line or end of file)
        let endLine = i + 1;
        const indent = line.match(/^(\s*)/)?.[1]?.length ?? 0;
        for (let j = i + 1; j < Math.min(i + MAX_BLOCK_SCAN_LINES, lines.length); j++) {
          const jLine = lines[j];
          if (jLine.trim() === '') continue;
          const jIndent = jLine.match(/^(\s*)/)?.[1]?.length ?? 0;
          if (jIndent <= indent && jLine.trim().length > 0 && j > i + 1) {
            endLine = j - 1;
            break;
          }
          endLine = j;
        }
        symbols.push({ name: m[1], type, startLine: i + 1, endLine: endLine + 1 });
        break;
      }
    }
  }

  return symbols;
}

export function extractSymbols(filepath: string, projectRoot: string): SymbolLocation[] {
  const fullPath = path.join(projectRoot, filepath);
  if (!fs.existsSync(fullPath)) return [];

  let content: string;
  try {
    content = fs.readFileSync(fullPath, 'utf-8');
  } catch {
    return [];
  }

  const language = detectLanguage(filepath);
  return extractSymbolsRegex(content, language);
}

export function findSymbol(
  filepath: string,
  symbolName: string,
  projectRoot: string,
): SymbolLocation | null {
  const symbols = extractSymbols(filepath, projectRoot);
  return symbols.find((s) => s.name === symbolName) ?? null;
}

// Verify that a line range contains the expected symbol
export function verifyRange(
  filepath: string,
  startLine: number,
  endLine: number,
  symbol: string | undefined,
  projectRoot: string,
): boolean {
  const fullPath = path.join(projectRoot, filepath);
  if (!fs.existsSync(fullPath)) return false;

  try {
    const lines = fs.readFileSync(fullPath, 'utf-8').split('\n');
    const rangeContent = lines.slice(startLine - 1, endLine).join('\n');
    if (!symbol) return true; // Range exists, no symbol check needed
    return rangeContent.includes(symbol);
  } catch {
    return false;
  }
}
