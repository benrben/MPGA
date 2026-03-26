#!/usr/bin/env bash
# Installs the MPGA CLI into a Python venv bundled inside the plugin.
# Safe to run multiple times — skips if already installed.

set -e

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_DIR="$PLUGIN_ROOT/cli"
VENV_DIR="$CLI_DIR/.venv"
CLI_BIN="$VENV_DIR/bin/mpga"

if [ ! -d "$CLI_DIR" ]; then
  echo "✗ CLI source not found at $CLI_DIR" >&2
  exit 1
fi

# Skip if already installed and up to date
if [ -f "$CLI_BIN" ] && [ "$CLI_BIN" -nt "$CLI_DIR/pyproject.toml" ] 2>/dev/null; then
  exit 0
fi

echo "⚙ MPGA: Creating Python venv..."
python3 -m venv "$VENV_DIR"

echo "⚙ MPGA: Installing CLI package..."
"$VENV_DIR/bin/pip" install -e "$CLI_DIR[dev]" --quiet

echo "✓ MPGA CLI ready at $CLI_BIN"
