import { Command } from 'commander';
import { log } from '../core/logger.js';

export function registerShortcuts(program: Command): void {
  program
    .command('diagnose [files...]')
    .description('Run bug-hunter + optimizer diagnosis')
    .action((files: string[]) => {
      log.header('Diagnose');
      if (files.length > 0) {
        console.log(`  Target files: ${files.join(', ')}`);
      }
      console.log('  Use /mpga:diagnose to run bug-hunter + optimizer in your AI coding agent.');
      log.dim('  This skill analyzes code for bugs, performance issues, and optimization opportunities.');
    });

  program
    .command('secure')
    .description('Run security audit')
    .action(() => {
      log.header('Secure');
      console.log('  Use /mpga:secure to run a security audit in your AI coding agent.');
      log.dim('  This skill scans for vulnerabilities, insecure patterns, and secrets exposure.');
    });

  program
    .command('simplify [files...]')
    .description('Improve code elegance')
    .action((files: string[]) => {
      log.header('Simplify');
      if (files.length > 0) {
        console.log(`  Target files: ${files.join(', ')}`);
      }
      console.log('  Use /mpga:simplify to improve code elegance in your AI coding agent.');
      log.dim('  This skill reduces complexity, removes duplication, and improves readability.');
    });
}
