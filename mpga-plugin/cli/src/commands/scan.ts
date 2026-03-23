import { Command } from 'commander';
import { log } from '../core/logger.js';
import { loadConfig, findProjectRoot } from '../core/config.js';
import { scan, detectProjectType } from '../core/scanner.js';

export function registerScan(program: Command): void {
  program
    .command('scan')
    .description('Analyze codebase structure and file tree')
    .option('--deep', 'Full analysis (default)')
    .option('--quick', 'File tree and exports only')
    .option('--lang <lang>', 'Language hint (auto-detected if omitted)')
    .option('--json', 'Output as JSON')
    .action(async (opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const config = loadConfig(projectRoot);

      if (!opts.json) {
        log.header('MPGA Scan');
        log.info(`Scanning ${projectRoot}...`);
      }

      const result = await scan(projectRoot, config.project.ignore, !opts.quick);

      if (opts.json) {
        console.log(JSON.stringify(result, null, 2));
        return;
      }

      const projectType = detectProjectType(result);
      const totalLines = result.totalLines;

      console.log('');
      log.bold('Project summary');
      console.log(`  Type:      ${projectType}`);
      console.log(`  Root:      ${projectRoot}`);
      console.log(`  Files:     ${result.totalFiles}`);
      console.log(`  Lines:     ${totalLines.toLocaleString()}`);

      console.log('');
      log.bold('Languages');
      const langEntries = Object.entries(result.languages).sort((a, b) => b[1].lines - a[1].lines);
      for (const [lang, stats] of langEntries) {
        const pct = Math.round((stats.lines / totalLines) * 100);
        const bar = '█'.repeat(Math.round(pct / 5)) + '░'.repeat(20 - Math.round(pct / 5));
        console.log(
          `  ${lang.padEnd(12)} ${bar} ${pct}%  (${stats.files} files, ${stats.lines.toLocaleString()} lines)`,
        );
      }

      if (result.entryPoints.length > 0) {
        console.log('');
        log.bold('Entry points');
        for (const ep of result.entryPoints) console.log(`  ${ep}`);
      }

      if (result.topLevelDirs.length > 0) {
        console.log('');
        log.bold('Top-level directories');
        for (const dir of result.topLevelDirs) console.log(`  ${dir}/`);
      }

      if (opts.deep) {
        console.log('');
        log.bold('Largest files');
        const sorted = [...result.files].sort((a, b) => b.lines - a.lines).slice(0, 10);
        for (const f of sorted) {
          console.log(`  ${String(f.lines).padStart(6)} lines  ${f.filepath}`);
        }
      }

      console.log('');
      log.dim('Run `mpga sync` to generate the full knowledge layer from this scan.');
    });
}
