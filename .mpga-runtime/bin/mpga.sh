#!/usr/bin/env bash
# MPGA CLI wrapper — auto-installs and builds the CLI if needed, then runs it.
# Usage: mpga.sh <command> [args...]

set -e

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_BIN="$PLUGIN_ROOT/cli/dist/index.js"
SETUP_SCRIPT="$PLUGIN_ROOT/scripts/setup.sh"

# Auto-setup if CLI not built
if [ ! -f "$CLI_BIN" ]; then
  bash "$SETUP_SCRIPT"
fi

exec node "$CLI_BIN" "$@"
