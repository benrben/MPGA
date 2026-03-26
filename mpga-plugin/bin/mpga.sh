#!/usr/bin/env bash
# MPGA CLI wrapper — auto-installs and builds the CLI if needed, then runs it.
# Usage: mpga.sh <command> [args...]

set -e

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_DIR="$PLUGIN_ROOT/cli"
CLI_BIN="$CLI_DIR/.venv/bin/mpga"
SETUP_SCRIPT="$PLUGIN_ROOT/scripts/setup.sh"

# Auto-setup if venv not created
if [ ! -f "$CLI_BIN" ]; then
  bash "$SETUP_SCRIPT"
fi

exec "$CLI_BIN" "$@"
