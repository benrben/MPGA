# Dependency graph

## Module dependencies

mpga-plugin → core
mpga-plugin → commands
board → core
commands → core
commands → board
commands → evidence
commands → generators
generators → core

## Circular dependencies
(none detected)

## Orphan modules
- mpga-plugin/bin/mpga.sh
- mpga-plugin/cli/vitest.config.ts
- mpga-plugin/scripts/check-cli.sh
- mpga-plugin/scripts/format-evidence.sh
- mpga-plugin/scripts/setup.sh
- mpga-plugin/cli/bin/mpga.js
- mpga-plugin/cli/src/cli.ts
- mpga-plugin/cli/src/index.ts
- mpga-plugin/cli/src/board/board-md.ts
- mpga-plugin/cli/src/board/task.test.ts

## Mermaid export
```mermaid
graph TD
    mpga_plugin --> core
    mpga_plugin --> commands
    board --> core
    commands --> core
    commands --> board
    commands --> evidence
    commands --> generators
    generators --> core
```
