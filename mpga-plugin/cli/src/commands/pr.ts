import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import { execSync } from 'child_process';
import { log } from '../core/logger.js';
import { findProjectRoot } from '../core/config.js';
import { loadAllTasks } from '../board/task.js';

// ---------------------------------------------------------------------------
// pr command
// ---------------------------------------------------------------------------

function handlePr(): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const mpgaDir = path.join(projectRoot, 'MPGA');

  if (!fs.existsSync(mpgaDir)) {
    log.error('MPGA not initialized. Run `mpga init` first.');
    process.exit(1);
  }

  // Gather git info
  let branch: string;
  let commits: string;
  let changedFiles: string;

  try {
    branch = execSync('git rev-parse --abbrev-ref HEAD', { cwd: projectRoot }).toString().trim();
    const base = execSync(
      'git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null || echo HEAD~10',
      { cwd: projectRoot },
    )
      .toString()
      .trim();
    commits = execSync(`git log --oneline ${base}..HEAD`, { cwd: projectRoot }).toString().trim();
    changedFiles = execSync(`git diff --name-only ${base}..HEAD`, { cwd: projectRoot })
      .toString()
      .trim();
  } catch {
    log.error('Failed to read git information. Ensure you are in a git repository.');
    process.exit(1);
  }

  // Load tasks for evidence links
  const tasksDir = path.join(mpgaDir, 'board', 'tasks');
  const tasks = loadAllTasks(tasksDir);
  const doneTasks = tasks.filter((t) => t.column === 'done');
  const evidenceLinks = doneTasks.flatMap((t) => t.evidence_produced);

  // Detect affected scopes
  const scopesDir = path.join(mpgaDir, 'scopes');
  const scopes: string[] = [];
  if (fs.existsSync(scopesDir)) {
    const scopeFiles = fs.readdirSync(scopesDir).filter((f) => f.endsWith('.md'));
    for (const sf of scopeFiles) {
      scopes.push(sf.replace('.md', ''));
    }
  }

  // Build PR description markdown
  const lines: string[] = [];
  lines.push(`## PR: ${branch}`);
  lines.push('');

  // Commits
  if (commits) {
    lines.push('### Commits');
    lines.push('');
    for (const line of commits.split('\n')) {
      if (line.trim()) lines.push(`- ${line.trim()}`);
    }
    lines.push('');
  }

  // Changed files
  if (changedFiles) {
    lines.push('### Changed files');
    lines.push('');
    for (const file of changedFiles.split('\n')) {
      if (file.trim()) lines.push(`- \`${file.trim()}\``);
    }
    lines.push('');
  }

  // Affected scopes
  if (scopes.length > 0) {
    lines.push('### Affected scopes');
    lines.push('');
    for (const scope of scopes) {
      lines.push(`- ${scope}`);
    }
    lines.push('');
  }

  // Evidence links
  if (evidenceLinks.length > 0) {
    lines.push('### Evidence');
    lines.push('');
    for (const link of evidenceLinks) {
      lines.push(`- ${link}`);
    }
    lines.push('');
  }

  console.log(lines.join('\n'));
}

// ---------------------------------------------------------------------------
// decision command
// ---------------------------------------------------------------------------

function handleDecision(title: string): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const mpgaDir = path.join(projectRoot, 'MPGA');

  if (!fs.existsSync(mpgaDir)) {
    log.error('MPGA not initialized. Run `mpga init` first.');
    process.exit(1);
  }

  const decisionsDir = path.join(mpgaDir, 'decisions');
  fs.mkdirSync(decisionsDir, { recursive: true });

  // Determine next ADR number
  const existing = fs.readdirSync(decisionsDir).filter((f) => f.endsWith('.md'));
  const numbers = existing
    .map((f) => {
      const match = f.match(/^(\d+)-/);
      return match ? parseInt(match[1], 10) : 0;
    })
    .filter((n) => n > 0);
  const nextNum = numbers.length > 0 ? Math.max(...numbers) + 1 : 1;
  const numStr = String(nextNum).padStart(3, '0');

  // Slugify title
  const slug = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 60);

  const today = new Date().toISOString().split('T')[0];
  const filename = `${numStr}-${today}-${slug}.md`;
  const filepath = path.join(decisionsDir, filename);

  const content = `# ADR: ${title}

**Date:** ${today}
**Number:** ${numStr}

## Status

Proposed

## Context

(Describe the context and problem statement that led to this decision.)

## Decision

(Describe the decision that was made.)

## Consequences

### Positive
- (List positive outcomes)

### Negative
- (List negative outcomes or trade-offs)

### Neutral
- (List neutral observations)
`;

  fs.writeFileSync(filepath, content);
  log.success(`ADR created: ${filepath}`);
}

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

export function registerPr(program: Command): void {
  program
    .command('pr')
    .description('Generate PR description from current branch changes')
    .action(handlePr);

  program
    .command('decision <title>')
    .description('Create an Architecture Decision Record (ADR)')
    .action(handleDecision);
}
