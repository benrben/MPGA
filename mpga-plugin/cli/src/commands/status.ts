import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import chalk from 'chalk';
import { log, progressBar, miniBanner } from '../core/logger.js';
import { loadConfig, findProjectRoot } from '../core/config.js';
import { BoardState } from '../board/board.js';

export function registerStatus(program: Command): void {
  program
    .command('status')
    .description('Show project health dashboard')
    .option('--json', 'Output as JSON')
    .action((opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const mpgaDir = path.join(projectRoot, 'MPGA');
      const config = loadConfig(projectRoot);

      if (!fs.existsSync(mpgaDir)) {
        log.error('MPGA not initialized. Run `mpga init` first.');
        process.exit(1);
      }

      const indexPath = path.join(mpgaDir, 'INDEX.md');
      const boardPath = path.join(mpgaDir, 'board', 'board.json');
      const scopesDir = path.join(mpgaDir, 'scopes');

      // Read board state
      let boardState: BoardState | null = null;
      if (fs.existsSync(boardPath)) {
        boardState = JSON.parse(fs.readFileSync(boardPath, 'utf-8'));
      }

      // Count scopes
      const scopes = fs.existsSync(scopesDir)
        ? fs.readdirSync(scopesDir).filter(f => f.endsWith('.md'))
        : [];

      // Read INDEX.md for last sync info
      let lastSync = 'never';
      let evidenceCoverage = '0%';
      if (fs.existsSync(indexPath)) {
        const content = fs.readFileSync(indexPath, 'utf-8');
        const syncMatch = content.match(/\*\*Last sync:\*\* (.+)/);
        if (syncMatch && !syncMatch[1].includes('run')) lastSync = syncMatch[1];
        const covMatch = content.match(/\*\*Evidence coverage:\*\* ([\d.]+%)/);
        if (covMatch) evidenceCoverage = covMatch[1];
      }

      if (opts.json) {
        console.log(JSON.stringify({
          initialized: true,
          lastSync,
          evidenceCoverage,
          scopes: scopes.length,
          board: boardState?.stats ?? null,
          config: { name: config.project.name },
        }, null, 2));
        return;
      }

      miniBanner();

      // ── Knowledge Layer ──
      log.header(`Status — ${config.project.name}`);

      log.section('  📚 Knowledge Layer');
      log.kv('Last sync', lastSync, 4);
      log.kv('Scopes', String(scopes.length), 4);
      log.kv('Evidence', evidenceCoverage, 4);
      log.kv('INDEX.md', fs.existsSync(indexPath) ? chalk.green('✓ present') : chalk.red('✗ missing'), 4);

      if (scopes.length > 0) {
        log.section('  🗂  Scopes');
        for (const scope of scopes) {
          const scopeName = scope.replace('.md', '');
          const scopePath = path.join(scopesDir, scope);
          const content = fs.readFileSync(scopePath, 'utf-8');
          const healthMatch = content.match(/\*\*Health:\*\* (.+)/);
          const health = healthMatch ? healthMatch[1] : chalk.dim('unknown');
          console.log(`    ${chalk.white(scopeName.padEnd(22))} ${health}`);
        }
      }

      // ── Board ──
      if (boardState) {
        const stats = boardState.stats;
        log.section('  📋 Task Board');
        const milestone = boardState.milestone ?? chalk.dim('none');
        log.kv('Milestone', String(milestone), 4);
        log.kv('Progress', `${progressBar(stats.done, stats.total)}  ${chalk.dim(`${stats.done}/${stats.total}`)}`, 4);
        if (stats.in_flight > 0) log.kv('In flight', chalk.yellow(String(stats.in_flight)), 4);
        if (stats.blocked > 0) log.kv('Blocked', chalk.red(String(stats.blocked)), 4);

        const cols = boardState.columns as Record<string, string[]>;
        const colSummary = Object.entries(cols)
          .filter(([, tasks]) => tasks.length > 0)
          .map(([col, tasks]) => `${col}(${chalk.white(String(tasks.length))})`)
          .join('  ');
        if (colSummary) log.kv('Columns', colSummary, 4);
      }

      // ── Config ──
      log.section('  ⚙  Configuration');
      log.kv('Project', config.project.name, 4);
      log.kv('Languages', config.project.languages.join(', '), 4);
      log.kv('Evidence', `${config.evidence.strategy}, ${Math.round(config.evidence.coverageThreshold * 100)}% target`, 4);
      log.kv('CI threshold', `${config.drift.ciThreshold}%`, 4);

      log.blank();
      log.dim('  Run `mpga sync` to refresh  ·  `mpga health` for full report');
      log.blank();
    });
}
