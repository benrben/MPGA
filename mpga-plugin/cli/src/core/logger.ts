import chalk from 'chalk';

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

export const VERSION = '1.0.0';

export function banner(): void {
  console.log(CAP_BANNER);
}

export function miniBanner(): void {
  console.log('');
  console.log(CAP_MINI);
  console.log(chalk.dim('─'.repeat(42)));
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
    console.log(`${pad}${chalk.dim(key.padEnd(18))} ${value}`);
  },
  table: (rows: string[][]) => {
    const widths = rows[0].map((_, i) => Math.max(...rows.map(r => (r[i] ?? '').length)));
    for (const row of rows) {
      console.log('  ' + row.map((cell, i) => cell.padEnd(widths[i])).join('  '));
    }
  },
  divider: () => console.log(chalk.dim('  ' + '─'.repeat(40))),
  blank: () => console.log(''),
};

export function progressBar(value: number, total: number, width = 20): string {
  const pct = total === 0 ? 0 : value / total;
  const filled = Math.round(pct * width);
  const bar = chalk.green('█'.repeat(filled)) + chalk.dim('░'.repeat(width - filled));
  return `${bar} ${Math.round(pct * 100)}%`;
}

export function gradeColor(grade: string): string {
  switch (grade) {
    case 'A': return chalk.green.bold(grade);
    case 'B': return chalk.blue.bold(grade);
    case 'C': return chalk.yellow.bold(grade);
    default: return chalk.red.bold(grade);
  }
}

export function statusBadge(ok: boolean, label: string): string {
  return ok
    ? chalk.green('✓') + ' ' + label
    : chalk.red('✗') + ' ' + label;
}
