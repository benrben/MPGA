import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import { log } from '../core/logger.js';
import { findProjectRoot, loadConfig } from '../core/config.js';
import { scan } from '../core/scanner.js';
import { buildGraph, renderGraphMd } from '../generators/graph-md.js';

export function registerGraph(program: Command): void {
  const cmd = program.command('graph').description('Dependency graph management');

  cmd
    .command('show')
    .description('Print dependency graph to terminal')
    .action(async () => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const graphPath = path.join(projectRoot, 'MPGA', 'GRAPH.md');

      if (!fs.existsSync(graphPath)) {
        log.error('GRAPH.md not found. Run `mpga sync` first.');
        process.exit(1);
      }

      console.log(fs.readFileSync(graphPath, 'utf-8'));
    });

  cmd
    .command('export')
    .description('Export dependency graph')
    .option('--mermaid', 'Export as mermaid diagram')
    .option('--json', 'Export as JSON')
    .action(async (opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const config = loadConfig(projectRoot);

      log.info('Building dependency graph...');
      const scanResult = await scan(projectRoot, config.project.ignore, false);
      const graph = await buildGraph(scanResult, config);

      if (opts.json) {
        console.log(JSON.stringify(graph, null, 2));
        return;
      }

      if (opts.mermaid) {
        const lines = ['```mermaid', 'graph TD'];
        const seen = new Set<string>();
        for (const { from, to } of graph.dependencies) {
          const key = `${from}-->${to}`;
          if (!seen.has(key)) {
            seen.add(key);
            lines.push(
              `    ${from.replace(/[^a-zA-Z0-9_]/g, '_')} --> ${to.replace(/[^a-zA-Z0-9_]/g, '_')}`,
            );
          }
        }
        lines.push('```');
        console.log(lines.join('\n'));
        return;
      }

      // Default: print text version
      const md = renderGraphMd(graph);
      console.log(md);
    });
}
