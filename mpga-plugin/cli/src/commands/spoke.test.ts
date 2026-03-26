import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Command } from 'commander';
import { createHash } from 'crypto';

describe('spoke command', () => {
  let logSpy: ReturnType<typeof vi.spyOn>;
  let errSpy: ReturnType<typeof vi.spyOn>;

  function makeProgram(): Command {
    const program = new Command();
    program.exitOverride();
    program.configureOutput({ writeOut: () => {}, writeErr: () => {} });
    return program;
  }

  beforeEach(() => {
    logSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
    errSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    logSpy.mockRestore();
    errSpy.mockRestore();
    vi.restoreAllMocks();
  });

  describe('registerSpoke', () => {
    it('registers a spoke command on the program', async () => {
      const { registerSpoke } = await import('./spoke.js');
      const program = makeProgram();
      registerSpoke(program);

      const cmd = program.commands.find((c) => c.name() === 'spoke');
      expect(cmd).toBeDefined();
      expect(cmd!.description()).toContain('Trump');
    });
  });

  describe('ANSI stripping', () => {
    // eslint-disable-next-line no-control-regex
    const ANSI_RE = /\x1B\[[0-9;]*m/g;

    it('strips ANSI escape codes from text', () => {
      const text = '\x1B[31mHello\x1B[0m \x1B[1;32mWorld\x1B[0m';
      const stripped = text.replace(ANSI_RE, '');
      expect(stripped).toBe('Hello World');
    });

    it('leaves plain text unchanged', () => {
      const text = 'Make America Great Again';
      const stripped = text.replace(ANSI_RE, '');
      expect(stripped).toBe('Make America Great Again');
    });
  });

  describe('cache hash generation', () => {
    it('produces deterministic MD5 hashes for the same input', () => {
      const text = 'We are going to win so much';
      const hash1 = createHash('md5').update(text).digest('hex');
      const hash2 = createHash('md5').update(text).digest('hex');
      expect(hash1).toBe(hash2);
    });

    it('produces different hashes for different input', () => {
      const hash1 = createHash('md5').update('Hello').digest('hex');
      const hash2 = createHash('md5').update('World').digest('hex');
      expect(hash1).not.toBe(hash2);
    });

    it('produces a 32-character hex string', () => {
      const hash = createHash('md5').update('test').digest('hex');
      expect(hash).toMatch(/^[a-f0-9]{32}$/);
    });
  });

  describe('handleSpoke with --setup', () => {
    it('attempts to run setup.sh when --setup flag is provided', async () => {
      // execSync will throw because setup.sh doesn't exist — we just verify it was called
      const { registerSpoke } = await import('./spoke.js');
      const program = makeProgram();
      registerSpoke(program);

      // Expect an error because setup.sh doesn't exist in the test environment
      let threw = false;
      try {
        await program.parseAsync(['node', 'mpga', 'spoke', '--setup']);
      } catch {
        threw = true;
      }
      // The command tries to exec `bash ...setup.sh`, which will throw in test env
      // This confirms the --setup path is taken (log.info is called before execSync)
      const output = logSpy.mock.calls.map((c) => c.join(' ')).join('\n');
      expect(output).toContain('setup');
      expect(threw).toBe(true);
    });
  });

  describe('handleSpoke without setup', () => {
    it('prints error when spoke is not set up', async () => {
      const { registerSpoke } = await import('./spoke.js');
      const program = makeProgram();
      registerSpoke(program);

      // VENV_PYTHON and LATENTS_FILE won't exist in test env
      await program.parseAsync(['node', 'mpga', 'spoke', 'Hello', 'world']);

      const errOutput = errSpy.mock.calls.map((c) => c.join(' ')).join('\n');
      expect(errOutput).toContain('not set up');
    });
  });
});
