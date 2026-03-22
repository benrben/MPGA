import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import { log } from '../core/logger.js';
import { loadConfig, saveConfig, getConfigValue, setConfigValue, findProjectRoot } from '../core/config.js';

export function registerConfig(program: Command): void {
  const cmd = program
    .command('config')
    .description('View and update MPGA configuration');

  cmd
    .command('show')
    .description('Display current configuration')
    .option('--json', 'Output as JSON')
    .action((opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const config = loadConfig(projectRoot);

      if (opts.json) {
        console.log(JSON.stringify(config, null, 2));
        return;
      }

      log.header('MPGA Configuration');
      const lines = flattenConfig(config);
      for (const [key, value] of lines) {
        console.log(`  ${key.padEnd(45)} ${String(value)}`);
      }
    });

  cmd
    .command('set <key> <value>')
    .description('Update a configuration value (e.g. drift.ciThreshold 90)')
    .action((key: string, value: string) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const config = loadConfig(projectRoot);

      const configPath = fs.existsSync(path.join(projectRoot, 'mpga.config.json'))
        ? path.join(projectRoot, 'mpga.config.json')
        : path.join(projectRoot, 'MPGA', 'mpga.config.json');

      if (!fs.existsSync(configPath)) {
        log.error('No mpga.config.json found. Run `mpga init` first.');
        process.exit(1);
      }

      const before = getConfigValue(config, key);
      if (before === undefined) {
        log.error(`Unknown config key: ${key}`);
        process.exit(1);
      }

      setConfigValue(config, key, value);
      saveConfig(config, configPath);

      log.success(`${key}: ${String(before)} → ${String(getConfigValue(config, key))}`);
    });
}

function flattenConfig(obj: unknown, prefix = ''): [string, unknown][] {
  if (typeof obj !== 'object' || obj === null) return [[prefix, obj]];
  const result: [string, unknown][] = [];
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    const fullKey = prefix ? `${prefix}.${k}` : k;
    if (typeof v === 'object' && v !== null && !Array.isArray(v)) {
      result.push(...flattenConfig(v, fullKey));
    } else {
      result.push([fullKey, Array.isArray(v) ? v.join(', ') : v]);
    }
  }
  return result;
}
