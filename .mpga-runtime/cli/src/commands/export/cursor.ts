import fs from 'fs';
import path from 'path';
import { log } from '../../core/logger.js';
import { AGENTS, SKILL_NAMES, copySkillsTo, readAgentInstructions } from './agents.js';
import type { AgentMeta } from './agents.js';
import {
  copyVendoredRuntime,
  globalVendoredCliCommand,
  projectVendoredCliCommand,
} from './runtime.js';

// ─── Cursor export ───────────────────────────────────────────────────────────

export function exportCursor(
  projectRoot: string,
  mpgaDir: string,
  indexContent: string,
  projectName: string,
  pluginRoot: string | null,
  isGlobal: boolean,
): void {
  if (isGlobal) {
    const cursorRoot = path.join(process.env.HOME ?? '~', '.cursor');
    const cliCommand = pluginRoot ? globalVendoredCliCommand(cursorRoot) : 'npx mpga';
    copyVendoredRuntime(cursorRoot, pluginRoot);
    log.info('Add the following to Cursor Settings > General > Rules for AI:');
    log.info('\n' + generateCursorGlobal(cliCommand));
    const globalSkillsDir = path.join(process.env.HOME ?? '~', '.cursor', 'skills');
    copySkillsTo(globalSkillsDir, pluginRoot, 'cursor', cliCommand);
    log.success(`Generated ~/.cursor/skills/ (${SKILL_NAMES.length} skills)`);
    // Global agents
    const globalAgentsDir = path.join(process.env.HOME ?? '~', '.cursor', 'agents');
    fs.mkdirSync(globalAgentsDir, { recursive: true });
    for (const agent of AGENTS) {
      fs.writeFileSync(
        path.join(globalAgentsDir, `${agent.name}.md`),
        generateCursorAgentMd(agent, pluginRoot, cliCommand),
      );
    }
    log.success(`Generated ~/.cursor/agents/ (${AGENTS.length} agents)`);
  } else {
    const cliCommand = pluginRoot ? projectVendoredCliCommand() : 'npx mpga';
    copyVendoredRuntime(projectRoot, pluginRoot);
    // Rules
    const rulesDir = path.join(projectRoot, '.cursor', 'rules');
    fs.mkdirSync(rulesDir, { recursive: true });
    fs.writeFileSync(
      path.join(rulesDir, 'mpga-project.mdc'),
      generateCursorProjectMdc(indexContent, projectName, cliCommand),
    );
    fs.writeFileSync(
      path.join(rulesDir, 'mpga-evidence.mdc'),
      generateCursorEvidenceMdc(cliCommand),
    );
    fs.writeFileSync(path.join(rulesDir, 'mpga-tdd.mdc'), generateCursorTddMdc());
    fs.writeFileSync(path.join(rulesDir, 'mpga-scopes.mdc'), generateCursorScopesMdc(mpgaDir));
    log.success('Generated .cursor/rules/ (4 MDC files)');
    // Skills
    const cursorSkillsDir = path.join(projectRoot, '.cursor', 'skills');
    copySkillsTo(cursorSkillsDir, pluginRoot, 'cursor', cliCommand);
    log.success(`.cursor/skills/ (${SKILL_NAMES.length} skills)`);
    // Agents
    const cursorAgentsDir = path.join(projectRoot, '.cursor', 'agents');
    fs.mkdirSync(cursorAgentsDir, { recursive: true });
    for (const agent of AGENTS) {
      fs.writeFileSync(
        path.join(cursorAgentsDir, `${agent.name}.md`),
        generateCursorAgentMd(agent, pluginRoot, cliCommand),
      );
    }
    log.success(`.cursor/agents/ (${AGENTS.length} agents)`);
  }
}

// ─── Cursor generators ────────────────────────────────────────────────────────

/** Generate Cursor-format agent markdown (.cursor/agents/mpga-<slug>.md) */
function generateCursorAgentMd(
  agent: AgentMeta,
  pluginRoot: string | null,
  cliCommand: string,
): string {
  const instructions = readAgentInstructions(pluginRoot, agent.slug, cliCommand);

  return `---
name: ${agent.name}
description: ${agent.description}
model: ${agent.model}
readonly: ${agent.readonly}
is_background: ${agent.isBackground}
---

${instructions}`;
}

function generateCursorProjectMdc(
  indexContent: string,
  _projectName: string,
  cliCommand: string,
): string {
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

function generateCursorEvidenceMdc(cliCommand: string): string {
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
${cliCommand} evidence verify       # check all links
${cliCommand} drift --quick         # fast staleness check
${cliCommand} evidence heal --auto  # auto-fix broken links via AST
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
6. Keep one writer per scope; parallelize read-only scouts and auditors instead

If you find yourself writing implementation code without a test:
STOP. Delete it. Write the test first.
`;
}

function generateCursorScopesMdc(mpgaDir: string): string {
  const scopesDir = path.join(mpgaDir, 'scopes');
  let scopeLines = '- (no scopes yet — run `mpga sync` to generate)';

  if (fs.existsSync(scopesDir)) {
    const scopes = fs
      .readdirSync(scopesDir)
      .filter((f) => f.endsWith('.md'))
      .map((f) => f.replace('.md', ''));
    if (scopes.length > 0) {
      scopeLines = scopes.map((s) => `- ${s} → @MPGA/scopes/${s}.md`).join('\n');
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

function generateCursorGlobal(cliCommand: string): string {
  return `When you see an MPGA/ directory in any project:
- Read MPGA/INDEX.md before starting any task
- Use evidence links [E] format: [E] file:line :: symbol()
- Mark unknowns as [Unknown] — never guess
- Follow TDD: test first, implement second, refactor third
- Check MPGA/board/BOARD.md for task assignments
- After modifying code, consider if evidence links need updating
- Prefer reading scope docs over scanning entire directories`;
}
