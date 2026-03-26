import { Command } from 'commander';
import chalk from 'chalk';
import { banner, VERSION } from './core/logger.js';
import { registerInit } from './commands/init.js';
import { registerScan } from './commands/scan.js';
import { registerSync } from './commands/sync.js';
import { registerScope } from './commands/scope.js';
import { registerEvidence } from './commands/evidence.js';
import { registerDrift } from './commands/drift.js';
import { registerGraph } from './commands/graph.js';
import { registerMilestone } from './commands/milestone.js';
import { registerSession } from './commands/session.js';
import { registerHealth } from './commands/health.js';
import { registerBoard } from './commands/board.js';
import { registerStatus } from './commands/status.js';
import { registerConfig } from './commands/config.js';
import { registerExport } from './commands/export.js';
import { registerDevelop } from './commands/develop.js';
import { registerShortcuts } from './commands/shortcuts.js';
import { registerMetrics } from './commands/metrics.js';
import { registerPr } from './commands/pr.js';
import { registerSpoke } from './commands/spoke.js';

export function createCli(): Command {
  const program = new Command();

  program
    .name('mpga')
    .description('Evidence-backed context engineering for AI-assisted development')
    .version(VERSION, '-v, --version', 'Show MPGA version')
    .configureHelp({
      sortSubcommands: true,
      subcommandTerm: (cmd) => chalk.hex('#FF4444')(cmd.name()) + ' ' + chalk.dim(cmd.usage()),
    })
    .addHelpText('before', () => {
      banner();
      return '';
    })
    .addHelpText('after', () => {
      return `
${chalk.dim('  Examples:')}
    $ mpga init --from-existing    Bootstrap from existing codebase
    $ mpga sync                    Generate knowledge layer
    $ mpga status                  View project health dashboard
    $ mpga drift                   Check evidence integrity
    $ mpga export --cursor         Export for Cursor / Windsurf

${chalk.dim('  Docs:')}  ${chalk.underline('https://github.com/benreich/mpga')}
`;
    });

  // ── Core workflow ──
  registerInit(program);
  registerScan(program);
  registerSync(program);
  registerStatus(program);
  registerHealth(program);

  // ── Evidence & drift ──
  registerEvidence(program);
  registerDrift(program);

  // ── Knowledge layer ──
  registerScope(program);
  registerGraph(program);

  // ── Project management ──
  registerBoard(program);
  registerDevelop(program);
  registerMilestone(program);
  registerSession(program);

  // ── Configuration & export ──
  registerConfig(program);
  registerExport(program);

  // ── Metrics & changelog ──
  registerMetrics(program);

  // ── PR & decisions ──
  registerPr(program);

  // ── Voice ──
  registerSpoke(program);

  // ── Shortcuts (skill pointers) ──
  registerShortcuts(program);

  return program;
}
