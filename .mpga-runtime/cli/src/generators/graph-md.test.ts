import { describe, it, expect } from 'vitest';
import { buildGraph } from './graph-md.js';
import type { ScanResult } from '../core/scanner.js';
import { DEFAULT_CONFIG } from '../core/config.js';

function scanFixture(files: ScanResult['files']): ScanResult {
  const totalLines = files.reduce((s, f) => s + f.lines, 0);
  return {
    root: '/proj',
    files,
    totalFiles: files.length,
    totalLines,
    languages: { typescript: { files: files.length, lines: totalLines } },
    entryPoints: [],
    topLevelDirs: ['src'],
  };
}

describe('buildGraph', () => {
  it('does not mark files in imported modules as orphans', async () => {
    const scan = scanFixture([
      {
        filepath: 'src/api/handler.ts',
        lines: 10,
        language: 'typescript',
        size: 100,
      },
      {
        filepath: 'src/core/util.ts',
        lines: 5,
        language: 'typescript',
        size: 50,
      },
    ]);

    const { writeFileSync, mkdirSync, rmSync } = await import('fs');
    const { join } = await import('path');
    const { tmpdir } = await import('os');
    const tmp = join(tmpdir(), `mpga-graph-${Date.now()}`);
    mkdirSync(join(tmp, 'src', 'api'), { recursive: true });
    mkdirSync(join(tmp, 'src', 'core'), { recursive: true });
    writeFileSync(
      join(tmp, 'src/api/handler.ts'),
      `import { help } from '../core/util';\nexport const x = help;\n`,
    );
    writeFileSync(join(tmp, 'src/core/util.ts'), `export function help() { return 1; }\n`);

    const localScan: ScanResult = { ...scan, root: tmp };

    const graph = await buildGraph(localScan, {
      ...DEFAULT_CONFIG,
      project: { ...DEFAULT_CONFIG.project, ignore: [] },
    });

    expect(graph.orphans).not.toContain('src/core/util.ts');

    rmSync(tmp, { recursive: true, force: true });
  });

  it('lists files only in modules with no graph edges as orphans', async () => {
    const { writeFileSync, mkdirSync, rmSync } = await import('fs');
    const { join } = await import('path');
    const { tmpdir } = await import('os');
    const tmp = join(tmpdir(), `mpga-graph-iso-${Date.now()}`);
    mkdirSync(join(tmp, 'src', 'island'), { recursive: true });
    writeFileSync(join(tmp, 'src/island/alone.ts'), `export const solo = 1;\n`);

    const localScan = scanFixture([
      { filepath: 'src/island/alone.ts', lines: 2, language: 'typescript', size: 20 },
    ]);
    const fullScan: ScanResult = { ...localScan, root: tmp };

    const graph = await buildGraph(fullScan, {
      ...DEFAULT_CONFIG,
      project: { ...DEFAULT_CONFIG.project, ignore: [] },
    });
    expect(graph.orphans).toContain('src/island/alone.ts');

    rmSync(tmp, { recursive: true, force: true });
  });
});
