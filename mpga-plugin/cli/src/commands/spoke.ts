// mpga spoke <text> — Speak text in Trump's voice via F5-TTS
// Streams audio chunks for low-latency playback.

import { Command } from 'commander';
import { execSync, spawn, spawnSync } from 'child_process';
import { createHash } from 'crypto';
import { existsSync, mkdirSync, writeFileSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { log } from '../core/logger.js';
import { request } from 'http';
import { createInterface } from 'readline';

const SPOKE_DIR = join(process.cwd(), '.mpga-runtime', 'spoke');
const CACHE_DIR = join(homedir(), '.mpga', 'spoke-cache');
const VENV_PYTHON = join(SPOKE_DIR, 'venv', 'bin', 'python3');
const REF_AUDIO = join(SPOKE_DIR, 'voicedata', 'trump_ref.wav');
const SERVER_SCRIPT = join(SPOKE_DIR, 'server.py');
const PID_FILE = join(SPOKE_DIR, '.server.pid');
const PORT = 5151;

function isServerRunning(): boolean {
  const result = spawnSync('curl', ['-sf', `http://127.0.0.1:${PORT}/health`], { timeout: 1000 });
  return result.status === 0;
}

function startServer(): void {
  log.info('Starting spoke server (loading model, one-time ~10s)...');
  const child = spawn(VENV_PYTHON, [SERVER_SCRIPT, '--port', String(PORT)], {
    detached: true,
    stdio: 'ignore',
  });
  child.unref();
  writeFileSync(PID_FILE, String(child.pid));

  for (let i = 0; i < 40; i++) {
    const result = spawnSync('curl', ['-sf', `http://127.0.0.1:${PORT}/health`], { timeout: 2000 });
    if (result.status === 0) return;
    spawnSync('sleep', ['1']);
  }
  log.error('Server failed to start');
}

function generateViaServer(text: string, wavPath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ text });
    const req = request(
      {
        hostname: '127.0.0.1',
        port: PORT,
        path: '/generate',
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
        timeout: 120000,
      },
      (res) => {
        const chunks: Buffer[] = [];
        res.on('data', (chunk: Buffer) => chunks.push(chunk));
        res.on('end', () => {
          if (res.statusCode === 200) {
            writeFileSync(wavPath, Buffer.concat(chunks));
            resolve();
          } else {
            reject(new Error(`Server returned ${res.statusCode}`));
          }
        });
      },
    );
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

/** Stream via server — plays each sentence chunk as it's generated. */
function streamViaServer(text: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ text });
    const req = request(
      {
        hostname: '127.0.0.1',
        port: PORT,
        path: '/stream',
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
        timeout: 300000,
      },
      (res) => {
        if (res.statusCode !== 200) {
          reject(new Error(`Server returned ${res.statusCode}`));
          return;
        }
        const rl = createInterface({ input: res });
        const playQueue: string[] = [];
        let playing = false;

        function playNext() {
          if (playQueue.length === 0) {
            playing = false;
            return;
          }
          playing = true;
          const wavFile = playQueue.shift()!;
          const child = spawn('afplay', [wavFile], { stdio: 'ignore' });
          child.on('close', playNext);
        }

        rl.on('line', (line: string) => {
          try {
            const data = JSON.parse(line);
            if (data.file) {
              playQueue.push(data.file);
              if (!playing) playNext();
            }
          } catch {
            /* skip bad lines */
          }
        });
        rl.on('close', () => {
          // Wait for all audio to finish
          const wait = () => {
            if (!playing && playQueue.length === 0) resolve();
            else setTimeout(wait, 200);
          };
          wait();
        });
      },
    );
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function handleSpoke(
  textParts: string[],
  opts: { setup?: boolean; cache: boolean; stream?: boolean },
): Promise<void> {
  if (opts.setup) {
    const setupScript = join(SPOKE_DIR, 'setup.sh');
    log.info('Running spoke setup...');
    execSync(`bash ${setupScript}`, { stdio: 'inherit' });
    return;
  }

  if (!existsSync(VENV_PYTHON) || !existsSync(REF_AUDIO)) {
    log.error('Spoke not set up. Run: mpga spoke --setup');
    return;
  }

  const text = textParts.join(' ');
  if (!text) {
    log.error('No text provided. Usage: mpga spoke "Your text here"');
    return;
  }

  const cleanText = text.replace(
    // eslint-disable-next-line no-control-regex
    /\x1B\[[0-9;]*m/g,
    '',
  );

  if (!isServerRunning()) {
    startServer();
  }

  // Stream mode — play sentence by sentence as generated
  if (opts.stream) {
    try {
      await streamViaServer(cleanText);
    } catch {
      log.error('Streaming TTS failed');
    }
    return;
  }

  // Single-shot mode with cache
  const hash = createHash('md5').update(cleanText).digest('hex');
  const wavPath = join(CACHE_DIR, `${hash}.wav`);

  if (!existsSync(CACHE_DIR)) {
    mkdirSync(CACHE_DIR, { recursive: true });
  }

  if (opts.cache && existsSync(wavPath)) {
    spawn('afplay', [wavPath], { detached: true, stdio: 'ignore' }).unref();
    return;
  }

  try {
    await generateViaServer(cleanText, wavPath);
  } catch {
    log.error('TTS generation failed');
    return;
  }

  spawn('afplay', [wavPath], { detached: true, stdio: 'ignore' }).unref();
}

export function registerSpoke(program: Command): void {
  program
    .command('spoke [text...]')
    .description('Speak text in Trump voice via F5-TTS — TREMENDOUS')
    .option('--setup', 'Run one-time setup (install deps, download voice)')
    .option('--no-cache', 'Skip cache, regenerate audio')
    .option('--stream', 'Stream sentence-by-sentence (play while generating)')
    .action(handleSpoke);
}
