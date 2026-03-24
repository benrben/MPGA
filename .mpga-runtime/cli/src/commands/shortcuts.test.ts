import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Command } from 'commander';
import { registerShortcuts } from './shortcuts.js';

describe('shortcut commands', () => {
  let logSpy: ReturnType<typeof vi.spyOn>;

  function captured(): string {
    return logSpy.mock.calls.map((c) => c.join(' ')).join('\n');
  }

  function makeProgram(): Command {
    const program = new Command();
    program.exitOverride();
    program.configureOutput({ writeOut: () => {}, writeErr: () => {} });
    return program;
  }

  beforeEach(() => {
    logSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    logSpy.mockRestore();
  });

  describe('diagnose', () => {
    it('prints instruction to use /mpga:diagnose skill', async () => {
      const program = makeProgram();
      registerShortcuts(program);

      await program.parseAsync(['node', 'mpga', 'diagnose']);

      const output = captured();
      expect(output).toContain('/mpga:diagnose');
      expect(output).toContain('bug-hunter');
    });

    it('accepts optional file arguments', async () => {
      const program = makeProgram();
      registerShortcuts(program);

      await program.parseAsync(['node', 'mpga', 'diagnose', 'src/foo.ts', 'src/bar.ts']);

      const output = captured();
      expect(output).toContain('/mpga:diagnose');
      expect(output).toContain('src/foo.ts');
      expect(output).toContain('src/bar.ts');
    });
  });

  describe('secure', () => {
    it('prints instruction to use /mpga:secure skill', async () => {
      const program = makeProgram();
      registerShortcuts(program);

      await program.parseAsync(['node', 'mpga', 'secure']);

      const output = captured();
      expect(output).toContain('/mpga:secure');
      expect(output).toContain('security audit');
    });
  });

  describe('simplify', () => {
    it('prints instruction to use /mpga:simplify skill', async () => {
      const program = makeProgram();
      registerShortcuts(program);

      await program.parseAsync(['node', 'mpga', 'simplify']);

      const output = captured();
      expect(output).toContain('/mpga:simplify');
      expect(output).toContain('elegance');
    });

    it('accepts optional file arguments', async () => {
      const program = makeProgram();
      registerShortcuts(program);

      await program.parseAsync(['node', 'mpga', 'simplify', 'src/utils.ts']);

      const output = captured();
      expect(output).toContain('/mpga:simplify');
      expect(output).toContain('src/utils.ts');
    });
  });
});
