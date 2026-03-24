# Scope: bin

## Summary

The **bin** scope contains the single CLI entry-point script that is registered as the `mpga` executable. When a user runs `mpga` from the terminal, Node executes `bin/mpga.js`, which immediately delegates to the compiled application bundle at `dist/index.js` [E] `bin/mpga.js:3`. The package.json `bin` field maps the command name `mpga` to this file [E] `package.json:28-29`.

## Where to start in code

- [E] `bin/mpga.js` — the sole file in this scope; a 3-line shim (shebang + strict mode + require)

## Context / stack / skills

- **Languages:** JavaScript (CommonJS)
- **Frameworks:** None. This file has zero dependencies of its own; it relies on Node.js `require()` to load the pre-built TypeScript output.

## Who and what triggers it

- **End users** invoking `mpga` on the command line after a global or local npm install [E] `package.json:28-29`.
- **npm scripts** such as `postbuild` that call `node mpga-plugin/cli/dist/index.js` bypass this shim and invoke the dist bundle directly [E] `package.json:38`.

## What happens

1. The OS reads the shebang `#!/usr/bin/env node` and launches the script under Node.js [E] `bin/mpga.js:1`.
2. Strict mode is enabled [E] `bin/mpga.js:2`.
3. `require('../dist/index.js')` loads the compiled CLI bundle, which calls `createCli().parse(process.argv)` to hand off to Commander [E] `bin/mpga.js:3`, `src/index.ts:1-4`.

There is no additional logic, argument parsing, or error handling in this file. All behavior is delegated to `dist/index.js`.

## Rules and edge cases

- The script assumes `dist/index.js` exists. If the project has not been built (`npm run build`), the `require` call will throw a `MODULE_NOT_FOUND` error at runtime.
- The shebang (`#!/usr/bin/env node`) requires Node.js to be on the user's `PATH`.
- The `engines` field in `package.json` requires Node >= 20 [E] `package.json:72`.

## Concrete examples

- **Normal invocation:** `npx mpga sync` causes npm to resolve `bin/mpga.js`, Node loads it, `dist/index.js` is required, and Commander parses `["node", "mpga", "sync"]`.
- **Missing build:** Running `mpga` without a prior `npm run build` produces `Error: Cannot find module '../dist/index.js'`.

## UI

N/A — this is a CLI bootstrap shim with no user-facing interface of its own.

## Navigation

**Sibling scopes:**

- [root](./root.md)
- [src](./src.md)
- [board](./board.md)
- [commands](./commands.md)
- [core](./core.md)
- [generators](./generators.md)
- [evidence](./evidence.md)

**Parent:** [INDEX.md](../INDEX.md)

## Relationships

- **Depends on [src](./src.md):** `bin/mpga.js` requires the compiled output of `src/index.ts` via `dist/index.js` [E] `bin/mpga.js:3`, `src/index.ts:1-4`.
- No other scope depends on `bin` directly; it is the outermost shell entry point.

## Diagram

```
┌──────────────┐      require()      ┌───────────────┐     createCli()    ┌────────────┐
│  Terminal     │ ──────────────────► │ bin/mpga.js   │ ─────────────────► │ dist/      │
│  $ mpga …    │   (shebang → node)  │ (3-line shim) │                    │ index.js   │
└──────────────┘                     └───────────────┘                    └────────────┘
```

## Traces

| Step | Layer | What happens | Evidence |
|------|-------|-------------|----------|
| 1 | OS / npm | User runs `mpga`; npm resolves `bin/mpga.js` via the `bin` field | [E] `package.json:28-29` |
| 2 | Node | Shebang `#!/usr/bin/env node` launches Node.js | [E] `bin/mpga.js:1` |
| 3 | Node | `'use strict'` enables strict mode | [E] `bin/mpga.js:2` |
| 4 | Application | `require('../dist/index.js')` loads the compiled CLI | [E] `bin/mpga.js:3` |
| 5 | Application | `createCli().parse(process.argv)` boots Commander | [E] `src/index.ts:3-4` |

## Evidence index

| Tag | File | Line(s) | Description |
|-----|------|---------|-------------|
| [E] | `bin/mpga.js` | 1 | Shebang line `#!/usr/bin/env node` |
| [E] | `bin/mpga.js` | 2 | Strict mode declaration |
| [E] | `bin/mpga.js` | 3 | `require('../dist/index.js')` — loads compiled bundle |
| [E] | `package.json` | 28-29 | `"bin": { "mpga": "./bin/mpga.js" }` |
| [E] | `package.json` | 38 | `postbuild` script invokes dist directly |
| [E] | `package.json` | 72 | `"engines": { "node": ">=20" }` |
| [E] | `src/index.ts` | 1-4 | `createCli().parse(process.argv)` — CLI bootstrap |

## Files

- `bin/mpga.js` (4 lines, javascript)

## Deeper splits

Not applicable. This scope contains a single 4-line file with no internal complexity warranting further decomposition.

## Confidence and notes

- **Confidence:** HIGH — the file is trivial and fully understood.
- **Evidence coverage:** 7/7 verified
- **Last verified:** 2026-03-24
- **Drift risk:** Very low. This file changes only if the compiled entry point path changes.

## Change history

- 2026-03-24: Initial scope generation via `mpga sync`
- 2026-03-24: Evidence-backed content added by scout agent
