import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { DEFAULT_CONFIG, loadConfig, saveConfig, getConfigValue, setConfigValue } from './config.js';

describe('DEFAULT_CONFIG', () => {
  it('has expected default values', () => {
    expect(DEFAULT_CONFIG.version).toBe('1.0.0');
    expect(DEFAULT_CONFIG.evidence.strategy).toBe('hybrid');
    expect(DEFAULT_CONFIG.drift.ciThreshold).toBe(80);
    expect(DEFAULT_CONFIG.board.columns).toContain('backlog');
    expect(DEFAULT_CONFIG.board.columns).toContain('done');
    expect(DEFAULT_CONFIG.scopes.scopeDepth).toBe('auto');
  });
});

describe('getConfigValue', () => {
  it('gets nested values by dot path', () => {
    expect(getConfigValue(DEFAULT_CONFIG, 'evidence.strategy')).toBe('hybrid');
    expect(getConfigValue(DEFAULT_CONFIG, 'drift.ciThreshold')).toBe(80);
    expect(getConfigValue(DEFAULT_CONFIG, 'board.columns')).toEqual(DEFAULT_CONFIG.board.columns);
  });

  it('returns undefined for missing paths', () => {
    expect(getConfigValue(DEFAULT_CONFIG, 'does.not.exist')).toBeUndefined();
  });

  it('returns top-level values', () => {
    expect(getConfigValue(DEFAULT_CONFIG, 'version')).toBe('1.0.0');
  });
});

describe('setConfigValue', () => {
  it('sets a numeric value', () => {
    const config = structuredClone(DEFAULT_CONFIG);
    setConfigValue(config, 'drift.ciThreshold', '90');
    expect(config.drift.ciThreshold).toBe(90);
  });

  it('sets a boolean value', () => {
    const config = structuredClone(DEFAULT_CONFIG);
    setConfigValue(config, 'evidence.autoHeal', 'false');
    expect(config.evidence.autoHeal).toBe(false);
  });

  it('sets a string value', () => {
    const config = structuredClone(DEFAULT_CONFIG);
    setConfigValue(config, 'evidence.strategy', 'ast-only');
    expect(config.evidence.strategy).toBe('ast-only');
  });
});

describe('saveConfig / loadConfig', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-test-'));
    fs.mkdirSync(path.join(tmpDir, 'MPGA'), { recursive: true });
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('saves and loads config round-trip', () => {
    const configPath = path.join(tmpDir, 'MPGA', 'mpga.config.json');
    const config = { ...DEFAULT_CONFIG, project: { ...DEFAULT_CONFIG.project, name: 'test-proj' } };
    saveConfig(config, configPath);

    const loaded = loadConfig(tmpDir);
    expect(loaded.project.name).toBe('test-proj');
    expect(loaded.evidence.strategy).toBe('hybrid');
  });

  it('returns defaults when no config file exists', () => {
    const emptyDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-empty-'));
    const loaded = loadConfig(emptyDir);
    expect(loaded.evidence.strategy).toBe('hybrid');
    expect(loaded.drift.ciThreshold).toBe(80);
    fs.rmSync(emptyDir, { recursive: true, force: true });
  });
});
