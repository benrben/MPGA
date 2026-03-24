#!/usr/bin/env bash
# Installs and builds the MPGA CLI from source bundled inside the plugin.
# Safe to run multiple times — skips if already built.

set -e

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI_DIR="$PLUGIN_ROOT/cli"
CLI_BIN="$CLI_DIR/dist/index.js"

if [ ! -d "$CLI_DIR" ]; then
  echo "✗ CLI source not found at $CLI_DIR" >&2
  exit 1
fi

# Skip if already built and up to date
if [ -f "$CLI_BIN" ] && [ "$CLI_DIR/dist" -nt "$CLI_DIR/src" ] 2>/dev/null; then
  exit 0
fi

echo "⚙ MPGA: Installing CLI dependencies..."
(cd "$CLI_DIR" && npm install --silent)

echo "⚙ MPGA: Building CLI..."
(cd "$CLI_DIR" && npm run build --silent)

echo "✓ MPGA CLI ready at $CLI_BIN"
