import fs from 'fs';
import { Command } from 'commander';
import chalk from 'chalk';
import { log } from '../core/logger.js';
import { loadConfig, findProjectRoot } from '../core/config.js';
import { runDriftCheck, healScopeFile } from '../evidence/drift.js';

export function registerDrift(program: Command): void {
  program
    .command('drift')
    .description('Detect drift between evidence links and codebase')
    .option('--report', 'Full staleness report (default)')
    .option('--quick', 'Fast check (for hooks)')
    .option('--ci', 'CI mode — exit code 0 = pass, 1 = fail')
    .option('--threshold <n>', 'Min % of valid evidence (default: 80)', '80')
    .option('--fix', 'Auto-sync stale scopes')
    .option('--scope <name>', 'Check specific scope')
    .option('--json', 'Output as JSON')
    .action(async (opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const config = loadConfig(projectRoot);
      const threshold = parseInt(opts.threshold ?? config.drift.ciThreshold);

      const report = await runDriftCheck(projectRoot, threshold, opts.scope);

      if (opts.json) {
        console.log(JSON.stringify(report, null, 2));
        if (opts.ci && !report.ciPass) process.exit(1);
        return;
      }

      if (opts.quick) {
        // Minimal output for hooks
        const staleTotal = report.scopes.reduce((s, r) => s + r.staleLinks, 0);
        if (staleTotal > 0) {
          log.warn(
            `Drift detected: ${staleTotal} stale evidence link(s). Run \`mpga evidence heal\` to fix.`,
          );
        }
        if (opts.ci && !report.ciPass) process.exit(1);
        return;
      }

      log.header('MPGA Drift Report');
      console.log(`  Timestamp: ${report.timestamp}`);
      console.log(`  Overall:   ${report.overallHealthPct}% (threshold: ${threshold}%)`);
      console.log('');

      if (report.scopes.length === 0) {
        log.info('No scopes found. Run `mpga sync` to generate them.');
        return;
      }

      for (const scope of report.scopes) {
        const icon =
          scope.healthPct >= 80
            ? chalk.green('✓ healthy')
            : scope.healthPct >= 50
              ? chalk.yellow('⚠ drift')
              : chalk.red('✗ stale');

        console.log(
          `  ${scope.scope.padEnd(20)} ${icon}   ${scope.validLinks}/${scope.totalLinks} links valid  (${scope.healthPct}%)`,
        );

        if (opts.report) {
          for (const item of scope.staleItems) {
            log.dim(
              `    ✗ stale: ${item.link.filepath}${item.link.startLine ? `:${item.link.startLine}` : ''} — ${item.reason}`,
            );
          }
          for (const item of scope.healedItems) {
            log.dim(
              `    ~ healed: ${item.link.filepath} line range updated to ${item.newStart}-${item.newEnd}`,
            );
          }
        }
      }

      if (opts.fix) {
        console.log('');
        log.info('Auto-fixing stale links...');
        let totalHealed = 0;
        for (const scope of report.scopes) {
          if (scope.healedItems.length === 0) continue;
          const { healed, content } = healScopeFile(scope);
          if (healed > 0) {
            fs.writeFileSync(scope.scopePath, content);
            log.success(`${scope.scope}: healed ${healed} link(s)`);
            totalHealed += healed;
          }
        }
        if (totalHealed > 0) log.success(`Total healed: ${totalHealed}`);
        const stale = report.scopes.reduce((s, r) => s + r.staleLinks, 0);
        if (stale > 0) log.warn(`${stale} link(s) need manual review (symbol not found in file)`);
      }

      console.log('');
      if (report.ciPass) {
        log.success(`Drift check passed (${report.overallHealthPct}% >= ${threshold}%)`);
      } else {
        log.error(`Drift check FAILED (${report.overallHealthPct}% < ${threshold}%)`);
        if (opts.ci) process.exit(1);
      }
    });
}
