import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { taskFilename, renderTaskFile, parseTaskFile, Task } from './task.js';

describe('taskFilename', () => {
  it('generates a slug from title', () => {
    expect(taskFilename('T001', 'Add authentication middleware')).toBe('T001-add-authentication-middleware.md');
  });

  it('handles special characters', () => {
    expect(taskFilename('T002', 'Fix bug #42: login fails!')).toBe('T002-fix-bug-42-login-fails.md');
  });

  it('truncates long titles', () => {
    const longTitle = 'This is a very long task title that exceeds the maximum slug length for filenames';
    const filename = taskFilename('T003', longTitle);
    expect(filename.length).toBeLessThan(60);
    expect(filename).toMatch(/^T003-.+\.md$/);
  });
});

describe('renderTaskFile / parseTaskFile', () => {
  let tmpDir: string;

  const sampleTask: Task = {
    id: 'T001',
    title: 'Add login page',
    column: 'todo',
    status: null,
    priority: 'high',
    milestone: 'v1.0',
    created: '2026-03-22',
    updated: '2026-03-22',
    depends_on: [],
    blocks: ['T002'],
    scopes: ['auth'],
    tdd_stage: 'green',
    evidence_expected: ['[E] src/auth.ts :: login'],
    evidence_produced: [],
    tags: ['auth', 'frontend'],
    time_estimate: '30min',
    body: '# Task body\n\nSome details here.',
  };

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-task-'));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('renders and parses a task round-trip', () => {
    const rendered = renderTaskFile(sampleTask);
    expect(rendered).toContain('---');
    expect(rendered).toContain('T001');
    expect(rendered).toContain('Add login page');

    const filepath = path.join(tmpDir, 'T001-add-login-page.md');
    fs.writeFileSync(filepath, rendered);

    const parsed = parseTaskFile(filepath);
    expect(parsed).not.toBeNull();
    expect(parsed!.id).toBe('T001');
    expect(parsed!.title).toBe('Add login page');
    expect(parsed!.column).toBe('todo');
    expect(parsed!.priority).toBe('high');
    expect(parsed!.blocks).toEqual(['T002']);
    expect(parsed!.scopes).toEqual(['auth']);
    expect(parsed!.tdd_stage).toBe('green');
  });

  it('returns null for non-existent file', () => {
    expect(parseTaskFile('/nonexistent/path.md')).toBeNull();
  });
});
