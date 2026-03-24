import { expect } from 'vitest';

expect.extend({
  toEndWith(received: string, expected: string) {
    const pass = typeof received === 'string' && received.endsWith(expected);
    return {
      pass,
      message: () =>
        pass
          ? `expected "${received}" not to end with "${expected}"`
          : `expected "${received}" to end with "${expected}"`,
    };
  },
});

// Augment vitest types
declare module 'vitest' {
  // eslint-disable-next-line @typescript-eslint/no-empty-interface
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface Assertion<T = any> {
    toEndWith(expected: string): void;
  }
  // eslint-disable-next-line @typescript-eslint/no-empty-interface
  interface AsymmetricMatchersContaining {
    toEndWith(expected: string): unknown;
  }
}
