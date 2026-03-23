import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import chalk from 'chalk';
import { log, progressBar } from '../core/logger.js';
import { loadConfig, findProjectRoot } from '../core/config.js';
import { formatEvidenceLink } from '../evidence/parser.js';
import { runDriftCheck, healScopeFile } from '../evidence/drift.js';

export function registerEvidence(program: Command): void {
  const cmd = program
    .command('evidence')
    .description('Evidence link management');

  // evidence verify
  cmd
    .command('verify')
    .description('Check all evidence links resolve to real code')
    .option('--scope <name>', 'Check specific scope only')
    .option('--json', 'Output as JSON')
    .action(async (opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const config = loadConfig(projectRoot);

      log.info('Verifying evidence links...');
      const report = await runDriftCheck(projectRoot, config.drift.ciThreshold, opts.scope);

      if (opts.json) {
        console.log(JSON.stringify(report, null, 2));
        return;
      }

      log.header('Evidence Verification');

      for (const scope of report.scopes) {
        const icon = scope.healthPct >= 80 ? chalk.green('✓') : scope.healthPct >= 50 ? chalk.yellow('⚠') : chalk.red('✗');
        console.log(`\n${icon} ${chalk.bold(scope.scope)}  ${scope.healthPct}% (${scope.validLinks}/${scope.totalLinks} valid)`);

        if (scope.staleItems.length > 0) {
          log.dim('  Stale links:');
          for (const item of scope.staleItems) {
            log.dim(`    ${formatEvidenceLink(item.link)} — ${item.reason}`);
          }
        }
        if (scope.healedItems.length > 0) {
          log.dim('  Healed links:');
          for (const item of scope.healedItems) {
            log.dim(`    ${item.link.filepath}:${item.newStart}-${item.newEnd} (was ${item.link.startLine}-${item.link.endLine})`);
          }
        }
      }

      console.log('');
      log.bold('Overall');
      console.log(`  Health:  ${progressBar(report.validLinks, report.totalLinks)} (${report.validLinks}/${report.totalLinks})`);
      if (report.totalLinks === 0) {
        log.info('No evidence links found. Run `mpga sync` to generate them.');
      } else if (report.overallHealthPct >= 80) {
        log.success(`Evidence health: ${report.overallHealthPct}%`);
      } else {
        log.warn(`Evidence health: ${report.overallHealthPct}% — run \`mpga evidence heal\` to fix stale links`);
      }
    });

  // evidence heal
  cmd
    .command('heal')
    .description('Re-resolve broken links via AST and update scope files')
    .option('--auto', 'Auto-fix without confirmation')
    .option('--scope <name>', 'Heal specific scope only')
    .action(async (opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const config = loadConfig(projectRoot);

      log.info('Running evidence heal...');
      const report = await runDriftCheck(projectRoot, config.drift.ciThreshold, opts.scope);

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

      const staleCount = report.scopes.reduce((s, r) => s + r.staleLinks, 0);
      if (totalHealed > 0) log.success(`Total healed: ${totalHealed} link(s)`);
      if (staleCount > 0) log.warn(`${staleCount} link(s) could not be healed (symbol not found) — manual review required`);
      if (totalHealed === 0 && staleCount === 0) log.success('All evidence links are already valid.');
    });

  // evidence coverage
  cmd
    .command('coverage')
    .description('Report evidence-to-code ratio')
    .option('--min <pct>', 'Fail if coverage below this %', '20')
    .action(async (opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const config = loadConfig(projectRoot);
      const report = await runDriftCheck(projectRoot, config.drift.ciThreshold);

      const minPct = parseInt(opts.min);
      log.header('Evidence Coverage');

      for (const scope of report.scopes) {
        const bar = progressBar(scope.validLinks, scope.totalLinks);
        console.log(`  ${scope.scope.padEnd(20)} ${bar}  (${scope.validLinks}/${scope.totalLinks})`);
      }

      console.log('');
      const pct = report.overallHealthPct;
      console.log(`  Overall: ${pct}% (threshold: ${minPct}%)`);

      if (pct < minPct) {
        log.warn(`Coverage ${pct}% is below threshold ${minPct}%`);
        process.exit(1);
      } else {
        log.success(`Coverage ${pct}% meets threshold ${minPct}%`);
      }
    });

  // evidence add
  cmd
    .command('add <scope> <link>')
    .description('Manually add an evidence link to a scope document')
    .action((scopeName: string, link: string) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const scopePath = path.join(projectRoot, 'MPGA', 'scopes', `${scopeName}.md`);

      if (!fs.existsSync(scopePath)) {
        log.error(`Scope '${scopeName}' not found.`);
        process.exit(1);
      }

      const content = fs.readFileSync(scopePath, 'utf-8');
      const evidenceLink = link.startsWith('[') ? link : `[E] ${link}`;

      // Insert before the Known unknowns section
      const updated = content.includes('## Known unknowns')
        ? content.replace('## Known unknowns', `${evidenceLink}\n\n## Known unknowns`)
        : content + '\n' + evidenceLink + '\n';

      fs.writeFileSync(scopePath, updated);
      log.success(`Added evidence link to scope '${scopeName}': ${evidenceLink}`);
    });
}
