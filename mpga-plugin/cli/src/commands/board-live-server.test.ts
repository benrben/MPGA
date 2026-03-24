import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { EventEmitter } from 'events';
import { createBoardLiveServer } from './board-live-server.js';

class MockResponse extends EventEmitter {
  statusCode = 200;
  headers: Record<string, string> = {};
  body = '';

  writeHead(statusCode: number, headers: Record<string, string> = {}): this {
    this.statusCode = statusCode;
    this.headers = headers;
    return this;
  }

  end(chunk?: string | Buffer): this {
    if (chunk) this.body += chunk.toString();
    this.emit('finish');
    return this;
  }
}

describe('createBoardLiveServer', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-live-server-'));
    fs.writeFileSync(path.join(tmpDir, 'index.html'), '<!doctype html><h1>Board</h1>');
    fs.writeFileSync(path.join(tmpDir, 'snapshot.json'), '{"ok":true}\n');
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('serves index.html and snapshot.json from the live board directory', async () => {
    const server = createBoardLiveServer(tmpDir);

    const indexResponse = new MockResponse();
    const snapshotResponse = new MockResponse();

    await new Promise<void>((resolve) => {
      indexResponse.once('finish', resolve);
      server.emit('request', { url: '/' }, indexResponse);
    });

    await new Promise<void>((resolve) => {
      snapshotResponse.once('finish', resolve);
      server.emit('request', { url: '/snapshot.json' }, snapshotResponse);
    });

    expect(indexResponse.statusCode).toBe(200);
    expect(indexResponse.body).toContain('Board');
    expect(indexResponse.headers['Content-Type']).toContain('text/html');
    expect(snapshotResponse.statusCode).toBe(200);
    expect(snapshotResponse.body).toContain('"ok":true');
    expect(snapshotResponse.headers['Content-Type']).toContain('application/json');
  });
});
