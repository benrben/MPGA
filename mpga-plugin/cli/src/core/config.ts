import fs from 'fs';
import path from 'path';

export interface MpgaConfig {
  version: string;
  project: {
    name: string;
    languages: string[];
    entryPoints: string[];
    ignore: string[];
  };
  evidence: {
    strategy: 'hybrid' | 'ast-only' | 'line-only';
    lineRanges: boolean;
    astAnchors: boolean;
    autoHeal: boolean;
    coverageThreshold: number;
  };
  drift: {
    ciThreshold: number;
    hookMode: 'quick' | 'report';
    autoSync: boolean;
  };
  tiers: {
    hotMaxLines: number;
    warmMaxLinesPerScope: number;
    coldAutoArchiveAfterDays: number;
  };
  milestone: {
    branchStrategy: 'worktree' | 'branch';
    autoAdvance: boolean;
    squashOnComplete: boolean;
  };
  agents: {
    tddCycle: boolean;
    explorationCycle: boolean;
    researchBeforePlan: boolean;
  };
  scopes: {
    /** How many directory levels to use when grouping files into scopes.
     *  1 = top-level only (e.g. "mpga-plugin"),
     *  2 = two levels (e.g. "mpga-plugin/cli"),
     *  'auto' = use the deepest common src-like directory (recommended). */
    scopeDepth: number | 'auto';
    /** Max files per scope before suggesting a split */
    maxFilesPerScope: number;
  };
  board: {
    columns: string[];
    customColumns: string[];
    wipLimits: Record<string, number>;
    autoTransitions: boolean;
    archiveOnMilestoneComplete: boolean;
    taskIdPrefix: string;
    defaultPriority: 'critical' | 'high' | 'medium' | 'low';
    defaultTimeEstimate: string;
    showTddStage: boolean;
    showEvidenceStatus: boolean;
    githubSync: boolean;
  };
}

export const DEFAULT_CONFIG: MpgaConfig = {
  version: '1.0.0',
  project: {
    name: path.basename(process.cwd()),
    languages: ['typescript'],
    entryPoints: [],
    ignore: ['node_modules', 'dist', '.git', 'MPGA/'],
  },
  evidence: {
    strategy: 'hybrid',
    lineRanges: true,
    astAnchors: true,
    autoHeal: true,
    coverageThreshold: 0.20,
  },
  drift: {
    ciThreshold: 80,
    hookMode: 'quick',
    autoSync: false,
  },
  tiers: {
    hotMaxLines: 500,
    warmMaxLinesPerScope: 300,
    coldAutoArchiveAfterDays: 30,
  },
  milestone: {
    branchStrategy: 'worktree',
    autoAdvance: false,
    squashOnComplete: true,
  },
  agents: {
    tddCycle: true,
    explorationCycle: true,
    researchBeforePlan: true,
  },
  scopes: {
    scopeDepth: 'auto' as const,
    maxFilesPerScope: 15,
  },
  board: {
    columns: ['backlog', 'todo', 'in-progress', 'testing', 'review', 'done'],
    customColumns: [],
    wipLimits: { 'in-progress': 3, testing: 3, review: 2 },
    autoTransitions: true,
    archiveOnMilestoneComplete: true,
    taskIdPrefix: 'T',
    defaultPriority: 'medium',
    defaultTimeEstimate: '5min',
    showTddStage: true,
    showEvidenceStatus: true,
    githubSync: false,
  },
};

export function findProjectRoot(startDir = process.cwd()): string | null {
  let dir = startDir;
  // eslint-disable-next-line no-constant-condition
  while (true) {
    if (fs.existsSync(path.join(dir, 'mpga.config.json'))) return dir;
    if (fs.existsSync(path.join(dir, 'MPGA', 'mpga.config.json'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

export function loadConfig(projectRoot?: string): MpgaConfig {
  const root = projectRoot ?? findProjectRoot() ?? process.cwd();
  const configPath = fs.existsSync(path.join(root, 'mpga.config.json'))
    ? path.join(root, 'mpga.config.json')
    : path.join(root, 'MPGA', 'mpga.config.json');

  if (!fs.existsSync(configPath)) {
    return { ...DEFAULT_CONFIG, project: { ...DEFAULT_CONFIG.project, name: path.basename(root) } };
  }

  const raw = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
  return deepMerge(DEFAULT_CONFIG, raw) as MpgaConfig;
}

export function saveConfig(config: MpgaConfig, configPath: string): void {
  fs.mkdirSync(path.dirname(configPath), { recursive: true });
  fs.writeFileSync(configPath, JSON.stringify(config, null, 2) + '\n');
}

export function getConfigValue(config: MpgaConfig, key: string): unknown {
  const parts = key.split('.');
  let obj: unknown = config;
  for (const part of parts) {
    if (obj == null || typeof obj !== 'object') return undefined;
    obj = (obj as Record<string, unknown>)[part];
  }
  return obj;
}

export function setConfigValue(config: MpgaConfig, key: string, value: string): void {
  const parts = key.split('.');
  let obj: Record<string, unknown> = config as unknown as Record<string, unknown>;
  for (let i = 0; i < parts.length - 1; i++) {
    obj = obj[parts[i]] as Record<string, unknown>;
  }
  const last = parts[parts.length - 1];
  // Coerce to appropriate type
  const existing = obj[last];
  if (typeof existing === 'number') obj[last] = Number(value);
  else if (typeof existing === 'boolean') obj[last] = value === 'true';
  else obj[last] = value;
}

function deepMerge(base: unknown, override: unknown): unknown {
  if (Array.isArray(override)) return override;
  if (Array.isArray(base)) return override ?? base;
  if (typeof base !== 'object' || base === null) return override ?? base;
  if (typeof override !== 'object' || override === null) return override ?? base;
  const result = { ...(base as Record<string, unknown>) };
  for (const key of Object.keys(override as Record<string, unknown>)) {
    result[key] = deepMerge(
      (base as Record<string, unknown>)[key],
      (override as Record<string, unknown>)[key]
    );
  }
  return result;
}
