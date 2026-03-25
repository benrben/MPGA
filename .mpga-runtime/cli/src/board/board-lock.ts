import fs from 'fs';
import path from 'path';

const LOCK_FILENAME = '.board.lock';
const DEFAULT_STALE_TIMEOUT_MS = 30_000; // 30 seconds

interface LockContent {
  pid: number;
  timestamp: number;
}

/**
 * Acquire an advisory file lock for board.json concurrent access.
 *
 * Creates a `.board.lock` file in the given boardDir containing
 * the current process PID and a timestamp. If a lock already exists:
 * - If held by the same PID, re-acquisition succeeds (re-entrant).
 * - If the lock is older than `timeout` ms, it is considered stale and overridden.
 * - Otherwise, acquisition fails and returns false.
 *
 * @param boardDir - Directory containing board.json
 * @param timeout - Stale lock threshold in milliseconds (default: 30000)
 * @returns true if the lock was acquired, false otherwise
 */
export function acquireBoardLock(
  boardDir: string,
  timeout: number = DEFAULT_STALE_TIMEOUT_MS,
): boolean {
  fs.mkdirSync(boardDir, { recursive: true });
  const lockPath = path.join(boardDir, LOCK_FILENAME);
  const content: LockContent = { pid: process.pid, timestamp: Date.now() };

  try {
    // Atomic exclusive create — fails if file already exists (no TOCTOU)
    fs.writeFileSync(lockPath, JSON.stringify(content), { flag: 'wx' });
    return true;
  } catch {
    // Lock file exists — check if re-entrant or stale
    try {
      const existing: LockContent = JSON.parse(fs.readFileSync(lockPath, 'utf-8'));

      // Re-entrant: same PID can re-acquire
      if (existing.pid === process.pid) {
        fs.writeFileSync(lockPath, JSON.stringify(content));
        return true;
      }

      // Check for stale lock
      const age = Date.now() - existing.timestamp;
      if (age < timeout) {
        return false;
      }

      // Lock is stale — override it
      fs.writeFileSync(lockPath, JSON.stringify(content));
      return true;
    } catch {
      // Corrupted lock file — override it
      fs.writeFileSync(lockPath, JSON.stringify(content));
      return true;
    }
  }
}

/**
 * Release the advisory file lock for board.json.
 * Removes the `.board.lock` file if it exists. No-op if no lock exists.
 *
 * @param boardDir - Directory containing board.json
 */
export function releaseBoardLock(boardDir: string): void {
  const lockPath = path.join(boardDir, LOCK_FILENAME);
  if (fs.existsSync(lockPath)) {
    fs.unlinkSync(lockPath);
  }
}

/**
 * Convenience wrapper that acquires the board lock, runs the given function,
 * and releases the lock afterward (even if the function throws).
 *
 * @param boardDir - Directory containing board.json
 * @param fn - Function to execute while holding the lock
 * @returns The return value of fn
 * @throws Error if the lock cannot be acquired
 */
export function withBoardLock<T>(boardDir: string, fn: () => T): T {
  const acquired = acquireBoardLock(boardDir);
  if (!acquired) {
    throw new Error(`Could not acquire board lock in ${boardDir}`);
  }
  try {
    return fn();
  } finally {
    releaseBoardLock(boardDir);
  }
}
