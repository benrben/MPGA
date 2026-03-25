import { describe, it, expect, vi } from 'vitest';
import { progressBar, RALLY_QUOTES, randomQuote, victory } from './logger.js';

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

describe('RALLY_QUOTES', () => {
  it('has at least 15 rally quotes', () => {
    expect(RALLY_QUOTES.length).toBeGreaterThanOrEqual(15);
  });

  it('every quote is a non-empty string', () => {
    for (const q of RALLY_QUOTES) {
      expect(typeof q).toBe('string');
      expect(q.length).toBeGreaterThan(0);
    }
  });
});

describe('randomQuote', () => {
  it('returns a string from RALLY_QUOTES', () => {
    const q = randomQuote();
    expect(RALLY_QUOTES).toContain(q);
  });
});

describe('victory', () => {
  it('prints the message and a rally quote to console', () => {
    const spy = vi.spyOn(console, 'log').mockImplementation(() => {});
    victory('We did it!');
    expect(spy).toHaveBeenCalled();
    const output = spy.mock.calls.map((c) => stripAnsi(String(c[0]))).join('\n');
    expect(output).toContain('We did it!');
    spy.mockRestore();
  });
});
