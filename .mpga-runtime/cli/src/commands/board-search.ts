import { findProjectRoot } from '../core/config.js';
import { loadAllTasks, type Task } from '../board/task.js';
import { log } from '../core/logger.js';
import path from 'path';

export interface BoardSearchOpts {
  priority?: string;
  column?: string;
  scope?: string;
  agent?: string;
  tags?: string;
}

/**
 * Search and filter board tasks by criteria.
 * Returns matching tasks (also prints them to console).
 */
export function handleBoardSearch(query: string, opts: BoardSearchOpts): Task[] {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const tasksDir = path.join(projectRoot, 'MPGA', 'board', 'tasks');

  const allTasks = loadAllTasks(tasksDir);
  let results = allTasks;

  // Text search across task titles (case-insensitive)
  if (query && query.trim().length > 0) {
    const q = query.toLowerCase();
    results = results.filter((t) => t.title.toLowerCase().includes(q));
  }

  // Filter by priority
  if (opts.priority) {
    results = results.filter((t) => t.priority === opts.priority);
  }

  // Filter by column
  if (opts.column) {
    results = results.filter((t) => t.column === opts.column);
  }

  // Filter by scope
  if (opts.scope) {
    results = results.filter((t) => t.scopes.includes(opts.scope!));
  }

  // Filter by assigned agent
  if (opts.agent) {
    results = results.filter((t) => t.assigned === opts.agent);
  }

  // Filter by tags (comma-separated — task must have ALL specified tags)
  if (opts.tags) {
    const requiredTags = opts.tags.split(',').map((s) => s.trim());
    results = results.filter((t) => requiredTags.every((tag) => t.tags.includes(tag)));
  }

  // Print results
  if (results.length === 0) {
    log.info('No tasks match the given criteria.');
    return results;
  }

  log.header(`Search Results (${results.length} task${results.length === 1 ? '' : 's'})`);
  for (const t of results) {
    const parts = [
      t.id,
      t.title,
      `[${t.column}]`,
      t.priority,
    ];
    if (t.assigned) parts.push(`@${t.assigned}`);
    if (t.tags.length > 0) parts.push(`#${t.tags.join(',')}`);
    console.log(`  ${parts.join('  ')}`);
  }

  return results;
}
