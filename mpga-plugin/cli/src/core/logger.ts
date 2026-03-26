import chalk from 'chalk';
import { spawn } from 'child_process';
import { existsSync } from 'fs';
import { createHash } from 'crypto';
import { join } from 'path';
import { homedir } from 'os';

// ── Brand colors ──────────────────────────────────────────────
const BRAND = {
  red: chalk.hex('#CC0000'),
  redBg: chalk.bgHex('#CC0000').white.bold,
  white: chalk.white.bold,
  gear: chalk.hex('#8899AA'),
  dim: chalk.dim,
  accent: chalk.hex('#FF4444'),
};

// ── ASCII cap banner (matches MPGA.png logo) ─────────────────
const r = BRAND.red;
const rb = BRAND.redBg;
const g = BRAND.gear;
const d = BRAND.dim;
const CAP_BANNER = [
  '',
  r('                  ▄▄███████████▄▄'),
  r('              ▄███') + rb('               ') + r('███▄'),
  r('           ▄██') + rb('  MAKE  PROJECT     ') + r('██▄'),
  r('          ██') + rb('    GREAT  AGAIN        ') + r('██'),
  r('         ██') + rb('       M P G A            ') + r('██'),
  r('        ██') + rb('                            ') + r('██'),
  r('  ▄▄▄▄▄███▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄███'),
  r('  ████████████████████████████████████████'),
  d('   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░') + g('   ⚙'),
  d('                                        ') + g('  </>'),
  '',
].join('\n');

const CAP_MINI = `${BRAND.red('🧢')} ${BRAND.accent('MPGA')} ${chalk.dim('— Make Project Great Again')}`;

/** Width of the mini banner divider line. */
const MINI_BANNER_WIDTH = 42;
/** Width of the key-value label column for aligned output. */
const KV_LABEL_WIDTH = 18;
/** Default width of the progress bar in characters. */
const DEFAULT_PROGRESS_BAR_WIDTH = 20;
/** Width of section divider lines. */
const DIVIDER_WIDTH = 40;

export const VERSION = '1.0.0';

export function banner(): void {
  console.log(CAP_BANNER);
}

export function miniBanner(): void {
  console.log('');
  console.log(CAP_MINI);
  console.log(chalk.dim('─'.repeat(MINI_BANNER_WIDTH)));
}

export const log = {
  info: (msg: string) => console.log(chalk.blue('ℹ') + ' ' + msg),
  success: (msg: string) => console.log(chalk.green('✓') + ' ' + msg),
  warn: (msg: string) => console.log(chalk.yellow('⚠') + ' ' + msg),
  error: (msg: string) => console.error(chalk.red('✗') + ' ' + msg),
  dim: (msg: string) => console.log(chalk.dim(msg)),
  bold: (msg: string) => console.log(chalk.bold(msg)),
  brand: (msg: string) => console.log(BRAND.accent(msg)),
  header: (msg: string) => {
    console.log('');
    console.log(BRAND.accent('■ ') + chalk.bold(msg));
    console.log(chalk.dim('  ' + '─'.repeat(msg.length + 2)));
  },
  section: (msg: string) => {
    console.log('');
    console.log(chalk.bold.white(msg));
  },
  kv: (key: string, value: string, indent = 2) => {
    const pad = ' '.repeat(indent);
    console.log(`${pad}${chalk.dim(key.padEnd(KV_LABEL_WIDTH))} ${value}`);
  },
  table: (rows: string[][]) => {
    const widths = rows[0].map((_, i) => Math.max(...rows.map((r) => (r[i] ?? '').length)));
    for (const row of rows) {
      console.log('  ' + row.map((cell, i) => cell.padEnd(widths[i])).join('  '));
    }
  },
  divider: () => console.log(chalk.dim('  ' + '─'.repeat(DIVIDER_WIDTH))),
  blank: () => console.log(''),
};

// ── Rally quotes — rotating Trump-style quips ───────────────
export const RALLY_QUOTES = [
  "Many people are saying this is the best sync they've ever seen.",
  "The fake tech press won't cover how clean this codebase is.",
  'I have the best dependency graphs. Everyone agrees.',
  "We're WINNING so much you're going to get TIRED of winning!",
  'Nobody builds plugins better than me, believe me.',
  'Big strong senior engineers, tears in their eyes — "Sir, the tests pass."',
  'This is, I believe, the greatest developer tool of all time.',
  'Evidence over claims, folks. Evidence. Over. Claims.',
  "We don't do fake documentation. We do EVIDENCE.",
  'Crooked Gemini just makes stuff up. We VERIFY.',
  "Our codebase is looking FANTASTIC. The best it's ever looked.",
  'Uncle Bob himself would be proud. TREMENDOUS code.',
  "We're going to make this project GREATER THAN EVER BEFORE.",
  "Some people say our tests are the best tests. I don't say it — they say it.",
  "That's a BEAUTIFUL directory structure. Elegant. The best word.",
  'Less than four sprints ago this CI was a DISASTER. Now look at it.',
  'We will SHIP faster, write CLEANER code, and SLASH the tech debt.',
  'We have mandatory post-edit hooks. Mandatory. Every. Single. Time.',
  'The engineers — they love it. They come up to me and say, "Sir, the hooks actually work."',
  'Tomorrow we begin a brand-new day of evidence-based documentation.',
];

export function randomQuote(): string {
  return RALLY_QUOTES[Math.floor(Math.random() * RALLY_QUOTES.length)];
}

export function victory(msg: string): void {
  console.log('');
  console.log(chalk.green('🎤 ') + chalk.bold.green(msg));
  const quote = randomQuote();
  console.log(chalk.dim('  ' + quote));
  // Fire-and-forget: play cached rally quote in Trump's voice
  try {
    const cacheDir = join(homedir(), '.mpga', 'spoke-cache');
    const hash = createHash('md5').update(quote).digest('hex');
    const wavPath = join(cacheDir, `${hash}.wav`);
    if (existsSync(wavPath)) {
      spawn('afplay', [wavPath], { detached: true, stdio: 'ignore' }).unref();
    }
  } catch {
    /* silent — spoke is optional */
  }
}

export function progressBar(
  value: number,
  total: number,
  width = DEFAULT_PROGRESS_BAR_WIDTH,
): string {
  const pct = total === 0 ? 0 : value / total;
  const filled = Math.round(pct * width);
  const bar = chalk.green('█'.repeat(filled)) + chalk.dim('░'.repeat(width - filled));
  return `${bar} ${Math.round(pct * 100)}%`;
}

export function gradeColor(grade: string): string {
  switch (grade) {
    case 'A':
      return chalk.green.bold(grade);
    case 'B':
      return chalk.blue.bold(grade);
    case 'C':
      return chalk.yellow.bold(grade);
    default:
      return chalk.red.bold(grade);
  }
}

export function statusBadge(ok: boolean, label: string): string {
  return ok ? chalk.green('✓') + ' ' + label : chalk.red('✗') + ' ' + label;
}
