import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import { log, miniBanner } from '../core/logger.js';
import { findProjectRoot } from '../core/config.js';
import { loadAllTasks, Task } from '../board/task.js';

// ---------------------------------------------------------------------------
// metrics command
// ---------------------------------------------------------------------------

interface MetricsData {
  total: number;
  done: number;
  inProgress: number;
  blocked: number;
  evidenceCoverage: string;
  tddAdherence: string;
  avgTaskTime: string | null;
}

function computeMetrics(tasks: Task[]): MetricsData {
  const total = tasks.length;
  const done = tasks.filter((t) => t.column === 'done').length;
  const inProgress = tasks.filter((t) =>
    ['in-progress', 'testing', 'review'].includes(t.column),
  ).length;
  const blocked = tasks.filter((t) => t.status === 'blocked').length;

  // Evidence coverage: produced / expected across all tasks
  const evidenceExpected = tasks.reduce((s, t) => s + t.evidence_expected.length, 0);
  const evidenceProduced = tasks.reduce((s, t) => s + t.evidence_produced.length, 0);
  const evidenceCoverage =
    evidenceExpected === 0 ? '0%' : `${Math.round((evidenceProduced / evidenceExpected) * 100)}%`;

  // TDD adherence: done tasks that completed tdd_stage=done / total done tasks
  const doneTasks = tasks.filter((t) => t.column === 'done');
  const tddComplete = doneTasks.filter((t) => t.tdd_stage === 'done').length;
  const tddAdherence =
    doneTasks.length === 0 ? '0%' : `${Math.round((tddComplete / doneTasks.length) * 100)}%`;

  // Average task completion time
  let avgTaskTime: string | null = null;
  const completedWithTimes = doneTasks.filter((t) => t.started_at && t.finished_at);
  if (completedWithTimes.length > 0) {
    const totalMs = completedWithTimes.reduce((sum, t) => {
      const start = new Date(t.started_at!).getTime();
      const end = new Date(t.finished_at!).getTime();
      return sum + (end - start);
    }, 0);
    const avgMs = totalMs / completedWithTimes.length;
    const hours = Math.round(avgMs / (1000 * 60 * 60));
    avgTaskTime = hours < 1 ? '<1h' : `${hours}h`;
  }

  return { total, done, inProgress, blocked, evidenceCoverage, tddAdherence, avgTaskTime };
}

function handleMetrics(opts: { json?: boolean }): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const mpgaDir = path.join(projectRoot, 'MPGA');

  if (!fs.existsSync(mpgaDir)) {
    log.error('MPGA not initialized. Run `mpga init` first.');
    process.exit(1);
  }

  const boardDir = path.join(mpgaDir, 'board');
  const tasksDir = path.join(boardDir, 'tasks');
  const tasks = loadAllTasks(tasksDir);
  const metrics = computeMetrics(tasks);

  if (opts.json) {
    console.log(
      JSON.stringify(
        {
          total: metrics.total,
          done: metrics.done,
          in_progress: metrics.inProgress,
          blocked: metrics.blocked,
          evidence_coverage: metrics.evidenceCoverage,
          tdd_adherence: metrics.tddAdherence,
          avg_task_time: metrics.avgTaskTime,
        },
        null,
        2,
      ),
    );
    return;
  }

  miniBanner();
  log.header('Project Metrics');

  log.section('  Task Summary');
  log.kv('Total tasks', String(metrics.total), 4);
  log.kv('Done', String(metrics.done), 4);
  log.kv('In-progress', String(metrics.inProgress), 4);
  log.kv('Blocked', String(metrics.blocked), 4);

  log.section('  Quality');
  log.kv('Evidence coverage', metrics.evidenceCoverage, 4);
  log.kv('TDD adherence', metrics.tddAdherence, 4);
  if (metrics.avgTaskTime) {
    log.kv('Avg completion', metrics.avgTaskTime, 4);
  }

  log.blank();
}

// ---------------------------------------------------------------------------
// changelog command
// ---------------------------------------------------------------------------

function handleChangelog(opts: { since?: string }): void {
  const projectRoot = findProjectRoot() ?? process.cwd();
  const mpgaDir = path.join(projectRoot, 'MPGA');

  if (!fs.existsSync(mpgaDir)) {
    log.error('MPGA not initialized. Run `mpga init` first.');
    process.exit(1);
  }

  const boardDir = path.join(mpgaDir, 'board');
  const tasksDir = path.join(boardDir, 'tasks');
  const tasks = loadAllTasks(tasksDir);

  let doneTasks = tasks.filter((t) => t.column === 'done');

  // Filter by --since date
  if (opts.since) {
    const sinceDate = new Date(opts.since).getTime();
    doneTasks = doneTasks.filter((t) => {
      const finishedAt = t.finished_at ? new Date(t.finished_at).getTime() : 0;
      return finishedAt >= sinceDate;
    });
  }

  if (doneTasks.length === 0) {
    log.info('No completed tasks found for changelog.');
    return;
  }

  // Group by milestone
  const grouped = new Map<string, Task[]>();
  for (const task of doneTasks) {
    const key = task.milestone ?? 'Unlinked';
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(task);
  }

  // Output markdown
  const today = new Date().toISOString().split('T')[0];
  console.log(`# Changelog — ${today}`);
  console.log('');

  for (const [milestone, milTasks] of grouped) {
    console.log(`## ${milestone}`);
    console.log('');
    for (const task of milTasks) {
      const date = task.finished_at
        ? new Date(task.finished_at).toISOString().split('T')[0]
        : task.updated.split('T')[0];
      console.log(`- **${task.id}**: ${task.title} (${date})`);
      for (const ev of task.evidence_produced) {
        console.log(`  - ${ev}`);
      }
    }
    console.log('');
  }
}

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

export function registerMetrics(program: Command): void {
  program
    .command('metrics')
    .description('Compute and display project metrics')
    .option('--json', 'Output as JSON')
    .action(handleMetrics);

  program
    .command('changelog')
    .description('Generate changelog from completed tasks')
    .option('--since <date>', 'Only include tasks completed after this date')
    .action(handleChangelog);
}
