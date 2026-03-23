import { describe, it, expect } from 'vitest';
import {
  extractModuleSummary,
  detectFrameworks,
  extractJSDocForExport,
  extractAnnotations,
  renderScopeMd,
  type ScopeInfo,
} from './scope-md.js';

// ── extractModuleSummary ──

describe('extractModuleSummary', () => {
  it('extracts a leading JSDoc block comment', () => {
    const content = `/** This module handles authentication. */\nimport express from 'express';`;
    expect(extractModuleSummary(content)).toBe('This module handles authentication.');
  });

  it('extracts multi-line JSDoc, skipping @tags', () => {
    const content = `/**\n * Board management utilities.\n * Handles task lifecycle.\n * @module board\n */\nimport fs from 'fs';`;
    expect(extractModuleSummary(content)).toBe(
      'Board management utilities. Handles task lifecycle.',
    );
  });

  it('extracts leading // comment block', () => {
    const content = `// Scanner module\n// Walks the filesystem and collects file info\nimport path from 'path';`;
    expect(extractModuleSummary(content)).toBe(
      'Scanner module Walks the filesystem and collects file info',
    );
  });

  it('returns null when no leading comment exists', () => {
    const content = `import fs from 'fs';\nconst x = 1;`;
    expect(extractModuleSummary(content)).toBeNull();
  });

  it('ignores JSDoc that is not at the top of the file', () => {
    const content = `import fs from 'fs';\n/** This is a function doc */\nexport function foo() {}`;
    expect(extractModuleSummary(content)).toBeNull();
  });
});

// ── detectFrameworks ──

describe('detectFrameworks', () => {
  it('detects known frameworks from imports', () => {
    const content = `import express from 'express';\nimport { z } from 'zod';`;
    const result = detectFrameworks(content);
    expect(result).toContain('Express');
    expect(result).toContain('Zod');
  });

  it('ignores relative imports', () => {
    const content = `import { foo } from './foo';\nimport bar from '../bar';`;
    expect(detectFrameworks(content)).toEqual([]);
  });

  it('detects require() style imports', () => {
    const content = `const express = require('express');`;
    expect(detectFrameworks(content)).toContain('Express');
  });

  it('handles scoped packages', () => {
    const content = `import { Client } from '@prisma/client';`;
    // @prisma/client won't match 'prisma' key directly — this tests that non-matching scoped packages don't crash
    expect(detectFrameworks(content)).toEqual([]);
  });

  it('deduplicates results', () => {
    const content = `import express from 'express';\nimport { Router } from 'express';`;
    // detectFrameworks itself doesn't deduplicate — groupIntoScopes does via Set
    // But within a single call, the Set in detectFrameworks handles it
    const result = detectFrameworks(content);
    expect(result.filter((f) => f === 'Express')).toHaveLength(1);
  });
});

// ── extractJSDocForExport ──

describe('extractJSDocForExport', () => {
  it('extracts description for a named export', () => {
    const content = `/** Load the board state from disk. */\nexport function loadBoard() {}`;
    expect(extractJSDocForExport(content, 'loadBoard')).toBe('Load the board state from disk.');
  });

  it('extracts first non-tag lines from multi-line JSDoc', () => {
    const content = `/**\n * Save the board to disk.\n * Writes JSON format.\n * @param board - the board state\n */\nexport function saveBoard(board: any) {}`;
    expect(extractJSDocForExport(content, 'saveBoard')).toBe(
      'Save the board to disk. Writes JSON format.',
    );
  });

  it('returns null when no JSDoc is present', () => {
    const content = `export function noDoc() {}`;
    expect(extractJSDocForExport(content, 'noDoc')).toBeNull();
  });

  it('returns null for non-existent symbol', () => {
    const content = `/** Docs */\nexport function exists() {}`;
    expect(extractJSDocForExport(content, 'doesNotExist')).toBeNull();
  });

  it('handles async functions', () => {
    const content = `/** Scan the filesystem. */\nexport async function scan() {}`;
    expect(extractJSDocForExport(content, 'scan')).toBe('Scan the filesystem.');
  });
});

// ── extractAnnotations ──

describe('extractAnnotations', () => {
  it('extracts @throws annotations', () => {
    const content = `/**\n * Do something.\n * @throws Error if config is missing\n */\nexport function doThing() {}`;
    const result = extractAnnotations(content, 'doThing');
    expect(result).toEqual(['@throws Error if config is missing']);
  });

  it('extracts @deprecated annotations', () => {
    const content = `/**\n * Old function.\n * @deprecated Use newFunc instead\n */\nexport function oldFunc() {}`;
    const result = extractAnnotations(content, 'oldFunc');
    expect(result).toEqual(['@deprecated Use newFunc instead']);
  });

  it('returns empty array when no annotations exist', () => {
    const content = `/** Simple doc. */\nexport function simple() {}`;
    expect(extractAnnotations(content, 'simple')).toEqual([]);
  });

  it('returns empty array when symbol not found', () => {
    const content = `/** @throws Error */\nexport function foo() {}`;
    expect(extractAnnotations(content, 'bar')).toEqual([]);
  });
});

// ── renderScopeMd integration ──

describe('renderScopeMd', () => {
  const baseScope: ScopeInfo = {
    name: 'auth',
    files: [{ filepath: 'src/auth/index.ts', lines: 100, language: 'typescript', size: 2000 }],
    exports: [{ symbol: 'login', filepath: 'src/auth/index.ts', kind: 'function' }],
    dependencies: ['db'],
    reverseDeps: ['api'],
    entryPoints: ['src/auth/index.ts'],
    allScopeNames: ['auth', 'db', 'api'],
    moduleSummaries: [],
    detectedFrameworks: [],
    exportDescriptions: [],
    rulesAndConstraints: [],
  };

  it('shows TODO when no module summary is available', () => {
    const md = renderScopeMd(baseScope, '/proj');
    expect(md).toContain('<!-- TODO: Describe what this area does');
  });

  it('shows module summary when available', () => {
    const scope = {
      ...baseScope,
      moduleSummaries: [
        { filepath: 'src/auth/index.ts', summary: 'Authentication and session management.' },
      ],
    };
    const md = renderScopeMd(scope, '/proj');
    expect(md).toContain('Authentication and session management.');
    expect(md).not.toContain('<!-- TODO: Describe what this area does');
  });

  it('shows TODO when no frameworks detected', () => {
    const md = renderScopeMd(baseScope, '/proj');
    expect(md).toContain('<!-- TODO: Add relevant frameworks');
  });

  it('shows detected frameworks', () => {
    const scope = { ...baseScope, detectedFrameworks: ['Express', 'Zod'] };
    const md = renderScopeMd(scope, '/proj');
    expect(md).toContain('**Frameworks:** Express, Zod');
    expect(md).not.toContain('<!-- TODO: Add relevant frameworks');
  });

  it('shows TODO when no export descriptions', () => {
    const md = renderScopeMd(baseScope, '/proj');
    expect(md).toContain('<!-- TODO: Describe the flow in plain language');
  });

  it('shows export descriptions in What happens section', () => {
    const scope = {
      ...baseScope,
      exportDescriptions: [
        {
          symbol: 'login',
          filepath: 'src/auth/index.ts',
          kind: 'function',
          description: 'Authenticate a user with credentials.',
        },
      ],
    };
    const md = renderScopeMd(scope, '/proj');
    expect(md).toContain('**login** (function) — Authenticate a user with credentials.');
    expect(md).not.toContain('<!-- TODO: Describe the flow in plain language');
  });

  it('shows TODO when no rules/constraints', () => {
    const md = renderScopeMd(baseScope, '/proj');
    expect(md).toContain('<!-- TODO: Constraints, validation');
  });

  it('shows rules and constraints when available', () => {
    const scope = {
      ...baseScope,
      rulesAndConstraints: [
        {
          filepath: 'src/auth/index.ts',
          symbol: 'login',
          annotation: '@throws Error if credentials are invalid',
        },
      ],
    };
    const md = renderScopeMd(scope, '/proj');
    expect(md).toContain('`login`: @throws Error if credentials are invalid');
    expect(md).not.toContain('<!-- TODO: Constraints, validation');
  });
});
