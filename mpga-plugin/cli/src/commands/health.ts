import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import chalk from 'chalk';
import { log, progressBar, miniBanner, gradeColor, statusBadge } from '../core/logger.js';
import { findProjectRoot, loadConfig } from '../core/config.js';
import { runDriftCheck } from '../evidence/drift.js';
import { loadBoard, recalcStats } from '../board/board.js';

export function registerHealth(program: Command): void {
  program
    .command('health')
    .description('Overall project health report')
    .option('--verbose', 'Detailed breakdown')
    .option('--json', 'Machine-readable output')
    .action(async (opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const mpgaDir = path.join(projectRoot, 'MPGA');
      const config = loadConfig(projectRoot);

      if (!fs.existsSync(mpgaDir)) {
        log.error('MPGA not initialized. Run `mpga init` first.');
        process.exit(1);
      }

      // Gather evidence health
      const driftReport = await runDriftCheck(projectRoot, config.drift.ciThreshold);

      // Gather board health
      const boardDir = path.join(mpgaDir, 'board');
      const tasksDir = path.join(boardDir, 'tasks');
      let boardStats: any = null;
      if (fs.existsSync(path.join(boardDir, 'board.json'))) {
        const board = loadBoard(boardDir);
        recalcStats(board, tasksDir);
        boardStats = board.stats;
      }

      // Gather scope count
      const scopesDir = path.join(mpgaDir, 'scopes');
      const scopeCount = fs.existsSync(scopesDir)
        ? fs.readdirSync(scopesDir).filter(f => f.endsWith('.md')).length
        : 0;

      const health = {
        initialized: true,
        evidenceHealth: driftReport.overallHealthPct,
        evidenceTarget: config.evidence.coverageThreshold * 100,
        ciThreshold: config.drift.ciThreshold,
        ciPass: driftReport.ciPass,
        scopes: scopeCount,
        board: boardStats,
        lastSync: getLastSync(mpgaDir),
        overallGrade: computeGrade(driftReport.overallHealthPct, config.drift.ciThreshold),
      };

      if (opts.json) {
        console.log(JSON.stringify(health, null, 2));
        return;
      }

      miniBanner();
      log.header('Health Report');

      // ── Grade ──
      console.log(`\n  ${chalk.dim('Grade')}  ${gradeColor(health.overallGrade)}\n`);

      // ── Evidence ──
      console.log(`  ${statusBadge(driftReport.overallHealthPct >= 80, 'Evidence health')}   ${driftReport.overallHealthPct}%  ${chalk.dim(`(CI threshold: ${config.drift.ciThreshold}%)`)}`);
      console.log(`    ${progressBar(driftReport.validLinks, driftReport.totalLinks)}  ${chalk.dim(`${driftReport.validLinks}/${driftReport.totalLinks} links`)}`);

      if (opts.verbose && driftReport.scopes.length > 0) {
        log.blank();
        for (const scope of driftReport.scopes) {
          const icon = scope.healthPct >= 80 ? chalk.green('✓') : chalk.yellow('⚠');
          console.log(`    ${icon} ${chalk.white(scope.scope.padEnd(20))} ${scope.healthPct}% ${chalk.dim(`(${scope.validLinks}/${scope.totalLinks})`)}`);
        }
      }

      // ── Scopes ──
      log.blank();
      console.log(`  ${statusBadge(scopeCount > 0, 'Scopes')}            ${scopeCount} document(s)`);

      // ── Board ──
      if (boardStats) {
        log.blank();
        console.log(`  ${statusBadge(boardStats.blocked === 0, 'Task board')}        ${boardStats.done}/${boardStats.total} tasks ${chalk.dim(`(${boardStats.progress_pct}%)`)}`);
        if (boardStats.blocked > 0) console.log(`    ${chalk.yellow('⚠')} ${boardStats.blocked} blocked task(s)`);
      }

      // ── Last sync ──
      log.blank();
      console.log(`  ${chalk.blue('ℹ')} Last sync          ${chalk.dim(health.lastSync)}`);

      // ── Recommendations ──
      log.blank();
      log.divider();
      if (driftReport.overallHealthPct < config.drift.ciThreshold) {
        log.warn(`Evidence below CI threshold — run \`mpga evidence heal\` or \`mpga sync\``);
      }
      if (scopeCount === 0) {
        log.warn('No scope documents — run `mpga sync` to generate them');
      }
      if (!driftReport.ciPass) {
        log.error(`CI would FAIL at ${config.drift.ciThreshold}% threshold`);
      } else {
        log.success('All health checks pass');
      }
      log.blank();
    });
}

function computeGrade(healthPct: number, threshold: number): string {
  if (healthPct >= 95) return 'A';
  if (healthPct >= threshold) return 'B';
  if (healthPct >= threshold * 0.7) return 'C';
  return 'D';
}

function getLastSync(mpgaDir: string): string {
  const indexPath = path.join(mpgaDir, 'INDEX.md');
  if (!fs.existsSync(indexPath)) return 'never';
  const content = fs.readFileSync(indexPath, 'utf-8');
  const m = content.match(/\*\*Last sync:\*\* (.+)/);
  if (m && !m[1].includes('run')) return m[1].trim();
  return 'never';
}
