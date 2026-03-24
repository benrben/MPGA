import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import { log } from '../core/logger.js';
import { loadConfig, findProjectRoot } from '../core/config.js';
import { scan } from '../core/scanner.js';
import { buildGraph, renderGraphMd } from '../generators/graph-md.js';
import { groupIntoScopes, renderScopeMd } from '../generators/scope-md.js';
import { renderIndexMd } from '../generators/index-md.js';
import { runDriftCheck } from '../evidence/drift.js';

export function registerSync(program: Command): void {
  program
    .command('sync')
    .description('Regenerate/update the knowledge layer')
    .option('--full', 'Rebuild everything (default)')
    .option('--incremental', 'Only update changed files since last sync')
    .action(async (opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const mpgaDir = path.join(projectRoot, 'MPGA');

      if (!fs.existsSync(mpgaDir)) {
        log.error('MPGA not initialized. Run `mpga init` first.');
        process.exit(1);
      }

      const config = loadConfig(projectRoot);
      log.header('MPGA Sync');

      // Step 1: Scan
      log.info('Scanning codebase...');
      const scanResult = await scan(projectRoot, config.project.ignore, true);
      log.success(
        `Scanned ${scanResult.totalFiles} files (${scanResult.totalLines.toLocaleString()} lines)`,
      );

      // Step 2: Build dependency graph
      log.info('Building dependency graph...');
      const graph = await buildGraph(scanResult, config);
      const graphMd = renderGraphMd(graph);
      fs.writeFileSync(path.join(mpgaDir, 'GRAPH.md'), graphMd);
      log.success(
        `GRAPH.md — ${graph.dependencies.length} dependencies, ${graph.circular.length} circular`,
      );

      // Step 3: Generate scope docs
      log.info('Generating scope documents...');
      const scopesDir = path.join(mpgaDir, 'scopes');
      fs.mkdirSync(scopesDir, { recursive: true });
      const scopes = groupIntoScopes(scanResult, graph, config);

      for (const scope of scopes) {
        const scopePath = path.join(scopesDir, `${scope.name}.md`);
        // In incremental mode, skip if file exists and scope hasn't changed
        if (opts.incremental && fs.existsSync(scopePath)) continue;
        const scopeMd = renderScopeMd(scope, projectRoot);
        fs.writeFileSync(scopePath, scopeMd);
      }
      log.success(`Generated ${scopes.length} scope documents`);

      // Step 4: Generate INDEX.md
      log.info('Generating INDEX.md...');

      // Read active milestone
      let activeMilestone: string | null = null;
      const milestonesDir = path.join(mpgaDir, 'milestones');
      if (fs.existsSync(milestonesDir)) {
        const mDirs = fs
          .readdirSync(milestonesDir)
          .filter((d) => fs.statSync(path.join(milestonesDir, d)).isDirectory());
        if (mDirs.length > 0) activeMilestone = mDirs[mDirs.length - 1];
      }

      const driftReport = await runDriftCheck(projectRoot, config.drift.ciThreshold);
      const evidenceCoverage =
        driftReport.totalLinks === 0 ? 0 : driftReport.validLinks / driftReport.totalLinks;

      const indexMd = renderIndexMd(scanResult, config, scopes, activeMilestone, evidenceCoverage);
      fs.writeFileSync(path.join(mpgaDir, 'INDEX.md'), indexMd);
      log.success('INDEX.md generated');

      // Summary
      console.log('');
      log.success('Sync complete!');
      console.log('');
      log.dim(`  ${scopes.length} scopes in MPGA/scopes/`);
      log.dim('  Run `mpga evidence verify` to check evidence health');
      log.dim('  Run `mpga status` to view dashboard');
    });
}
