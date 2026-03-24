import fs from 'fs';
import path from 'path';

const RUNTIME_ASSETS = ['bin', 'scripts', 'cli'] as const;
const COPY_EXCLUDES = new Set(['node_modules', '.git', 'coverage']);

function copyTree(src: string, dest: string): void {
  const stats = fs.statSync(src);
  if (stats.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true });
    for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
      if (COPY_EXCLUDES.has(entry.name)) continue;
      copyTree(path.join(src, entry.name), path.join(dest, entry.name));
    }
    return;
  }

  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
}

export function projectVendoredCliCommand(): string {
  return 'node ./.mpga-runtime/cli/dist/index.js';
}

export function globalVendoredCliCommand(baseDir: string): string {
  return path.join(baseDir, '.mpga-runtime', 'cli', 'dist', 'index.js').replace(/\\/g, '/');
}

export function copyVendoredRuntime(targetRoot: string, pluginRoot: string | null): string | null {
  if (!pluginRoot) return null;

  const runtimeDir = path.join(targetRoot, '.mpga-runtime');
  const copiedAssets: string[] = [];

  fs.mkdirSync(runtimeDir, { recursive: true });
  for (const asset of RUNTIME_ASSETS) {
    const srcPath = path.join(pluginRoot, asset);
    if (!fs.existsSync(srcPath)) continue;
    copyTree(srcPath, path.join(runtimeDir, asset));
    copiedAssets.push(asset);
  }

  fs.writeFileSync(
    path.join(runtimeDir, 'manifest.json'),
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        source_root: pluginRoot.replace(/\\/g, '/'),
        assets: copiedAssets,
      },
      null,
      2,
    ) + '\n',
  );

  return runtimeDir;
}
