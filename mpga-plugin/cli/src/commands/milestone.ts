import fs from 'fs';
import path from 'path';
import { Command } from 'commander';
import { log } from '../core/logger.js';
import { findProjectRoot } from '../core/config.js';
import { loadBoard, saveBoard, recalcStats } from '../board/board.js';
import { renderBoardMd } from '../board/board-md.js';

interface MilestoneInfo {
  id: string;
  name: string;
  dirPath: string;
  status: 'active' | 'complete' | 'planned';
  created: string;
}

function getMilestonesDir(projectRoot: string): string {
  return path.join(projectRoot, 'MPGA', 'milestones');
}

function listMilestones(milestonesDir: string): MilestoneInfo[] {
  if (!fs.existsSync(milestonesDir)) return [];
  return fs.readdirSync(milestonesDir)
    .filter(d => {
      const full = path.join(milestonesDir, d);
      return fs.statSync(full).isDirectory() && d.match(/^M\d+/);
    })
    .map(d => {
      const dirPath = path.join(milestonesDir, d);
      const m = d.match(/^(M\d+)-(.+)/);
      const summaryPath = path.join(dirPath, 'SUMMARY.md');
      return {
        id: m?.[1] ?? d,
        name: m?.[2]?.replace(/-/g, ' ') ?? d,
        dirPath,
        status: fs.existsSync(summaryPath) ? 'complete' : 'active',
        created: fs.statSync(dirPath).birthtime.toISOString().split('T')[0],
      } as MilestoneInfo;
    });
}

function nextMilestoneId(milestonesDir: string): string {
  const existing = listMilestones(milestonesDir);
  const nums = existing.map(m => parseInt(m.id.replace('M', ''))).filter(n => !isNaN(n));
  const max = nums.length > 0 ? Math.max(...nums) : 0;
  return `M${String(max + 1).padStart(3, '0')}`;
}

export function registerMilestone(program: Command): void {
  const cmd = program
    .command('milestone')
    .description('Milestone workflow management');

  // milestone new
  cmd
    .command('new <name>')
    .description('Create a new milestone')
    .action((name: string) => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const milestonesDir = getMilestonesDir(projectRoot);
      fs.mkdirSync(milestonesDir, { recursive: true });

      const id = nextMilestoneId(milestonesDir);
      const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
      const dirName = `${id}-${slug}`;
      const dirPath = path.join(milestonesDir, dirName);

      fs.mkdirSync(dirPath);

      const now = new Date().toISOString();
      const today = now.split('T')[0];

      // PLAN.md
      fs.writeFileSync(path.join(dirPath, 'PLAN.md'), `# ${id}: ${name} — Plan

## Objective
(describe what this milestone achieves)

## Tasks
(run \`/mpga:plan\` to generate evidence-based tasks)

## Acceptance criteria
- [ ] (define criteria)

## Created
${today}
`);

      // CONTEXT.md
      fs.writeFileSync(path.join(dirPath, 'CONTEXT.md'), `# ${id}: ${name} — Context

## Background
(why this milestone, what problem it solves)

## Constraints
- (list constraints)

## Dependencies
- (list external dependencies)

## Decisions
| Decision | Rationale | Date |
|----------|-----------|------|
| | | |
`);

      // Link milestone to board
      const boardDir = path.join(projectRoot, 'MPGA', 'board');
      const tasksDir = path.join(boardDir, 'tasks');
      if (fs.existsSync(path.join(boardDir, 'board.json'))) {
        const board = loadBoard(boardDir);
        board.milestone = dirName;
        recalcStats(board, tasksDir);
        saveBoard(boardDir, board);
        fs.writeFileSync(path.join(boardDir, 'BOARD.md'), renderBoardMd(board, tasksDir));
      }

      log.success(`Created milestone ${id}: ${name}`);
      log.dim(`  Directory: MPGA/milestones/${dirName}/`);
      log.dim('');
      log.dim('Next steps:');
      log.dim('  Edit MPGA/milestones/' + dirName + '/PLAN.md');
      log.dim('  Run /mpga:plan to generate tasks');
    });

  // milestone list
  cmd
    .command('list')
    .description('List all milestones')
    .action(() => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const milestonesDir = getMilestonesDir(projectRoot);
      const milestones = listMilestones(milestonesDir);

      if (milestones.length === 0) {
        log.info('No milestones yet. Run `mpga milestone new "<name>"` to create one.');
        return;
      }

      log.header('Milestones');
      const rows = [['ID', 'Name', 'Status', 'Created']];
      for (const m of milestones) {
        rows.push([m.id, m.name, m.status === 'complete' ? '✅ complete' : '🔄 active', m.created]);
      }
      log.table(rows);
    });

  // milestone status
  cmd
    .command('status')
    .description('Show current milestone progress')
    .action(() => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const boardDir = path.join(projectRoot, 'MPGA', 'board');
      const tasksDir = path.join(boardDir, 'tasks');

      if (!fs.existsSync(path.join(boardDir, 'board.json'))) {
        log.error('No board found. Run `mpga init` first.');
        process.exit(1);
      }

      const board = loadBoard(boardDir);
      recalcStats(board, tasksDir);

      if (!board.milestone) {
        log.info('No active milestone. Run `mpga milestone new "<name>"` to create one.');
        return;
      }

      log.header(`Milestone: ${board.milestone}`);
      const { stats } = board;
      console.log(`  Progress:    ${stats.done}/${stats.total} tasks (${stats.progress_pct}%)`);
      console.log(`  In flight:   ${stats.in_flight}`);
      console.log(`  Blocked:     ${stats.blocked}`);
      console.log(`  Evidence:    ${stats.evidence_produced}/${stats.evidence_expected} links`);
    });

  // milestone complete
  cmd
    .command('complete')
    .description('Archive milestone and mark as complete')
    .action(() => {
      const projectRoot = findProjectRoot() ?? process.cwd();
      const boardDir = path.join(projectRoot, 'MPGA', 'board');
      const tasksDir = path.join(boardDir, 'tasks');
      const board = loadBoard(boardDir);

      if (!board.milestone) {
        log.error('No active milestone to complete.');
        process.exit(1);
      }

      const milestoneDir = path.join(projectRoot, 'MPGA', 'milestones', board.milestone);
      const today = new Date().toISOString().split('T')[0];

      // Write SUMMARY.md
      recalcStats(board, tasksDir);
      fs.writeFileSync(path.join(milestoneDir, 'SUMMARY.md'), `# ${board.milestone} — Summary

## Completed: ${today}

## Stats
- Tasks completed: ${board.stats.done}
- Evidence links produced: ${board.stats.evidence_produced}

## Outcome
(describe what was delivered)
`);

      log.success(`Milestone '${board.milestone}' marked complete.`);
      log.dim(`  Summary saved to MPGA/milestones/${board.milestone}/SUMMARY.md`);
      log.dim('  Run `mpga board archive` to archive done tasks.');
    });
}
