import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import { log } from '../core/logger.js';
import { findProjectRoot } from '../core/config.js';
import { parseEvidenceLinks, evidenceStats } from '../evidence/parser.js';

/** Number of characters of context to show before a search match in excerpts. */
const EXCERPT_CONTEXT_CHARS = 50;
/** Maximum length of a search result excerpt in characters. */
const EXCERPT_MAX_LENGTH = 200;
/** Maximum number of scope search results to display. */
const MAX_SEARCH_RESULTS = 3;

function getScopesDir(projectRoot: string): string {
  return path.join(projectRoot, 'MPGA', 'scopes');
}

function handleScopeList(): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const scopesDir = getScopesDir(projectRoot);

  if (!fs.existsSync(scopesDir)) {
    log.error('No scopes found. Run `mpga sync` first.');
    return;
  }

  const files = fs.readdirSync(scopesDir).filter((f) => f.endsWith('.md'));
  if (files.length === 0) {
    log.info('No scopes found. Run `mpga sync` to generate them.');
    return;
  }

  log.header('Scopes');
  const rows: string[][] = [['Scope', 'Health', 'Evidence', 'Last verified']];
  for (const file of files) {
    const content = fs.readFileSync(path.join(scopesDir, file), 'utf-8');
    const links = parseEvidenceLinks(content);
    const stats = evidenceStats(links);
    const healthMatch = content.match(/\*\*Health:\*\* (.+)/);
    const health = healthMatch ? healthMatch[1] : '? unknown';
    const verifiedMatch = content.match(/\*\*Last verified:\*\* (.+)/);
    const verified = verifiedMatch ? verifiedMatch[1] : '?';
    rows.push([file.replace('.md', ''), health, `${stats.valid}/${stats.total}`, verified]);
  }
  log.table(rows);
}

function handleScopeShow(name: string): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const scopePath = path.join(getScopesDir(projectRoot), `${name}.md`);

  if (!fs.existsSync(scopePath)) {
    log.error(`Scope '${name}' not found. Run \`mpga scope list\` to see available scopes.`);
    process.exit(1);
  }

  const content = fs.readFileSync(scopePath, 'utf-8');
  const links = parseEvidenceLinks(content);
  const stats = evidenceStats(links);

  console.log(content);
  console.log('');
  log.dim(
    `─── Evidence: ${stats.valid} valid, ${stats.stale} stale, ${stats.unknown} unknown (${stats.healthPct}% health) ───`,
  );
}

function handleScopeAdd(name: string): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const scopesDir = getScopesDir(projectRoot);
  fs.mkdirSync(scopesDir, { recursive: true });

  const scopePath = path.join(scopesDir, `${name}.md`);
  if (fs.existsSync(scopePath)) {
    log.error(`Scope '${name}' already exists.`);
    process.exit(1);
  }

  const now = new Date().toISOString().split('T')[0];
  const template = `# Scope: ${name}

## Summary
<!-- TODO: Describe what this area does and what is intentionally out of scope -->

## Where to start in code
<!-- TODO: The main entry points — files or modules someone should open first -->

## Context / stack / skills
<!-- TODO: Technologies, integrations, and relevant expertise -->

## Who and what triggers it
<!-- TODO: Users, systems, schedules, or APIs that kick off this behavior -->

## What happens
<!-- TODO: The flow in plain language: inputs, main steps, outputs or side effects -->

## Rules and edge cases
<!-- TODO: Constraints, validation, permissions, failures, retries, empty states -->

## Concrete examples
<!-- TODO: A few real scenarios ("when X happens, Y results") -->

## UI
<!-- TODO: Screens or flows if relevant. Remove this section if not applicable. -->

## Navigation
**Parent:** [INDEX.md](../INDEX.md)

## Relationships
<!-- TODO: What this depends on, what depends on it, and shared concepts -->

## Diagram
<!-- TODO: Flow, sequence, or boundary diagrams (must match written story and evidence) -->

## Traces
<!-- TODO: Step-by-step paths through the system:

| Step | Layer | What happens | Evidence |
|------|-------|-------------|----------|
| 1 | (layer) | (description) | [E] file:line |
-->

## Evidence index
<!-- TODO: Map claims to code references:

| Claim | Evidence |
|-------|----------|
| (description) | [E] file :: symbol |
-->

## Deeper splits
<!-- TODO: Pointers to sub-topic scopes if this capability is large enough to split -->

## Confidence and notes
- **Confidence:** low — manually created, not yet filled
- **Evidence coverage:** 0/0 verified
- **Last verified:** ${now}
- **Drift risk:** unknown
<!-- TODO: Note anything unknown, ambiguous, or still to verify -->

## Change history
- ${now}: Created manually
`;
  fs.writeFileSync(scopePath, template);
  log.success(`Created MPGA/scopes/${name}.md`);
}

function handleScopeRemove(name: string): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const scopePath = path.join(getScopesDir(projectRoot), `${name}.md`);

  if (!fs.existsSync(scopePath)) {
    log.error(`Scope '${name}' not found.`);
    process.exit(1);
  }

  const archiveDir = path.join(projectRoot, 'MPGA', 'milestones', '_archived-scopes');
  fs.mkdirSync(archiveDir, { recursive: true });
  const archivePath = path.join(archiveDir, `${name}-${Date.now()}.md`);
  fs.renameSync(scopePath, archivePath);
  log.success(`Archived scope '${name}' to ${path.relative(projectRoot, archivePath)}`);
}

function handleScopeQuery(question: string): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const scopesDir = getScopesDir(projectRoot);

  if (!fs.existsSync(scopesDir)) {
    log.error('No scopes found. Run `mpga sync` first.');
    return;
  }

  const files = fs.readdirSync(scopesDir).filter((f) => f.endsWith('.md'));
  const terms = question.toLowerCase().split(/\s+/);
  const matches: Array<{ name: string; score: number; excerpt: string }> = [];

  for (const file of files) {
    const content = fs.readFileSync(path.join(scopesDir, file), 'utf-8');
    const lower = content.toLowerCase();
    let score = 0;
    for (const term of terms) score += (lower.match(new RegExp(term, 'g')) ?? []).length;

    if (score > 0) {
      const lineIdx = content.toLowerCase().indexOf(terms[0]);
      const start = Math.max(0, lineIdx - EXCERPT_CONTEXT_CHARS);
      const excerpt = content.slice(start, start + EXCERPT_MAX_LENGTH).replace(/\n/g, ' ');
      matches.push({ name: file.replace('.md', ''), score, excerpt });
    }
  }

  matches.sort((a, b) => b.score - a.score);

  if (matches.length === 0) {
    log.info(`No scopes matched "${question}"`);
    log.dim('Tip: Run `mpga sync` to generate more detailed scope docs.');
    return;
  }

  log.header(`Scope search: "${question}"`);
  for (const m of matches.slice(0, MAX_SEARCH_RESULTS)) {
    console.log('');
    log.bold(`  ${m.name}  (score: ${m.score})`);
    log.dim(`  ...${m.excerpt}...`);
  }
}

export function registerScope(program: Command): void {
  const cmd = program.command('scope').description('Manage scope documents');

  // scope list
  cmd.command('list').description('Show all scopes with health status').action(handleScopeList);

  // scope show <name>
  cmd
    .command('show <name>')
    .description('Display a scope with evidence status')
    .action(handleScopeShow);

  // scope add <name>
  cmd.command('add <name>').description('Create a new empty scope document').action(handleScopeAdd);

  // scope remove <name>
  cmd.command('remove <name>').description('Archive a scope document').action(handleScopeRemove);

  // scope query <question>
  cmd
    .command('query <question>')
    .description('Search scopes for an answer')
    .action(handleScopeQuery);
}
