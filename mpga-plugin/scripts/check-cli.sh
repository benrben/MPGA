#!/usr/bin/env bash
# Ensures the MPGA CLI is available, auto-installing from the plugin's bundled
# source if not already built. Called by hooks before running drift checks.

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_BIN="$PLUGIN_ROOT/cli/.venv/bin/mpga"

if [ ! -f "$CLI_BIN" ]; then
  bash "$PLUGIN_ROOT/scripts/setup.sh" >&2
fi

# Export a shell function so callers can use `mpga` as a command name
mpga() {
  "$CLI_BIN" "$@"
}
export -f mpga 2>/dev/null || true  # export -f not available in all shells

# Also expose as an alias path check passes
export MPGA_BIN="$CLI_BIN"
