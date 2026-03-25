import fs from 'fs';
import http, { type Server } from 'http';
import path from 'path';
import { spawn } from 'child_process';

const CONTENT_TYPES: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
};

function resolveRequestPath(liveDir: string, requestUrl?: string): string | null {
  const pathname = new URL(requestUrl ?? '/', 'http://127.0.0.1').pathname;
  const relativePath = pathname === '/' ? 'index.html' : pathname.replace(/^\/+/, '');
  const resolved = path.resolve(liveDir, relativePath);
  const liveRoot = path.resolve(liveDir) + path.sep;
  return resolved.startsWith(liveRoot) || resolved === path.resolve(liveDir, 'index.html')
    ? resolved
    : null;
}

export function createBoardLiveServer(liveDir: string): Server {
  return http.createServer((req, res) => {
    const filePath = resolveRequestPath(liveDir, req.url);
    if (!filePath) {
      res.writeHead(403);
      res.end('Forbidden');
      return;
    }

    if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
      res.writeHead(404);
      res.end('Not found');
      return;
    }

    res.writeHead(200, {
      'Content-Type': CONTENT_TYPES[path.extname(filePath)] ?? 'application/octet-stream',
      'Cache-Control': 'no-store',
    });
    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(500);
        res.end('Internal Server Error');
        return;
      }
      res.end(data);
    });
  });
}

export function openBoardLiveUrl(url: string): void {
  const command =
    process.platform === 'darwin'
      ? ['open', url]
      : process.platform === 'win32'
        ? ['cmd', '/c', 'start', '', url]
        : ['xdg-open', url];

  const child = spawn(command[0]!, command.slice(1), {
    detached: true,
    stdio: 'ignore',
  });
  child.unref();
}
