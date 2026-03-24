import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import { log } from '../core/logger.js';
import { findProjectRoot, loadConfig } from '../core/config.js';
import { findPluginRoot } from './export/agents.js';
import { exportClaude } from './export/claude.js';
import { exportCursor } from './export/cursor.js';
import { exportCodex } from './export/codex.js';
import { exportAntigravity } from './export/antigravity.js';

// ─── Main export command ──────────────────────────────────────────────────────

export function registerExport(program: Command): void {
  program
    .command('export')
    .description('Export knowledge layer for other AI tools')
    .option('--claude', 'Generate CLAUDE.md + .claude/skills/ for Claude Code')
    .option('--cursor', 'Generate .cursor/rules/*.mdc + .cursor/skills/ + .cursor/agents/')
    .option('--codex', 'Generate AGENTS.md + .codex/skills/ + .codex/agents/*.toml')
    .option(
      '--antigravity',
      'Generate GEMINI.md + .agent/skills/ + .antigravity/rules/ + .agents/workflows/',
    )
    .option('--all', 'Generate for all tools')
    .option('--global', 'Generate user-level config instead of project config')
    .option('--workflows', 'Include workflow files (Antigravity)')
    .option('--knowledge', 'Seed Knowledge Items from MPGA/scopes/ (Antigravity)')
    // Legacy aliases
    .option('--cursorrules', 'Deprecated alias for --cursor')
    .option('--gemini', 'Deprecated alias for --codex')
    .option('--opencode', 'Generate .opencode/ directory (legacy)')
    .action((opts) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const mpgaDir = path.join(projectRoot, 'MPGA');
      const config = loadConfig(projectRoot);
      const pluginRoot = findPluginRoot();

      if (!fs.existsSync(mpgaDir)) {
        log.error('MPGA not initialized. Run `mpga init` first.');
        process.exit(1);
      }

      const indexPath = path.join(mpgaDir, 'INDEX.md');
      const indexContent = fs.existsSync(indexPath) ? fs.readFileSync(indexPath, 'utf-8') : '';
      const projectName = config.project.name;

      let exported = 0;
      const doAll = opts.all;

      // ── Claude Code ──────────────────────────────────────────────────────────
      if (opts.claude || doAll) {
        exportClaude(projectRoot, indexContent, projectName, pluginRoot, !!opts.global);
        exported++;
      }

      // ── Cursor ───────────────────────────────────────────────────────────────
      if (opts.cursor || opts.cursorrules || doAll) {
        if (opts.cursorrules) log.warn('--cursorrules is deprecated. Use --cursor.');
        exportCursor(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, !!opts.global);
        exported++;
      }

      // ── Codex / Gemini CLI ───────────────────────────────────────────────────
      if (opts.codex || opts.gemini || doAll) {
        if (opts.gemini) log.warn('--gemini is deprecated. Use --codex.');
        exportCodex(projectRoot, mpgaDir, indexContent, projectName, pluginRoot, !!opts.global);
        exported++;
      }

      // ── Antigravity ──────────────────────────────────────────────────────────
      if (opts.antigravity || doAll) {
        exportAntigravity(
          projectRoot,
          mpgaDir,
          indexContent,
          projectName,
          pluginRoot,
          !!opts.global,
          {
            knowledge: opts.knowledge,
          },
        );
        exported++;
      }

      // ── Legacy --opencode ────────────────────────────────────────────────────
      if (opts.opencode) {
        const openCodeDir = path.join(projectRoot, '.opencode');
        fs.mkdirSync(openCodeDir, { recursive: true });
        fs.writeFileSync(path.join(openCodeDir, 'context.md'), indexContent);
        log.success('Generated .opencode/context.md');
        exported++;
      }

      if (exported === 0) {
        log.info('Specify an export target: --claude, --cursor, --codex, --antigravity, --all');
        log.info('Add --global for user-level config.');
        log.info('Add --workflows for Antigravity workflow files.');
        log.info('Add --knowledge to seed Antigravity Knowledge Items from scopes.');
      }
    });
}
