import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { acquireBoardLock, releaseBoardLock, withBoardLock } from './board-lock.js';

describe('board-lock', () => {
  let tmpDir: string;
  let boardDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-lock-'));
    boardDir = path.join(tmpDir, 'MPGA', 'board');
    fs.mkdirSync(boardDir, { recursive: true });
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('acquireBoardLock creates a .board.lock file', () => {
    const acquired = acquireBoardLock(boardDir);
    expect(acquired).toBe(true);
    const lockPath = path.join(boardDir, '.board.lock');
    expect(fs.existsSync(lockPath)).toBe(true);

    // Lock file should contain PID and timestamp
    const content = JSON.parse(fs.readFileSync(lockPath, 'utf-8'));
    expect(content).toHaveProperty('pid');
    expect(content).toHaveProperty('timestamp');
    expect(typeof content.pid).toBe('number');
    expect(typeof content.timestamp).toBe('number');
  });

  it('releaseBoardLock removes the .board.lock file', () => {
    acquireBoardLock(boardDir);
    const lockPath = path.join(boardDir, '.board.lock');
    expect(fs.existsSync(lockPath)).toBe(true);

    releaseBoardLock(boardDir);
    expect(fs.existsSync(lockPath)).toBe(false);
  });

  it('releaseBoardLock is a no-op when no lock exists', () => {
    // Should not throw
    expect(() => releaseBoardLock(boardDir)).not.toThrow();
  });

  it('acquireBoardLock returns false when already locked by another process', () => {
    // Simulate a lock held by a different PID
    const lockPath = path.join(boardDir, '.board.lock');
    const fakePid = process.pid + 99999; // Very unlikely to be a real PID
    fs.writeFileSync(
      lockPath,
      JSON.stringify({ pid: fakePid, timestamp: Date.now() }),
    );

    const acquired = acquireBoardLock(boardDir);
    expect(acquired).toBe(false);
  });

  it('acquireBoardLock succeeds when lock is held by current process (re-entrant)', () => {
    const first = acquireBoardLock(boardDir);
    expect(first).toBe(true);

    // Same PID should be able to re-acquire
    const second = acquireBoardLock(boardDir);
    expect(second).toBe(true);
  });

  it('acquireBoardLock overrides stale lock (older than timeout)', () => {
    const lockPath = path.join(boardDir, '.board.lock');
    const fakePid = process.pid + 99999;
    const staleTimestamp = Date.now() - 60_000; // 60 seconds ago (well past 30s default)
    fs.writeFileSync(
      lockPath,
      JSON.stringify({ pid: fakePid, timestamp: staleTimestamp }),
    );

    const acquired = acquireBoardLock(boardDir);
    expect(acquired).toBe(true);

    // Lock file should now reflect current process
    const content = JSON.parse(fs.readFileSync(lockPath, 'utf-8'));
    expect(content.pid).toBe(process.pid);
  });

  it('acquireBoardLock respects custom timeout for stale detection', () => {
    const lockPath = path.join(boardDir, '.board.lock');
    const fakePid = process.pid + 99999;
    // 10 seconds ago — stale with 5s timeout, not stale with 30s default
    const timestamp = Date.now() - 10_000;
    fs.writeFileSync(
      lockPath,
      JSON.stringify({ pid: fakePid, timestamp }),
    );

    // With 30s default timeout, should NOT be stale
    expect(acquireBoardLock(boardDir, 30_000)).toBe(false);

    // With 5s custom timeout, should be stale and overridable
    expect(acquireBoardLock(boardDir, 5_000)).toBe(true);
  });

  it('withBoardLock acquires, runs function, and releases', () => {
    const result = withBoardLock(boardDir, () => {
      // Lock should exist inside the callback
      const lockPath = path.join(boardDir, '.board.lock');
      expect(fs.existsSync(lockPath)).toBe(true);
      return 42;
    });

    expect(result).toBe(42);
    // Lock should be released after
    const lockPath = path.join(boardDir, '.board.lock');
    expect(fs.existsSync(lockPath)).toBe(false);
  });

  it('withBoardLock releases lock even if function throws', () => {
    expect(() =>
      withBoardLock(boardDir, () => {
        throw new Error('boom');
      }),
    ).toThrow('boom');

    const lockPath = path.join(boardDir, '.board.lock');
    expect(fs.existsSync(lockPath)).toBe(false);
  });

  it('withBoardLock throws when lock cannot be acquired', () => {
    // Simulate a held lock by another process
    const lockPath = path.join(boardDir, '.board.lock');
    const fakePid = process.pid + 99999;
    fs.writeFileSync(
      lockPath,
      JSON.stringify({ pid: fakePid, timestamp: Date.now() }),
    );

    expect(() =>
      withBoardLock(boardDir, () => 'should not run'),
    ).toThrow(/Could not acquire board lock/);
  });

  it('acquireBoardLock creates boardDir if it does not exist', () => {
    const newBoardDir = path.join(tmpDir, 'new', 'board');
    const acquired = acquireBoardLock(newBoardDir);
    expect(acquired).toBe(true);
    expect(fs.existsSync(path.join(newBoardDir, '.board.lock'))).toBe(true);
  });
});
