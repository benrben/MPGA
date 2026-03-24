# MPGA CLI

Evidence-backed context engineering for AI-assisted development. MPGA scans your codebase, generates scope documents with verifiable evidence links, detects drift, and exports context for multiple AI tools.

## Installation

```bash
cd mpga-plugin/cli
npm install
```

Requires Node.js >= 20.

## Usage

```bash
npx mpga <command>
```

### Commands

| Command     | Description                                      |
| ----------- | ------------------------------------------------ |
| `init`      | Initialize MPGA in a project                     |
| `scan`      | Scan codebase and collect file metadata           |
| `sync`      | Synchronize scope documents with codebase state   |
| `graph`     | Generate dependency graph between scopes          |
| `scope`     | View or manage scope documents                    |
| `board`     | View and manage the task board                    |
| `evidence`  | Query and validate evidence links                 |
| `drift`     | Detect stale evidence and outdated context        |
| `milestone` | Manage project milestones                         |
| `session`   | Manage conversation-scoped sessions               |
| `health`    | Run project health checks                         |
| `status`    | Show project status dashboard                     |
| `config`    | View or update MPGA configuration                 |
| `export`    | Export context for AI tools (Claude, Cursor, etc) |

### Examples

```bash
# Initialize MPGA in your project
npx mpga init

# Scan and sync everything
npx mpga scan && npx mpga sync

# Generate graph and scope docs
npx mpga graph && npx mpga scope

# Export for Claude
npx mpga export --claude

# Check project health
npx mpga health
```

## Development

```bash
# Watch mode (recompile on change)
npm run dev

# Run tests
npm run test

# Full check (typecheck + lint + test)
npm run check
```

## License

MIT
