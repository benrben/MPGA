import { describe, it, expect } from 'vitest';
import { progressBar } from './logger.js';

// Strip ANSI color codes for testing
function stripAnsi(s: string): string {
  // eslint-disable-next-line no-control-regex
  return s.replace(/\x1B\[[0-9;]*m/g, '');
}

describe('progressBar', () => {
  it('shows 0% for empty', () => {
    const bar = stripAnsi(progressBar(0, 10));
    expect(bar).toContain('0%');
    expect(bar).toContain('░');
  });

  it('shows 100% for full', () => {
    const bar = stripAnsi(progressBar(10, 10));
    expect(bar).toContain('100%');
    expect(bar).toContain('█');
  });

  it('shows 50% for half', () => {
    const bar = stripAnsi(progressBar(5, 10));
    expect(bar).toContain('50%');
  });

  it('handles zero total', () => {
    const bar = stripAnsi(progressBar(0, 0));
    expect(bar).toContain('0%');
  });

  it('respects custom width', () => {
    const bar = stripAnsi(progressBar(5, 10, 10));
    // 5 filled + 5 empty = 10 bar chars
    const barChars = bar.replace(/\s*\d+%/, '');
    expect(barChars.length).toBe(10);
  });
});
