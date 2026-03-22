import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import { log } from '../core/logger.js';
import { findProjectRoot, loadConfig } from '../core/config.js';

// ─── Agent metadata ───────────────────────────────────────────────────────────
// Canonical list of MPGA agents with their per-tool attributes.
// The markdown instructions live in mpga-plugin/agents/<slug>.md.

interface AgentMeta {
  slug: string;           // filename slug (e.g. "green-dev")
  name: string;           // display name
  description: string;    // one-line description for agent routing
  model: string;          // preferred model
  readonly: boolean;      // Cursor: cannot write files
  isBackground: boolean;  // Cursor: can run in parallel
  sandboxMode: string;    // Codex: workspace | none
}

const AGENTS: AgentMeta[] = [
  {
    slug: 'green-dev',
    name: 'mpga-green-dev',
    description: 'Write failing tests FIRST for a task. Use at the start of every TDD cycle. Never writes implementation code.',
    model: 'claude-sonnet-4-6',
    readonly: false,
    isBackground: false,
    sandboxMode: 'workspace',
  },
  {
    slug: 'red-dev',
    name: 'mpga-red-dev',
    description: 'Write minimal implementation to make a failing test pass. Use after green-dev has written tests. Never modifies tests.',
    model: 'claude-sonnet-4-6',
    readonly: false,
    isBackground: false,
    sandboxMode: 'workspace',
  },
  {
    slug: 'blue-dev',
    name: 'mpga-blue-dev',
    description: 'Refactor passing code for quality without changing behavior. Use after red-dev. Updates evidence links in scope docs.',
    model: 'claude-sonnet-4-6',
    readonly: false,
    isBackground: false,
    sandboxMode: 'workspace',
  },
  {
    slug: 'scout',
    name: 'mpga-scout',
    description: 'Read-only codebase explorer. Traces execution paths, maps dependencies, and builds evidence links. Never modifies files.',
    model: 'claude-sonnet-4-6',
    readonly: true,
    isBackground: true,
    sandboxMode: 'none',
  },
  {
    slug: 'architect',
    name: 'mpga-architect',
    description: 'Structural analysis agent. Generates and updates GRAPH.md and scope docs from scout findings. Every claim must cite evidence.',
    model: 'claude-opus-4-6',
    readonly: false,
    isBackground: false,
    sandboxMode: 'workspace',
  },
  {
    slug: 'auditor',
    name: 'mpga-auditor',
    description: 'Evidence integrity checker. Verifies evidence links resolve, flags stale links, calculates scope health. Read-only — only flags, never auto-fixes.',
    model: 'claude-sonnet-4-6',
    readonly: true,
    isBackground: true,
    sandboxMode: 'none',
  },
  {
    slug: 'researcher',
    name: 'mpga-researcher',
    description: 'Domain research before planning. Reads scope docs, identifies knowledge gaps, investigates library options and pitfalls.',
    model: 'claude-opus-4-6',
    readonly: true,
    isBackground: false,
    sandboxMode: 'none',
  },
  {
    slug: 'reviewer',
    name: 'mpga-reviewer',
    description: 'Two-stage code reviewer. Stage 1: spec compliance + evidence validity. Stage 2: code quality + security. Critical issues block progress.',
    model: 'claude-opus-4-6',
    readonly: true,
    isBackground: false,
    sandboxMode: 'none',
  },
  {
    slug: 'verifier',
    name: 'mpga-verifier',
    description: 'Post-execution verification. Runs test suite, checks for stubs, verifies evidence links updated, confirms milestone progress.',
    model: 'claude-sonnet-4-6',
    readonly: true,
    isBackground: false,
    sandboxMode: 'workspace',
  },
];

const SKILL_NAMES = [
  'sync-project', 'brainstorm', 'plan', 'develop', 'drift-check',
  'ask', 'onboard', 'ship', 'handoff', 'map-codebase',
];

// ─── Plugin root finder ───────────────────────────────────────────────────────

function findPluginRoot(): string | null {
  // When running from compiled CLI at mpga-plugin/cli/dist/commands/export.js,
  // __dirname is dist/commands/ — plugin root is three levels up: ../../..
  const candidate = path.resolve(__dirname, '../../..');
  if (fs.existsSync(path.join(candidate, 'skills')) && fs.existsSync(path.join(candidate, 'agents'))) {
    return candidate;
  }
  // Fallback: MPGA_PLUGIN_ROOT env var (set by bin/mpga.sh as PLUGIN_ROOT)
  const envRoot = process.env.MPGA_PLUGIN_ROOT ?? process.env.PLUGIN_ROOT;
  if (envRoot && fs.existsSync(path.join(envRoot, 'skills'))) {
    return envRoot;
  }
  return null;
}

// ─── Skills copying ───────────────────────────────────────────────────────────

/**
 * Copy or recreate SKILL.md packages from the plugin's skills/ directory
 * into the target tool's skills directory.
 */
function copySkillsTo(targetSkillsDir: string, pluginRoot: string | null, toolName: string): void {
  fs.mkdirSync(targetSkillsDir, { recursive: true });

  for (const skillName of SKILL_NAMES) {
    const destDir = path.join(targetSkillsDir, `mpga-${skillName}`);
    fs.mkdirSync(destDir, { recursive: true });

    if (pluginRoot) {
      const srcDir = path.join(pluginRoot, 'skills', skillName);
      if (fs.existsSync(srcDir)) {
        copyDir(srcDir, destDir, toolName);
        continue;
      }
    }

    // Fallback: write a minimal SKILL.md if plugin root not available
    if (!fs.existsSync(path.join(destDir, 'SKILL.md'))) {
      fs.writeFileSync(
        path.join(destDir, 'SKILL.md'),
        generateFallbackSkillMd(skillName)
      );
    }
  }
}

function copyDir(src: string, dest: string, toolName: string): void {
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      fs.mkdirSync(destPath, { recursive: true });
      copyDir(srcPath, destPath, toolName);
    } else {
      let content = fs.readFileSync(srcPath, 'utf-8');
      // Rewrite CLAUDE_PLUGIN_ROOT references to use npx mpga for non-Claude tools
      if (toolName !== 'claude') {
        content = content.replace(/\$\{CLAUDE_PLUGIN_ROOT\}\/bin\/mpga\.sh/g, 'npx mpga');
      }
      fs.writeFileSync(destPath, content);
    }
  }
}

function generateFallbackSkillMd(skillName: string): string {
  const descriptions: Record<string, string> = {
    'sync-project': 'Rebuild the MPGA knowledge layer from the current codebase state',
    'brainstorm': 'Socratic design refinement before writing any code',
    'plan': 'Generate an evidence-based task breakdown for a milestone',
    'develop': 'Orchestrate the TDD cycle for a task (green → red → blue → review)',
    'drift-check': 'Validate evidence links and detect stale scope docs',
    'ask': 'Answer questions about the codebase using MPGA scope docs as citations',
    'onboard': 'Guided tour of the codebase using the MPGA knowledge layer',
    'ship': 'Verify, commit, update evidence, and advance milestone',
    'handoff': 'Export session state for cross-context continuity',
    'map-codebase': 'Parallel scout agents analyze the full codebase and generate scopes',
  };

  return `---
description: ${descriptions[skillName] ?? skillName}
---

## ${skillName}

See MPGA documentation for full protocol.

Run \`npx mpga ${skillName.replace('-', ' ')}\` for CLI equivalent.
`;
}

// ─── Agent file generators ────────────────────────────────────────────────────

function readAgentInstructions(pluginRoot: string | null, slug: string): string {
  if (pluginRoot) {
    const agentPath = path.join(pluginRoot, 'agents', `${slug}.md`);
    if (fs.existsSync(agentPath)) {
      // Strip the H1 title line — it becomes redundant with the YAML frontmatter
      return fs.readFileSync(agentPath, 'utf-8').replace(/^# Agent:.*\n/, '').trimStart();
    }
  }
  return `See MPGA documentation for full ${slug} agent protocol.`;
}

/** Generate Cursor-format agent markdown (.cursor/agents/mpga-<slug>.md) */
function generateCursorAgentMd(agent: AgentMeta, pluginRoot: string | null): string {
  const instructions = readAgentInstructions(pluginRoot, agent.slug)
    // Rewrite plugin-root-relative CLI calls to npx mpga
    .replace(/\$\{CLAUDE_PLUGIN_ROOT\}\/bin\/mpga\.sh/g, 'npx mpga');

  return `---
name: ${agent.name}
description: ${agent.description}
model: ${agent.model}
readonly: ${agent.readonly}
is_background: ${agent.isBackground}
---

${instructions}`;
}

/** Generate Codex-format TOML agent (.codex/agents/mpga-<slug>.toml) */
function generateCodexAgentToml(agent: AgentMeta, pluginRoot: string | null): string {
  const instructions = readAgentInstructions(pluginRoot, agent.slug)
    .replace(/\$\{CLAUDE_PLUGIN_ROOT\}\/bin\/mpga\.sh/g, 'npx mpga')
    // Escape double-quotes and backslashes for TOML triple-quoted strings
    .replace(/\\/g, '\\\\')
    .replace(/"""/g, '\\"\\"\\"');

  return `name = "${agent.name}"
description = "${agent.description.replace(/"/g, '\\"')}"
model = "${agent.model}"
sandbox_mode = "${agent.sandboxMode}"

developer_instructions = """
${instructions}
"""
`;
}

// ─── Main export command ──────────────────────────────────────────────────────

export function registerExport(program: Command): void {
  program
    .command('export')
    .description('Export knowledge layer for other AI tools')
    .option('--claude', 'Generate CLAUDE.md + .claude/skills/ for Claude Code')
    .option('--cursor', 'Generate .cursor/rules/*.mdc + .cursor/skills/ + .cursor/agents/')
    .option('--codex', 'Generate AGENTS.md + .codex/skills/ + .codex/agents/*.toml')
    .option('--antigravity', 'Generate GEMINI.md + .agent/skills/ + .antigravity/rules/ + .agents/workflows/')
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
        if (opts.global) {
          log.info('Append the following to ~/.claude/CLAUDE.md:');
          log.info('\n' + generateClaudeGlobal());
          deployClaudePlugin(path.join(process.env.HOME ?? '~', '.claude'), pluginRoot, projectRoot, true);
        } else {
          fs.writeFileSync(path.join(projectRoot, 'CLAUDE.md'), generateClaudeMd(indexContent, projectName));
          log.success('Generated CLAUDE.md');
          deployClaudePlugin(path.join(projectRoot, '.claude'), pluginRoot, projectRoot, false);
        }
        exported++;
      }

      // ── Cursor ───────────────────────────────────────────────────────────────
      if (opts.cursor || opts.cursorrules || doAll) {
        if (opts.cursorrules) log.warn('--cursorrules is deprecated. Use --cursor.');

        if (opts.global) {
          log.info('Add the following to Cursor Settings > General > Rules for AI:');
          log.info('\n' + generateCursorGlobal());
          const globalSkillsDir = path.join(process.env.HOME ?? '~', '.cursor', 'skills');
          copySkillsTo(globalSkillsDir, pluginRoot, 'cursor');
          log.success(`Generated ~/.cursor/skills/ (${SKILL_NAMES.length} skills)`);
          // Global agents
          const globalAgentsDir = path.join(process.env.HOME ?? '~', '.cursor', 'agents');
          fs.mkdirSync(globalAgentsDir, { recursive: true });
          for (const agent of AGENTS) {
            fs.writeFileSync(
              path.join(globalAgentsDir, `${agent.name}.md`),
              generateCursorAgentMd(agent, pluginRoot)
            );
          }
          log.success(`Generated ~/.cursor/agents/ (${AGENTS.length} agents)`);
        } else {
          // Rules
          const rulesDir = path.join(projectRoot, '.cursor', 'rules');
          fs.mkdirSync(rulesDir, { recursive: true });
          fs.writeFileSync(path.join(rulesDir, 'mpga-project.mdc'), generateCursorProjectMdc(indexContent, projectName));
          fs.writeFileSync(path.join(rulesDir, 'mpga-evidence.mdc'), generateCursorEvidenceMdc());
          fs.writeFileSync(path.join(rulesDir, 'mpga-tdd.mdc'), generateCursorTddMdc());
          fs.writeFileSync(path.join(rulesDir, 'mpga-scopes.mdc'), generateCursorScopesMdc(mpgaDir));
          log.success('Generated .cursor/rules/ (4 MDC files)');
          // Skills
          const cursorSkillsDir = path.join(projectRoot, '.cursor', 'skills');
          copySkillsTo(cursorSkillsDir, pluginRoot, 'cursor');
          log.success(`.cursor/skills/ (${SKILL_NAMES.length} skills)`);
          // Agents
          const cursorAgentsDir = path.join(projectRoot, '.cursor', 'agents');
          fs.mkdirSync(cursorAgentsDir, { recursive: true });
          for (const agent of AGENTS) {
            fs.writeFileSync(
              path.join(cursorAgentsDir, `${agent.name}.md`),
              generateCursorAgentMd(agent, pluginRoot)
            );
          }
          log.success(`.cursor/agents/ (${AGENTS.length} agents)`);
        }
        exported++;
      }

      // ── Codex / Gemini CLI ───────────────────────────────────────────────────
      if (opts.codex || opts.gemini || doAll) {
        if (opts.gemini) log.warn('--gemini is deprecated. Use --codex.');

        if (opts.global) {
          const codexGlobalDir = path.join(process.env.HOME ?? '~', '.codex');
          fs.mkdirSync(codexGlobalDir, { recursive: true });
          fs.writeFileSync(path.join(codexGlobalDir, 'AGENTS.md'), generateCodexGlobalAgentsMd());
          log.success('Generated ~/.codex/AGENTS.md');
          const globalSkillsDir = path.join(codexGlobalDir, 'skills');
          copySkillsTo(globalSkillsDir, pluginRoot, 'codex');
          log.success(`Generated ~/.codex/skills/ (${SKILL_NAMES.length} skills)`);
          const globalAgentsDir = path.join(codexGlobalDir, 'agents');
          fs.mkdirSync(globalAgentsDir, { recursive: true });
          for (const agent of AGENTS) {
            fs.writeFileSync(
              path.join(globalAgentsDir, `${agent.name}.toml`),
              generateCodexAgentToml(agent, pluginRoot)
            );
          }
          log.success(`Generated ~/.codex/agents/ (${AGENTS.length} TOML agents)`);
        } else {
          // Root AGENTS.md
          fs.writeFileSync(path.join(projectRoot, 'AGENTS.md'), generateAgentsMd(indexContent, projectName));
          // MPGA layer nav guide
          fs.writeFileSync(path.join(mpgaDir, 'AGENTS.md'), generateMpgaLayerAgentsMd());
          // Subdirectory AGENTS.md files for detected scopes
          const scopesDir = path.join(mpgaDir, 'scopes');
          if (fs.existsSync(scopesDir)) generateSubdirAgentsMd(projectRoot, scopesDir);
          log.success('Generated AGENTS.md (root + MPGA/ + scope subdirs)');
          // Skills
          const codexSkillsDir = path.join(projectRoot, '.codex', 'skills');
          copySkillsTo(codexSkillsDir, pluginRoot, 'codex');
          log.success(`.codex/skills/ (${SKILL_NAMES.length} skills)`);
          // TOML agents
          const codexAgentsDir = path.join(projectRoot, '.codex', 'agents');
          fs.mkdirSync(codexAgentsDir, { recursive: true });
          for (const agent of AGENTS) {
            fs.writeFileSync(
              path.join(codexAgentsDir, `${agent.name}.toml`),
              generateCodexAgentToml(agent, pluginRoot)
            );
          }
          log.success(`.codex/agents/ (${AGENTS.length} TOML agents)`);
        }
        exported++;
      }

      // ── Antigravity ───────────────────────────────────────────────────────────
      if (opts.antigravity || doAll) {
        if (opts.global) {
          const agGlobalSkillsDir = path.join(process.env.HOME ?? '~', '.gemini', 'antigravity', 'skills');
          copySkillsTo(agGlobalSkillsDir, pluginRoot, 'antigravity');
          log.success(`Generated ~/.gemini/antigravity/skills/ (${SKILL_NAMES.length} skills)`);
          const agGlobalRulesDir = path.join(process.env.HOME ?? '~', '.antigravity', 'rules');
          fs.mkdirSync(agGlobalRulesDir, { recursive: true });
          fs.writeFileSync(path.join(agGlobalRulesDir, 'mpga-global.md'), generateAntigravityGlobal());
          log.success('Generated ~/.antigravity/rules/mpga-global.md');
        } else {
          // GEMINI.md constitution
          fs.writeFileSync(path.join(projectRoot, 'GEMINI.md'), generateGeminiMd(indexContent, projectName));
          log.success('Generated GEMINI.md');
          // Skills in .agent/skills/
          const agSkillsDir = path.join(projectRoot, '.agent', 'skills');
          copySkillsTo(agSkillsDir, pluginRoot, 'antigravity');
          log.success(`.agent/skills/ (${SKILL_NAMES.length} skills)`);
          // Rules in .antigravity/rules/
          const rulesDir = path.join(projectRoot, '.antigravity', 'rules');
          fs.mkdirSync(rulesDir, { recursive: true });
          fs.writeFileSync(path.join(rulesDir, 'mpga-context.md'), generateAntigravityContextMd(indexContent, projectName));
          fs.writeFileSync(path.join(rulesDir, 'mpga-evidence.md'), generateAntigravityEvidenceMd());
          fs.writeFileSync(path.join(rulesDir, 'mpga-tdd.md'), generateAntigravityTddMd());
          log.success('Generated .antigravity/rules/ (3 files)');
          // Workflows in .agents/workflows/ — always generated for antigravity
          const workflowsDir = path.join(projectRoot, '.agents', 'workflows');
          fs.mkdirSync(workflowsDir, { recursive: true });
          fs.writeFileSync(path.join(workflowsDir, 'mpga-plan.md'), generateAntigravityPlanWorkflow());
          fs.writeFileSync(path.join(workflowsDir, 'mpga-develop.md'), generateAntigravityDevelopWorkflow());
          fs.writeFileSync(path.join(workflowsDir, 'mpga-review.md'), generateAntigravityReviewWorkflow());
          log.success('Generated .agents/workflows/ (3 workflow files)');
          // Knowledge Items seeding
          if (opts.knowledge) {
            const scopesDir = path.join(mpgaDir, 'scopes');
            if (fs.existsSync(scopesDir)) {
              seedAntigravityKnowledgeItems(projectRoot, scopesDir);
              log.success('Seeded Knowledge Items from MPGA/scopes/');
            }
          }
        }
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

// ─── Claude Code generators ───────────────────────────────────────────────────

// Deploy the full MPGA plugin into a .claude/ directory:
//   skills/mpga-<name>/SKILL.md  (10 skills)
//   agents/<slug>.md             (9 agents)
//   commands/<cmd>.md            (12 /mpga:* commands)
//   settings.json                (hooks merged with existing)
function deployClaudePlugin(claudeDir: string, pluginRoot: string | null, projectRoot: string, isGlobal: boolean): void {
  fs.mkdirSync(claudeDir, { recursive: true });

  // Skills
  copySkillsTo(path.join(claudeDir, 'skills'), pluginRoot, 'claude');
  log.success(`.claude/skills/ (${SKILL_NAMES.length} skills)`);

  if (!pluginRoot) {
    log.warn('Plugin root not found — skipping agents, commands, and hooks. Set MPGA_PLUGIN_ROOT to fix.');
    return;
  }

  // Agents
  const agentsSrc = path.join(pluginRoot, 'agents');
  const agentsDest = path.join(claudeDir, 'agents');
  if (fs.existsSync(agentsSrc)) {
    fs.mkdirSync(agentsDest, { recursive: true });
    for (const f of fs.readdirSync(agentsSrc).filter(n => n.endsWith('.md'))) {
      fs.copyFileSync(path.join(agentsSrc, f), path.join(agentsDest, f));
    }
    log.success(`.claude/agents/ (${fs.readdirSync(agentsSrc).filter(n => n.endsWith('.md')).length} agents)`);
  }

  // Commands (project-scoped only — global commands go in ~/.claude/commands/)
  if (!isGlobal) {
    const commandsSrc = path.join(pluginRoot, 'commands');
    const commandsDest = path.join(claudeDir, 'commands');
    if (fs.existsSync(commandsSrc)) {
      fs.mkdirSync(commandsDest, { recursive: true });
      for (const f of fs.readdirSync(commandsSrc).filter(n => n.endsWith('.md'))) {
        fs.copyFileSync(path.join(commandsSrc, f), path.join(commandsDest, f));
      }
      log.success(`.claude/commands/ (${fs.readdirSync(commandsSrc).filter(n => n.endsWith('.md')).length} /mpga:* commands)`);
    }
  }

  // Hooks → merged into settings.json
  const hooksSrc = path.join(pluginRoot, 'hooks', 'hooks.json');
  if (fs.existsSync(hooksSrc)) {
    const settingsPath = path.join(claudeDir, 'settings.json');
    const hooks = JSON.parse(fs.readFileSync(hooksSrc, 'utf-8'));

    // Replace ${CLAUDE_PLUGIN_ROOT} with the actual plugin path
    const hooksStr = JSON.stringify(hooks).replace(
      /\$\{CLAUDE_PLUGIN_ROOT\}/g,
      pluginRoot.replace(/\\/g, '/')
    );
    const resolvedHooks = JSON.parse(hooksStr);

    let settings: Record<string, unknown> = {};
    if (fs.existsSync(settingsPath)) {
      try { settings = JSON.parse(fs.readFileSync(settingsPath, 'utf-8')); } catch { /* ignore */ }
    }
    // Merge hooks (append PostToolUse entries, don't duplicate)
    const existing = (settings.hooks as Record<string, unknown[]> | undefined) ?? {};
    for (const [event, entries] of Object.entries(resolvedHooks.hooks ?? {})) {
      const existingEntries = (existing[event] as unknown[] | undefined) ?? [];
      existing[event] = [...existingEntries, ...(entries as unknown[])];
    }
    settings.hooks = existing;
    fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2));
    log.success('.claude/settings.json (hooks configured)');
  }
}

function generateClaudeMd(indexContent: string, projectName: string): string {
  const milestonesMatch = indexContent.match(/## Active milestone\n([\s\S]*?)(?=\n##|$)/);
  const milestone = milestonesMatch ? milestonesMatch[1].trim() : '(none)';

  return `# MPGA-Managed Project Context

This project uses MPGA for evidence-backed context engineering.
Do NOT edit this file manually — generated from MPGA/INDEX.md.
Run \`mpga sync && mpga export --claude\` to update.

## Key rules
- ALWAYS read MPGA/INDEX.md before starting any task
- ALWAYS cite evidence links [E] when making claims about code
- NEVER write implementation before tests (TDD enforced)
- Mark anything unverified as [Unknown]

## Available MPGA commands
- /mpga:status — project health dashboard
- /mpga:board — task board
- /mpga:plan — evidence-based planning
- /mpga:execute — TDD cycle execution
- /mpga:quick "<task>" — ad-hoc task with TDD

## Scope registry
Read MPGA/INDEX.md for the full scope registry and agent trigger table.

## Active milestone
${milestone}

Generated: ${new Date().toISOString()}
`;
}

function generateClaudeGlobal(): string {
  return `## MPGA Global Rules

When you detect an MPGA/ directory in any project:
1. Read MPGA/INDEX.md first — it is the project's truth map
2. Use evidence links [E] to ground every code claim
3. Mark unknowns explicitly as [Unknown]
4. Follow the TDD cycle: green-dev → red-dev → blue-dev
5. Check MPGA/board/BOARD.md for current task state
6. Run \`mpga drift --quick\` after modifying files
7. Update scope docs when code changes affect evidence links
`;
}

// ─── Cursor generators ────────────────────────────────────────────────────────

function generateCursorProjectMdc(indexContent: string, projectName: string): string {
  const milestonesMatch = indexContent.match(/## Active milestone\n([\s\S]*?)(?=\n##|$)/);
  const milestone = milestonesMatch ? milestonesMatch[1].trim() : '(none)';

  return `---
description: "MPGA project context — evidence-backed navigation layer"
globs:
alwaysApply: true
---

# MPGA Project Context

This project uses MPGA for evidence-backed context engineering.

## Before writing ANY code
1. Read MPGA/INDEX.md for the project map and scope registry
2. Find the relevant scope doc in MPGA/scopes/ for the area you're working in
3. Check MPGA/board/BOARD.md for current task assignments

## Evidence rules
- Every claim about how code works MUST cite a file:line evidence link
- Format: [E] src/auth/jwt.ts:42-67 :: validateToken()
- If you cannot find evidence → mark as [Unknown]
- Never guess — look it up or mark it unknown

## Key files
@MPGA/INDEX.md

## Active milestone
${milestone}

Generated: ${new Date().toISOString()}
`;
}

function generateCursorEvidenceMdc(): string {
  return `---
description: "MPGA evidence link conventions — format and verification rules"
globs:
alwaysApply: true
---

# Evidence Link Protocol

## Format
\`\`\`
[E] filepath:startLine-endLine :: symbolName()    # exact range + AST anchor (preferred)
[E] filepath :: symbolName                         # AST-only, resilient to line shifts
[Unknown] description                              # explicitly unknown — never guess
[Stale:YYYY-MM-DD] filepath:range                 # was valid, needs re-verification
\`\`\`

## When to use
- Before touching code: read the relevant scope doc in MPGA/scopes/
- After changing code: check if evidence links in the scope doc still resolve
- When in doubt: mark [Unknown]

## Verification
\`\`\`bash
npx mpga evidence verify       # check all links
npx mpga drift --quick         # fast staleness check
npx mpga evidence heal --auto  # auto-fix broken links via AST
\`\`\`
`;
}

function generateCursorTddMdc(): string {
  return `---
description: "MPGA TDD enforcement — write tests before implementation"
globs:
alwaysApply: true
---

# TDD Protocol (mandatory)

1. WRITE FAILING TEST FIRST — never write implementation before a test exists
2. Run test — confirm it FAILS (red)
3. Write MINIMAL implementation to pass (green)
4. Refactor without changing behavior (blue)
5. Update evidence links in the relevant MPGA/scopes/*.md file

If you find yourself writing implementation code without a test:
STOP. Delete it. Write the test first.
`;
}

function generateCursorScopesMdc(mpgaDir: string): string {
  const scopesDir = path.join(mpgaDir, 'scopes');
  let scopeLines = '- (no scopes yet — run `mpga sync` to generate)';

  if (fs.existsSync(scopesDir)) {
    const scopes = fs.readdirSync(scopesDir)
      .filter(f => f.endsWith('.md'))
      .map(f => f.replace('.md', ''));
    if (scopes.length > 0) {
      scopeLines = scopes.map(s => `- ${s} → @MPGA/scopes/${s}.md`).join('\n');
    }
  }

  return `---
description: "Load MPGA scope documents when working on specific features. Use when the user asks about a specific feature area or module."
globs:
alwaysApply: false
---

# MPGA Scope Lookup

When working on a specific feature, load the relevant scope document:

${scopeLines}

Each scope doc contains:
- Evidence links proving how the feature actually works
- Known unknowns (explicitly marked)
- Dependencies to other scopes
- Drift status (are the evidence links still valid?)

Always check the scope BEFORE making changes.
`;
}

function generateCursorGlobal(): string {
  return `When you see an MPGA/ directory in any project:
- Read MPGA/INDEX.md before starting any task
- Use evidence links [E] format: [E] file:line :: symbol()
- Mark unknowns as [Unknown] — never guess
- Follow TDD: test first, implement second, refactor third
- Check MPGA/board/BOARD.md for task assignments
- After modifying code, consider if evidence links need updating
- Prefer reading scope docs over scanning entire directories`;
}

// ─── Codex / Gemini CLI generators ───────────────────────────────────────────

function generateAgentsMd(indexContent: string, projectName: string): string {
  return `# MPGA — Evidence-Backed Context Engineering

This project uses MPGA to maintain a verified knowledge layer.
The AI's "map" of this codebase lives in the MPGA/ directory.

## Before any task
1. Read MPGA/INDEX.md — it's the project truth map
2. Check MPGA/board/BOARD.md — see what's in progress
3. Find the relevant MPGA/scopes/*.md for the feature area

## Evidence link protocol
- Every code claim MUST cite evidence: [E] file:line :: symbol()
- Unknown things get marked: [Unknown] description
- Stale evidence: [Stale:date] file:line
- After making code changes, verify affected evidence links

## TDD protocol (mandatory)
1. Write failing test FIRST
2. Implement minimal code to pass
3. Refactor without changing behavior
4. Update MPGA scope docs with new evidence links

## Task board
Current tasks tracked in MPGA/board/BOARD.md
Task cards in MPGA/board/tasks/T*.md

## Verification commands
- Run tests: npm test
- Check evidence: npx mpga evidence verify
- Check drift: npx mpga drift --quick
- Board status: npx mpga board show

## Project structure
See MPGA/INDEX.md for complete file registry with evidence links.
See MPGA/GRAPH.md for module dependency graph.

---
*Generated by MPGA ${new Date().toISOString()}. Source: MPGA/INDEX.md*

${indexContent}
`;
}

function generateMpgaLayerAgentsMd(): string {
  return `# MPGA Knowledge Layer — Navigation Guide

This directory is the MPGA knowledge layer — the AI's verified map of the codebase.

## Reading order (tiered loading)
1. **Tier 1 — hot (always read first):** INDEX.md
2. **Tier 2 — warm (read per task):** GRAPH.md, scopes/<relevant>.md
3. **Tier 3 — cold (on demand):** sessions/, milestones/, board/tasks/

## File purposes
| File | Purpose |
|------|---------|
| INDEX.md | Project truth map — identity, key files, conventions, scope registry |
| GRAPH.md | Module dependency graph |
| scopes/*.md | Feature/capability docs with evidence links |
| board/BOARD.md | Human-readable task board |
| board/board.json | Machine-readable board state |
| board/tasks/T*.md | Individual task cards with TDD trace |
| milestones/ | Milestone plans, context, summaries |
| sessions/ | Session handoff documents |

## Evidence link format
\`\`\`
[E] filepath:startLine-endLine :: symbolName()   # verified, preferred
[E] filepath :: symbolName                        # AST-only, resilient
[Unknown] description                             # explicitly unknown
[Stale:YYYY-MM-DD] filepath:range                # needs re-verification
\`\`\`

Do NOT modify files in this directory manually. Use:
- \`mpga sync\` to regenerate the knowledge layer
- \`mpga evidence heal\` to fix stale evidence links
- \`mpga board add/move\` to manage tasks
`;
}

function generateSubdirAgentsMd(projectRoot: string, scopesDir: string): void {
  const scopes = fs.readdirSync(scopesDir).filter(f => f.endsWith('.md'));
  for (const scopeFile of scopes) {
    const scopeName = scopeFile.replace('.md', '');
    const scopeContent = fs.readFileSync(path.join(scopesDir, scopeFile), 'utf-8');
    const evidenceLinks = (scopeContent.match(/\[E\] .+/g) ?? []).slice(0, 5);
    const evidenceSection = evidenceLinks.length > 0
      ? evidenceLinks.map(l => `- ${l}`).join('\n')
      : '- (run `mpga sync` to populate evidence links)';

    const srcDir = path.join(projectRoot, 'src', scopeName);
    if (!fs.existsSync(srcDir)) continue;

    fs.writeFileSync(path.join(srcDir, 'AGENTS.md'), `# ${scopeName} Module — MPGA Scope

For detailed evidence-backed documentation of this module,
read: MPGA/scopes/${scopeName}.md

## Key evidence
${evidenceSection}

## Dependencies
See MPGA/scopes/${scopeName}.md for full dependency graph.
`);
  }
}

function generateCodexGlobalAgentsMd(): string {
  return `# MPGA Methodology (Global)

When working in ANY project that contains an MPGA/ directory:

## Core principles
- Evidence over claims: every code assertion must cite [E] file:line
- Unknown is honest: mark gaps as [Unknown], never guess
- TDD is mandatory: test → implement → refactor → update evidence
- Tiered reading: INDEX.md first, scope docs second, deep docs only if needed

## Workflow
1. Read MPGA/INDEX.md for project map
2. Check MPGA/board/BOARD.md for current tasks
3. Load relevant MPGA/scopes/*.md before touching code
4. After changes: update evidence links in scope docs
5. Run \`npx mpga drift --quick\` to verify nothing broke

## Evidence link format
[E] filepath:startLine-endLine :: symbolName()
[E] filepath :: symbolName (AST-only, resilient)
[Unknown] description (explicitly unknown)
[Stale:YYYY-MM-DD] filepath:range (was valid, needs verification)
`;
}

// ─── Antigravity generators ───────────────────────────────────────────────────

function generateGeminiMd(indexContent: string, projectName: string): string {
  const milestonesMatch = indexContent.match(/## Active milestone\n([\s\S]*?)(?=\n##|$)/);
  const milestone = milestonesMatch ? milestonesMatch[1].trim() : '(none)';

  return `# MPGA-Managed Project Context

This project uses MPGA for evidence-backed context engineering.
Do NOT edit this file manually — generated from MPGA/INDEX.md.
Run \`mpga sync && mpga export --antigravity\` to update.

## Before starting any task
1. Read MPGA/INDEX.md — this is the project's truth map
2. Find the relevant MPGA/scopes/*.md for the feature area
3. Check MPGA/board/BOARD.md for task state and assignments

## Evidence protocol
- Every claim about code behavior must cite an evidence link
- Format: [E] src/auth/jwt.ts:42-67 :: validateToken()
- If you cannot verify a claim, mark it: [Unknown] description
- After modifying code, check if evidence links need updating

## TDD protocol (mandatory)
1. Write failing test FIRST
2. Implement minimal code to pass
3. Refactor without changing behavior
4. Update MPGA scope docs with new evidence links

## Active milestone
${milestone}

## Verification commands
- \`npm test\` — run test suite
- \`npx mpga evidence verify\` — check evidence links
- \`npx mpga drift --quick\` — check for drift
- \`npx mpga board show\` — view task board

Generated: ${new Date().toISOString()}
`;
}

function generateAntigravityContextMd(indexContent: string, projectName: string): string {
  const milestonesMatch = indexContent.match(/## Active milestone\n([\s\S]*?)(?=\n##|$)/);
  const milestone = milestonesMatch ? milestonesMatch[1].trim() : '(none)';

  return `# MPGA Project Context

This project uses evidence-backed context engineering via MPGA.

## Agent instructions
Before executing any task:
1. Read MPGA/INDEX.md — this is the project's truth map
2. Read the relevant MPGA/scopes/*.md for the feature area
3. Check MPGA/board/BOARD.md for task state and assignments

## Evidence protocol
- Every claim about code behavior must cite an evidence link
- Format: [E] src/auth/jwt.ts:42-67 :: validateToken()
- If you cannot verify a claim, mark it: [Unknown] description
- After modifying code, check if evidence links need updating

## Active milestone
${milestone}

## Verification commands
- \`npm test\` — run test suite
- \`npx mpga evidence verify\` — check evidence links
- \`npx mpga drift --quick\` — check for drift
- \`npx mpga board show\` — view task board

Generated: ${new Date().toISOString()}
`;
}

function generateAntigravityEvidenceMd(): string {
  return `# MPGA Evidence Protocol

## Evidence link format
\`\`\`
[E] filepath:startLine-endLine :: symbolName()   # exact range + AST anchor (preferred)
[E] filepath :: symbolName                        # AST-only, resilient to refactors
[Unknown] description                             # explicitly unknown — never guess
[Stale:YYYY-MM-DD] filepath:range                # was valid, needs re-verification
\`\`\`

## Rules
- EVERY claim about how code works must cite an evidence link
- When you cannot find evidence, write [Unknown] — never invent a claim
- After changing code, check whether evidence links in the affected scope still resolve
- Run \`npx mpga evidence heal --auto\` to fix broken line ranges via AST

## Scope documents
Evidence links live in MPGA/scopes/*.md — read the relevant scope before touching code.
`;
}

function generateAntigravityTddMd(): string {
  return `# MPGA TDD Protocol

## Mandatory test-driven development cycle

### For every code change:
1. GREEN: Write a failing test that describes expected behavior
   - Cite relevant evidence from MPGA/scopes/ in test comments
   - Run test — it MUST fail
2. RED: Write minimal implementation to make the test pass
   - YAGNI — do not add anything the test doesn't require
   - Run test — it MUST pass
3. BLUE: Refactor without changing behavior
   - All tests must stay green after every refactoring step
   - Update evidence links in MPGA/scopes/ if code moved

### Rules
- NEVER write implementation code before a test exists
- NEVER add features not covered by tests
- ALWAYS update MPGA/board/ task cards with TDD stage progress
`;
}

function generateAntigravityGlobal(): string {
  return `# MPGA Global Methodology

When you detect an MPGA/ directory in any project:

## Always do
- Read MPGA/INDEX.md before starting any task
- Use evidence links to ground every claim about code behavior
- Mark unknowns explicitly — never guess or hallucinate
- Follow TDD: test first, implement second, refactor third
- Check the task board at MPGA/board/BOARD.md
- Update scope docs when you change code

## Evidence link format
[E] filepath:startLine-endLine :: symbolName()
[Unknown] description
[Stale:YYYY-MM-DD] filepath:range

## Never do
- Never paste entire directories into context — use tiered loading
- Never write implementation before tests
- Never claim code works without an evidence link
- Never ignore [Unknown] markers — they mean "we don't know yet"
`;
}

function generateAntigravityPlanWorkflow(): string {
  return `# MPGA Plan Workflow

## Trigger
Use this workflow when a milestone has been created and needs an implementation plan.

## Steps
1. Read MPGA/INDEX.md for project map and scope registry
2. Identify the milestone in MPGA/milestones/
3. Load relevant scope docs from MPGA/scopes/
4. Research: identify knowledge gaps ([Unknown] markers in scopes)
5. Break work into tasks (2-10 min each)
   - Each task MUST cite exact files to modify (with evidence links)
   - Each task MUST specify expected test file locations
   - Each task MUST have mechanically verifiable acceptance criteria
6. Save plan to MPGA/milestones/<id>/PLAN.md
7. Add tasks to board: \`npx mpga board add "<title>" --scope <name>\`
`;
}

function generateAntigravityDevelopWorkflow(): string {
  return `# MPGA Develop Workflow

## Trigger
Use this workflow when implementing a planned task from the MPGA board.

## Steps
1. Read the task card from MPGA/board/tasks/T*.md
2. Load the scopes listed in the task's \`scopes\` field
3. Write failing test (cite scope evidence in comments)
4. Implement minimal code to pass
5. Refactor for quality
6. Update evidence links in the relevant scope doc
7. Update the task card: set tdd_stage, add evidence_produced
8. Move task to next board column
9. Run: \`npx mpga drift --quick\`
10. Commit with conventional message
`;
}

function generateAntigravityReviewWorkflow(): string {
  return `# MPGA Review Workflow

## Trigger
Use this workflow when a task reaches the review column.

## Stage 1 — Spec compliance
- Does implementation match the plan in MPGA/milestones/<id>/PLAN.md?
- Are all evidence links in scope docs still valid? (\`npx mpga evidence verify\`)
- Were tests written BEFORE implementation? (check git log order)

## Stage 2 — Code quality
- Clean code principles (naming, single responsibility, DRY)
- Error handling for expected failure modes
- No security regressions
- Performance considerations

## Output
- PASS: move task to done, update board
- FAIL (critical): move task back to in-progress, note the blocker
- FAIL (warning): move to done with follow-up task created
`;
}

function seedAntigravityKnowledgeItems(projectRoot: string, scopesDir: string): void {
  const kiDir = path.join(projectRoot, '.antigravity', 'knowledge');
  fs.mkdirSync(kiDir, { recursive: true });

  const scopes = fs.readdirSync(scopesDir).filter(f => f.endsWith('.md'));
  for (const scopeFile of scopes) {
    const scopeName = scopeFile.replace('.md', '');
    const scopeContent = fs.readFileSync(path.join(scopesDir, scopeFile), 'utf-8');
    const evidenceLinks = (scopeContent.match(/\[E\] .+/g) ?? []).slice(0, 10);

    fs.writeFileSync(path.join(kiDir, `mpga-${scopeName}.md`), `# Knowledge: ${scopeName} module

Source: MPGA/scopes/${scopeName}.md
Auto-seeded by \`mpga export --antigravity --knowledge\`

## Key evidence
${evidenceLinks.map(l => `- ${l}`).join('\n') || '- (run `mpga sync` to populate)'}

## Full scope
Read MPGA/scopes/${scopeName}.md for the complete evidence-backed scope document.
`);
  }
}
