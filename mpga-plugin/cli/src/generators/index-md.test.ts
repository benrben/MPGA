import { describe, it, expect } from 'vitest';
import { renderIndexMd } from './index-md.js';
import { DEFAULT_CONFIG, type MpgaConfig } from '../core/config.js';
import type { ScanResult } from '../core/scanner.js';
import type { ScopeInfo } from './scope-md.js';

const minimalScope: ScopeInfo = {
  name: 'alpha',
  files: [],
  exports: [{ symbol: 'x', filepath: 'a.ts', kind: 'function' }],
  dependencies: [],
  reverseDeps: [],
  entryPoints: [],
  allScopeNames: ['alpha'],
};

const scanTwoFiles: ScanResult = {
  root: '/proj',
  files: [
    { filepath: 'src/heavy.ts', lines: 200, language: 'typescript', size: 4000 },
    { filepath: 'src/light.ts', lines: 20, language: 'typescript', size: 400 },
  ],
  totalFiles: 2,
  totalLines: 220,
  languages: { typescript: { files: 2, lines: 220 } },
  entryPoints: [],
  topLevelDirs: ['src'],
};

describe('renderIndexMd', () => {
  it('uses knowledgeLayer.conventions when provided', () => {
    const config: MpgaConfig = {
      ...DEFAULT_CONFIG,
      knowledgeLayer: {
        conventions: [
          'Always read INDEX before large changes.',
          'Cite [E] evidence when describing behavior.',
        ],
      },
    };
    const md = renderIndexMd(scanTwoFiles, config, [minimalScope], null, 0);
    expect(md).toContain('Always read INDEX before large changes.');
    expect(md).toContain('Cite [E] evidence when describing behavior.');
    expect(md).not.toContain('(Add your project conventions here)');
  });

  it('uses knowledgeLayer.keyFileRoles for matching key files', () => {
    const config: MpgaConfig = {
      ...DEFAULT_CONFIG,
      knowledgeLayer: {
        keyFileRoles: {
          'src/heavy.ts': 'Primary module — orchestrates sync.',
        },
      },
    };
    const md = renderIndexMd(scanTwoFiles, config, [minimalScope], null, 0);
    expect(md).toContain('| src/heavy.ts | Primary module — orchestrates sync. |');
    expect(md).toContain('| src/light.ts | (describe role) |');
  });

  it('falls back to placeholders when knowledgeLayer is absent', () => {
    const md = renderIndexMd(scanTwoFiles, DEFAULT_CONFIG, [minimalScope], null, 0);
    expect(md).toContain('(Add your project conventions here)');
    expect(md).toContain('| src/heavy.ts | (describe role) |');
  });
});
