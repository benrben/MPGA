import fs from 'fs';
import path from 'path';

// ─── Agent metadata ───────────────────────────────────────────────────────────
// Canonical list of MPGA agents with their per-tool attributes.
// The markdown instructions live in mpga-plugin/agents/<slug>.md.

export interface AgentMeta {
  slug: string; // filename slug (e.g. "red-dev")
  name: string; // display name
  description: string; // one-line description for agent routing
  model: string; // preferred model
  readonly: boolean; // Cursor: cannot write files
  isBackground: boolean; // Cursor: can run in parallel
  sandboxMode: string; // Codex: workspace | none
}

export const AGENTS: AgentMeta[] = [
  {
    slug: 'red-dev',
    name: 'mpga-red-dev',
    description:
      'Write failing tests FIRST for a task. Use at the start of every TDD cycle (RED = failing test bar). Never writes implementation code.',
    model: 'claude-sonnet-4-6',
    readonly: false,
    isBackground: false,
    sandboxMode: 'workspace',
  },
  {
    slug: 'green-dev',
    name: 'mpga-green-dev',
    description:
      'Write minimal implementation to make a failing test pass (GREEN = passing test bar). Use after red-dev has written tests. Never modifies tests.',
    model: 'claude-sonnet-4-6',
    readonly: false,
    isBackground: false,
    sandboxMode: 'workspace',
  },
  {
    slug: 'blue-dev',
    name: 'mpga-blue-dev',
    description:
      'Refactor passing code and tests for quality without changing behavior. Use after green-dev. Updates evidence links in scope docs.',
    model: 'claude-sonnet-4-6',
    readonly: false,
    isBackground: false,
    sandboxMode: 'workspace',
  },
  {
    slug: 'scout',
    name: 'mpga-scout',
    description:
      'Read-only codebase explorer. Traces execution paths, maps dependencies, and builds evidence links. Never modifies files.',
    model: 'claude-sonnet-4-6',
    readonly: true,
    isBackground: true,
    sandboxMode: 'none',
  },
  {
    slug: 'architect',
    name: 'mpga-architect',
    description:
      'Structural analysis agent. Generates and updates GRAPH.md and scope docs from scout findings. Every claim must cite evidence.',
    model: 'claude-opus-4-6',
    readonly: false,
    isBackground: false,
    sandboxMode: 'workspace',
  },
  {
    slug: 'auditor',
    name: 'mpga-auditor',
    description:
      'Evidence integrity checker. Verifies evidence links resolve, flags stale links, calculates scope health. Read-only — only flags, never auto-fixes.',
    model: 'claude-sonnet-4-6',
    readonly: true,
    isBackground: true,
    sandboxMode: 'none',
  },
  {
    slug: 'researcher',
    name: 'mpga-researcher',
    description:
      'Domain research before planning. Reads scope docs, identifies knowledge gaps, investigates library options and pitfalls.',
    model: 'claude-opus-4-6',
    readonly: true,
    isBackground: false,
    sandboxMode: 'none',
  },
  {
    slug: 'reviewer',
    name: 'mpga-reviewer',
    description:
      'Two-stage code reviewer. Stage 1: spec compliance + evidence validity. Stage 2: code quality + security. Critical issues block progress.',
    model: 'claude-opus-4-6',
    readonly: true,
    isBackground: false,
    sandboxMode: 'none',
  },
  {
    slug: 'verifier',
    name: 'mpga-verifier',
    description:
      'Post-execution verification. Runs test suite, checks for stubs, verifies evidence links updated, confirms milestone progress.',
    model: 'claude-sonnet-4-6',
    readonly: true,
    isBackground: false,
    sandboxMode: 'workspace',
  },
];

export const SKILL_NAMES = [
  'sync-project',
  'brainstorm',
  'plan',
  'develop',
  'drift-check',
  'ask',
  'onboard',
  'ship',
  'handoff',
  'map-codebase',
];

// ─── Plugin root finder ───────────────────────────────────────────────────────

export function findPluginRoot(): string | null {
  // When running from compiled CLI at mpga-plugin/cli/dist/commands/export.js,
  // __dirname is dist/commands/ — plugin root is three levels up: ../../..
  const candidate = path.resolve(__dirname, '../../../..');
  if (
    fs.existsSync(path.join(candidate, 'skills')) &&
    fs.existsSync(path.join(candidate, 'agents'))
  ) {
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
export function copySkillsTo(
  targetSkillsDir: string,
  pluginRoot: string | null,
  toolName: string,
  cliPath?: string,
): void {
  fs.mkdirSync(targetSkillsDir, { recursive: true });

  for (const skillName of SKILL_NAMES) {
    const destDir = path.join(targetSkillsDir, `mpga-${skillName}`);
    fs.mkdirSync(destDir, { recursive: true });

    if (pluginRoot) {
      const srcDir = path.join(pluginRoot, 'skills', skillName);
      if (fs.existsSync(srcDir)) {
        copyDir(srcDir, destDir, toolName, cliPath);
        continue;
      }
    }

    // Fallback: write a minimal SKILL.md if plugin root not available
    if (!fs.existsSync(path.join(destDir, 'SKILL.md'))) {
      fs.writeFileSync(path.join(destDir, 'SKILL.md'), generateFallbackSkillMd(skillName));
    }
  }
}

function copyDir(src: string, dest: string, toolName: string, cliPath?: string): void {
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      fs.mkdirSync(destPath, { recursive: true });
      copyDir(srcPath, destPath, toolName, cliPath);
    } else {
      let content = fs.readFileSync(srcPath, 'utf-8');
      if (toolName === 'claude' && cliPath) {
        // Resolve to portable relative path from project root
        content = content.replace(/\$\{CLAUDE_PLUGIN_ROOT\}\/bin\/mpga\.sh/g, cliPath);
      } else if (toolName !== 'claude') {
        // Rewrite CLAUDE_PLUGIN_ROOT references to use npx mpga for non-Claude tools
        content = content.replace(/\$\{CLAUDE_PLUGIN_ROOT\}\/bin\/mpga\.sh/g, 'npx mpga');
      }
      fs.writeFileSync(destPath, content);
    }
  }
}

function generateFallbackSkillMd(skillName: string): string {
  const descriptions: Record<string, string> = {
    'sync-project': 'Rebuild the MPGA knowledge layer from the current codebase state',
    brainstorm: 'Socratic design refinement before writing any code',
    plan: 'Generate an evidence-based task breakdown for a milestone',
    develop: 'Orchestrate the TDD cycle for a task (red → green → blue → review)',
    'drift-check': 'Validate evidence links and detect stale scope docs',
    ask: 'Answer questions about the codebase using MPGA scope docs as citations',
    onboard: 'Guided tour of the codebase using the MPGA knowledge layer',
    ship: 'Verify, commit, update evidence, and advance milestone',
    handoff: 'Export session state for cross-context continuity',
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

export function readAgentInstructions(pluginRoot: string | null, slug: string): string {
  if (pluginRoot) {
    const agentPath = path.join(pluginRoot, 'agents', `${slug}.md`);
    if (fs.existsSync(agentPath)) {
      // Strip the H1 title line — it becomes redundant with the YAML frontmatter
      return fs
        .readFileSync(agentPath, 'utf-8')
        .replace(/^# Agent:.*\n/, '')
        .trimStart();
    }
  }
  return `See MPGA documentation for full ${slug} agent protocol.`;
}
