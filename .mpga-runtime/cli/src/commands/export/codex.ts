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

// ─── Codex / Gemini CLI export ───────────────────────────────────────────────

export function exportCodex(
  projectRoot: string,
  mpgaDir: string,
  indexContent: string,
  projectName: string,
  pluginRoot: string | null,
  isGlobal: boolean,
): void {
  if (isGlobal) {
    const codexGlobalDir = path.join(process.env.HOME ?? '~', '.codex');
    const cliCommand = pluginRoot ? globalVendoredCliCommand(codexGlobalDir) : 'npx mpga';
    copyVendoredRuntime(codexGlobalDir, pluginRoot);
    fs.mkdirSync(codexGlobalDir, { recursive: true });
    fs.writeFileSync(path.join(codexGlobalDir, 'AGENTS.md'), generateCodexGlobalAgentsMd(cliCommand));
    log.success('Generated ~/.codex/AGENTS.md');
    const globalSkillsDir = path.join(codexGlobalDir, 'skills');
    copySkillsTo(globalSkillsDir, pluginRoot, 'codex', cliCommand);
    log.success(`Generated ~/.codex/skills/ (${SKILL_NAMES.length} skills)`);
    const globalAgentsDir = path.join(codexGlobalDir, 'agents');
    fs.mkdirSync(globalAgentsDir, { recursive: true });
    for (const agent of AGENTS) {
      fs.writeFileSync(
        path.join(globalAgentsDir, `${agent.name}.toml`),
        generateCodexAgentToml(agent, pluginRoot, cliCommand),
      );
    }
    log.success(`Generated ~/.codex/agents/ (${AGENTS.length} TOML agents)`);
  } else {
    const cliCommand = pluginRoot ? projectVendoredCliCommand() : 'npx mpga';
    copyVendoredRuntime(projectRoot, pluginRoot);
    // Root AGENTS.md
    fs.writeFileSync(
      path.join(projectRoot, 'AGENTS.md'),
      generateAgentsMd(indexContent, projectName, cliCommand),
    );
    // MPGA layer nav guide
    fs.writeFileSync(path.join(mpgaDir, 'AGENTS.md'), generateMpgaLayerAgentsMd());
    // Subdirectory AGENTS.md files for detected scopes
    const scopesDir = path.join(mpgaDir, 'scopes');
    if (fs.existsSync(scopesDir)) generateSubdirAgentsMd(projectRoot, scopesDir);
    log.success('Generated AGENTS.md (root + MPGA/ + scope subdirs)');
    // Skills
    const codexSkillsDir = path.join(projectRoot, '.codex', 'skills');
    copySkillsTo(codexSkillsDir, pluginRoot, 'codex', cliCommand);
    log.success(`.codex/skills/ (${SKILL_NAMES.length} skills)`);
    // TOML agents
    const codexAgentsDir = path.join(projectRoot, '.codex', 'agents');
    fs.mkdirSync(codexAgentsDir, { recursive: true });
    for (const agent of AGENTS) {
      fs.writeFileSync(
        path.join(codexAgentsDir, `${agent.name}.toml`),
        generateCodexAgentToml(agent, pluginRoot, cliCommand),
      );
    }
    log.success(`.codex/agents/ (${AGENTS.length} TOML agents)`);
  }
}

// ─── Codex generators ────────────────────────────────────────────────────────

/** Generate Codex-format TOML agent (.codex/agents/mpga-<slug>.toml) */
function generateCodexAgentToml(
  agent: AgentMeta,
  pluginRoot: string | null,
  cliCommand: string,
): string {
  const instructions = readAgentInstructions(pluginRoot, agent.slug, cliCommand)
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

function generateAgentsMd(indexContent: string, _projectName: string, cliCommand: string): string {
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

## Parallel execution protocol
- One writer per scope at a time
- Read-only helpers like scouts and auditors may run in parallel
- Break plans into independent scope lanes when possible

## Task board
Current tasks tracked in MPGA/board/BOARD.md
Task cards in MPGA/board/tasks/T*.md

## Verification commands
- Run tests: npm test
- Check evidence: ${cliCommand} evidence verify
- Check drift: ${cliCommand} drift --quick
- Board status: ${cliCommand} board show

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
  const scopes = fs.readdirSync(scopesDir).filter((f) => f.endsWith('.md'));
  for (const scopeFile of scopes) {
    const scopeName = scopeFile.replace('.md', '');
    const scopeContent = fs.readFileSync(path.join(scopesDir, scopeFile), 'utf-8');
    const evidenceLinks = (scopeContent.match(/\[E\] .+/g) ?? []).slice(0, 5);
    const evidenceSection =
      evidenceLinks.length > 0
        ? evidenceLinks.map((l) => `- ${l}`).join('\n')
        : '- (run `mpga sync` to populate evidence links)';

    const srcDir = path.join(projectRoot, 'src', scopeName);
    if (!fs.existsSync(srcDir)) continue;

    fs.writeFileSync(
      path.join(srcDir, 'AGENTS.md'),
      `# ${scopeName} Module — MPGA Scope

For detailed evidence-backed documentation of this module,
read: MPGA/scopes/${scopeName}.md

## Key evidence
${evidenceSection}

## Dependencies
See MPGA/scopes/${scopeName}.md for full dependency graph.
`,
    );
  }
}

function generateCodexGlobalAgentsMd(cliCommand: string): string {
  return `# MPGA Methodology (Global)

When working in ANY project that contains an MPGA/ directory:

## Core principles
- Evidence over claims: every code assertion must cite [E] file:line
- Unknown is honest: mark gaps as [Unknown], never guess
- TDD is mandatory: test → implement → refactor → update evidence
- Tiered reading: INDEX.md first, scope docs second, deep docs only if needed
- Parallelize reads, not writes: one writer per scope

## Workflow
1. Read MPGA/INDEX.md for project map
2. Check MPGA/board/BOARD.md for current tasks
3. Load relevant MPGA/scopes/*.md before touching code
4. After changes: update evidence links in scope docs
5. Run \`${cliCommand} drift --quick\` to verify nothing broke

## Evidence link format
[E] filepath:startLine-endLine :: symbolName()
[E] filepath :: symbolName (AST-only, resilient)
[Unknown] description (explicitly unknown)
[Stale:YYYY-MM-DD] filepath:range (was valid, needs verification)
`;
}
