import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { detectLanguage, extractSymbols, findSymbol, verifyRange } from './ast.js';

describe('detectLanguage', () => {
  it('maps .ts to typescript', () => {
    expect(detectLanguage('src/index.ts')).toBe('typescript');
  });

  it('maps .tsx to typescript', () => {
    expect(detectLanguage('App.tsx')).toBe('typescript');
  });

  it('maps .js to javascript', () => {
    expect(detectLanguage('lib/utils.js')).toBe('javascript');
  });

  it('maps .jsx to javascript', () => {
    expect(detectLanguage('components/App.jsx')).toBe('javascript');
  });

  it('maps .mjs to javascript', () => {
    expect(detectLanguage('module.mjs')).toBe('javascript');
  });

  it('maps .py to python', () => {
    expect(detectLanguage('main.py')).toBe('python');
  });

  it('maps .go to go', () => {
    expect(detectLanguage('cmd/server.go')).toBe('go');
  });

  it('maps .rs to rust', () => {
    expect(detectLanguage('src/lib.rs')).toBe('rust');
  });

  it('maps .java to java', () => {
    expect(detectLanguage('src/Main.java')).toBe('java');
  });

  it('maps .cs to csharp', () => {
    expect(detectLanguage('Program.cs')).toBe('csharp');
  });

  it('maps .rb to ruby', () => {
    expect(detectLanguage('app.rb')).toBe('ruby');
  });

  it('maps .php to php', () => {
    expect(detectLanguage('index.php')).toBe('php');
  });

  it('returns unknown for unrecognized extension', () => {
    expect(detectLanguage('file.unknown')).toBe('unknown');
  });

  it('returns unknown for files with no extension', () => {
    expect(detectLanguage('Makefile')).toBe('unknown');
  });
});

describe('extractSymbols', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-ast-test-'));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('returns empty array for nonexistent file', () => {
    const result = extractSymbols('nonexistent.ts', tmpDir);
    expect(result).toEqual([]);
  });

  it('extracts TypeScript function declarations', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'funcs.ts'),
      [
        'export function greet(name: string): string {',
        '  return `Hello ${name}`;',
        '}',
        '',
        'function helper() {',
        '  return 42;',
        '}',
      ].join('\n'),
    );

    const symbols = extractSymbols('funcs.ts', tmpDir);
    const names = symbols.map((s) => s.name);
    expect(names).toContain('greet');
    expect(names).toContain('helper');
    expect(symbols.find((s) => s.name === 'greet')?.type).toBe('function');
    expect(symbols.find((s) => s.name === 'helper')?.type).toBe('function');
  });

  it('extracts async function declarations', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'async.ts'),
      ['export async function fetchData() {', '  return await fetch("/api");', '}'].join('\n'),
    );

    const symbols = extractSymbols('async.ts', tmpDir);
    expect(symbols).toHaveLength(1);
    expect(symbols[0].name).toBe('fetchData');
    expect(symbols[0].type).toBe('function');
  });

  it('extracts TypeScript class declarations', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'classes.ts'),
      [
        'export class UserService {',
        '  getUser() {',
        '    return null;',
        '  }',
        '}',
        '',
        'abstract class BaseModel {',
        '  abstract validate(): boolean;',
        '}',
      ].join('\n'),
    );

    const symbols = extractSymbols('classes.ts', tmpDir);
    const names = symbols.map((s) => s.name);
    expect(names).toContain('UserService');
    expect(names).toContain('BaseModel');
    expect(symbols.find((s) => s.name === 'UserService')?.type).toBe('class');
    expect(symbols.find((s) => s.name === 'BaseModel')?.type).toBe('class');
  });

  it('extracts TypeScript type and interface declarations', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'types.ts'),
      [
        'export type UserId = string;',
        '',
        'export interface Config {',
        '  host: string;',
        '  port: number;',
        '}',
        '',
        'type Internal = { key: string };',
      ].join('\n'),
    );

    const symbols = extractSymbols('types.ts', tmpDir);
    const names = symbols.map((s) => s.name);
    expect(names).toContain('UserId');
    expect(names).toContain('Config');
    expect(names).toContain('Internal');
    symbols
      .filter((s) => ['UserId', 'Config', 'Internal'].includes(s.name))
      .forEach((s) => expect(s.type).toBe('type'));
  });

  it('extracts arrow function assignments', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'arrows.ts'),
      [
        'export const add = (a: number, b: number) => a + b;',
        '',
        'const multiply = (x: number, y: number) => {',
        '  return x * y;',
        '};',
      ].join('\n'),
    );

    const symbols = extractSymbols('arrows.ts', tmpDir);
    const names = symbols.map((s) => s.name);
    expect(names).toContain('add');
    expect(names).toContain('multiply');
    expect(symbols.find((s) => s.name === 'add')?.type).toBe('function');
    expect(symbols.find((s) => s.name === 'multiply')?.type).toBe('function');
  });

  it('extracts const function expressions', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'funcexpr.ts'),
      ['export const handler = function handleRequest() {', '  return "ok";', '};'].join('\n'),
    );

    const symbols = extractSymbols('funcexpr.ts', tmpDir);
    const names = symbols.map((s) => s.name);
    expect(names).toContain('handler');
    expect(symbols.find((s) => s.name === 'handler')?.type).toBe('function');
  });

  it('extracts const variable declarations', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'vars.ts'),
      ['export const MAX_RETRIES = 3;', 'const BASE_URL = "http://localhost";'].join('\n'),
    );

    const symbols = extractSymbols('vars.ts', tmpDir);
    const names = symbols.map((s) => s.name);
    expect(names).toContain('MAX_RETRIES');
    expect(names).toContain('BASE_URL');
    expect(symbols.find((s) => s.name === 'MAX_RETRIES')?.type).toBe('variable');
    expect(symbols.find((s) => s.name === 'BASE_URL')?.type).toBe('variable');
  });

  it('extracts methods inside classes', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'methods.ts'),
      [
        'class Router {',
        '  handle(req: Request) {',
        '    return null;',
        '  }',
        '',
        '  async process(data: string) {',
        '    return data;',
        '  }',
        '}',
      ].join('\n'),
    );

    const symbols = extractSymbols('methods.ts', tmpDir);
    const names = symbols.map((s) => s.name);
    expect(names).toContain('handle');
    expect(names).toContain('process');
    expect(symbols.find((s) => s.name === 'handle')?.type).toBe('method');
    expect(symbols.find((s) => s.name === 'process')?.type).toBe('method');
  });

  it('assigns correct line numbers', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'lines.ts'),
      [
        'function first() {',
        '  return 1;',
        '}',
        '',
        'function second() {',
        '  return 2;',
        '}',
      ].join('\n'),
    );

    const symbols = extractSymbols('lines.ts', tmpDir);
    const first = symbols.find((s) => s.name === 'first');
    const second = symbols.find((s) => s.name === 'second');
    expect(first?.startLine).toBe(1);
    expect(second?.startLine).toBe(5);
  });

  it('does not extract keywords as symbols', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'keywords.ts'),
      [
        'function realFunc() {',
        '  if (true) {',
        '    for (let i = 0; i < 10; i++) {',
        '      while (false) {}',
        '    }',
        '  }',
        '  return 1;',
        '}',
      ].join('\n'),
    );

    const symbols = extractSymbols('keywords.ts', tmpDir);
    const names = symbols.map((s) => s.name);
    expect(names).not.toContain('if');
    expect(names).not.toContain('for');
    expect(names).not.toContain('while');
    expect(names).toContain('realFunc');
  });

  describe('Python', () => {
    it('extracts def and class declarations', () => {
      fs.writeFileSync(
        path.join(tmpDir, 'module.py'),
        [
          'def greet(name):',
          '    return f"Hello {name}"',
          '',
          'class UserService:',
          '    def get_user(self):',
          '        return None',
          '',
          'def process():',
          '    pass',
        ].join('\n'),
      );

      const symbols = extractSymbols('module.py', tmpDir);
      const names = symbols.map((s) => s.name);
      expect(names).toContain('greet');
      expect(names).toContain('UserService');
      expect(names).toContain('get_user');
      expect(names).toContain('process');
      expect(symbols.find((s) => s.name === 'greet')?.type).toBe('function');
      expect(symbols.find((s) => s.name === 'UserService')?.type).toBe('class');
      expect(symbols.find((s) => s.name === 'get_user')?.type).toBe('method');
    });
  });

  describe('Go', () => {
    it('extracts func and type struct declarations', () => {
      fs.writeFileSync(
        path.join(tmpDir, 'main.go'),
        [
          'package main',
          '',
          'func main() {',
          '    fmt.Println("hello")',
          '}',
          '',
          'type Server struct {',
          '    Host string',
          '    Port int',
          '}',
          '',
          'func (s *Server) Start() {',
          '    // start',
          '}',
          '',
          'type Handler interface {',
          '    Handle()',
          '}',
        ].join('\n'),
      );

      const symbols = extractSymbols('main.go', tmpDir);
      const names = symbols.map((s) => s.name);
      expect(names).toContain('main');
      expect(names).toContain('Server');
      expect(names).toContain('Start');
      expect(names).toContain('Handler');
      expect(symbols.find((s) => s.name === 'main')?.type).toBe('function');
      expect(symbols.find((s) => s.name === 'Server')?.type).toBe('class');
      expect(symbols.find((s) => s.name === 'Start')?.type).toBe('function');
      expect(symbols.find((s) => s.name === 'Handler')?.type).toBe('type');
    });
  });

  describe('Rust', () => {
    it('extracts fn, struct, and trait declarations', () => {
      fs.writeFileSync(
        path.join(tmpDir, 'lib.rs'),
        [
          'pub fn initialize() {',
          '    // init',
          '}',
          '',
          'pub struct Config {',
          '    pub host: String,',
          '}',
          '',
          'pub trait Service {',
          '    fn run(&self);',
          '}',
          '',
          'async fn fetch_data() {',
          '    // fetch',
          '}',
        ].join('\n'),
      );

      const symbols = extractSymbols('lib.rs', tmpDir);
      const names = symbols.map((s) => s.name);
      expect(names).toContain('initialize');
      expect(names).toContain('Config');
      expect(names).toContain('Service');
      expect(names).toContain('fetch_data');
      expect(symbols.find((s) => s.name === 'initialize')?.type).toBe('function');
      expect(symbols.find((s) => s.name === 'Config')?.type).toBe('class');
      expect(symbols.find((s) => s.name === 'Service')?.type).toBe('type');
      expect(symbols.find((s) => s.name === 'fetch_data')?.type).toBe('function');
    });
  });
});

describe('findSymbol', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-ast-find-'));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('finds an existing symbol by name', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'mod.ts'),
      [
        'export function alpha() {',
        '  return "a";',
        '}',
        '',
        'export function beta() {',
        '  return "b";',
        '}',
      ].join('\n'),
    );

    const result = findSymbol('mod.ts', 'beta', tmpDir);
    expect(result).not.toBeNull();
    expect(result!.name).toBe('beta');
    expect(result!.type).toBe('function');
    expect(result!.startLine).toBe(5);
  });

  it('returns null for a symbol that does not exist', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'mod.ts'),
      ['function exists() {', '  return true;', '}'].join('\n'),
    );

    const result = findSymbol('mod.ts', 'doesNotExist', tmpDir);
    expect(result).toBeNull();
  });

  it('returns null for a nonexistent file', () => {
    const result = findSymbol('nope.ts', 'anything', tmpDir);
    expect(result).toBeNull();
  });
});

describe('verifyRange', () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mpga-ast-verify-'));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it('returns true when the range contains the specified symbol', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'code.ts'),
      ['const x = 1;', 'function doSomething() {', '  return x + 1;', '}', 'const y = 2;'].join(
        '\n',
      ),
    );

    expect(verifyRange('code.ts', 2, 4, 'doSomething', tmpDir)).toBe(true);
  });

  it('returns false when the range does not contain the specified symbol', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'code.ts'),
      ['const x = 1;', 'function doSomething() {', '  return x + 1;', '}', 'const y = 2;'].join(
        '\n',
      ),
    );

    expect(verifyRange('code.ts', 1, 1, 'doSomething', tmpDir)).toBe(false);
  });

  it('returns true when no symbol is specified and range exists', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'code.ts'),
      ['line one', 'line two', 'line three'].join('\n'),
    );

    expect(verifyRange('code.ts', 1, 3, undefined, tmpDir)).toBe(true);
  });

  it('returns false for a nonexistent file', () => {
    expect(verifyRange('missing.ts', 1, 5, 'anything', tmpDir)).toBe(false);
  });

  it('returns true when symbol appears anywhere in the range', () => {
    fs.writeFileSync(
      path.join(tmpDir, 'multi.ts'),
      [
        '// header comment',
        '// more comments',
        'export function targetSymbol() {',
        '  return 42;',
        '}',
      ].join('\n'),
    );

    expect(verifyRange('multi.ts', 1, 5, 'targetSymbol', tmpDir)).toBe(true);
  });
});
