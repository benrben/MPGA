#!/usr/bin/env bash
# ┌─────────────────────────────────────────────────────┐
# │  MPGA Installer — Make Project Great Again          │
# │  Sets up the CLI + optional Trump voice (spoke)     │
# └─────────────────────────────────────────────────────┘
#
# Usage:
#   curl -sL <url>/install.sh | bash        (or just: bash install.sh)
#   bash install.sh --with-spoke            (also set up TTS voice)
#   bash install.sh --uninstall             (remove symlink)

set -e

# ── Config ────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$REPO_ROOT/mpga-plugin"
CLI_DIR="$PLUGIN_ROOT/cli"
SPOKE_DIR="$PLUGIN_ROOT/spoke"
VENV_DIR="$CLI_DIR/.venv"
CLI_BIN="$VENV_DIR/bin/mpga"
INSTALL_TARGET="/usr/local/bin/mpga"
MIN_PYTHON="3.11"

RED='\033[0;31m'
GREEN='\033[0;32m'
DIM='\033[0;90m'
BOLD='\033[1m'
NC='\033[0m'

WITH_SPOKE=false
UNINSTALL=false

for arg in "$@"; do
  case "$arg" in
    --with-spoke) WITH_SPOKE=true ;;
    --uninstall)  UNINSTALL=true ;;
    --help|-h)
      echo "Usage: bash install.sh [--with-spoke] [--uninstall]"
      echo ""
      echo "  --with-spoke   Also install Trump voice TTS (requires ~500MB)"
      echo "  --uninstall    Remove mpga from PATH"
      exit 0
      ;;
  esac
done

# ── Uninstall ─────────────────────────────────────────
if $UNINSTALL; then
  if [ -L "$INSTALL_TARGET" ]; then
    rm "$INSTALL_TARGET"
    echo -e "${GREEN}✓${NC} Removed $INSTALL_TARGET"
  else
    echo -e "${DIM}Nothing to remove — $INSTALL_TARGET not found${NC}"
  fi
  exit 0
fi

# ── Banner ────────────────────────────────────────────
echo ""
echo -e "${RED}  ▄▄███████████▄▄${NC}"
echo -e "${RED}  ██${BOLD} MPGA INSTALLER ${NC}${RED}██${NC}"
echo -e "${RED}  ▀▀███████████▀▀${NC}"
echo ""

# ── Check Python ──────────────────────────────────────
echo -e "${DIM}Checking Python...${NC}"

if ! command -v python3 &>/dev/null; then
  echo -e "${RED}✗${NC} Python 3 not found. Install Python >= $MIN_PYTHON first."
  exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
MIN_MAJOR=$(echo "$MIN_PYTHON" | cut -d. -f1)
MIN_MINOR=$(echo "$MIN_PYTHON" | cut -d. -f2)

if [ "$PY_MAJOR" -lt "$MIN_MAJOR" ] || { [ "$PY_MAJOR" -eq "$MIN_MAJOR" ] && [ "$PY_MINOR" -lt "$MIN_MINOR" ]; }; then
  echo -e "${RED}✗${NC} Python $PY_VERSION found, but >= $MIN_PYTHON required."
  exit 1
fi

echo -e "${GREEN}✓${NC} Python $PY_VERSION"

# ── Create venv + install ─────────────────────────────
if [ ! -f "$CLI_BIN" ] || [ "$CLI_DIR/pyproject.toml" -nt "$CLI_BIN" ]; then
  echo -e "${DIM}Creating virtual environment...${NC}"
  python3 -m venv "$VENV_DIR"

  echo -e "${DIM}Installing MPGA CLI...${NC}"
  "$VENV_DIR/bin/pip" install -e "$CLI_DIR[dev]" --quiet 2>&1 | tail -1

  echo -e "${GREEN}✓${NC} CLI installed"
else
  echo -e "${GREEN}✓${NC} CLI already up to date"
fi

# ── Verify CLI works ──────────────────────────────────
CLI_VERSION=$("$CLI_BIN" --version 2>/dev/null || echo "FAIL")
if [ "$CLI_VERSION" = "FAIL" ]; then
  echo -e "${RED}✗${NC} CLI failed to start. Check $VENV_DIR for issues."
  exit 1
fi
echo -e "${GREEN}✓${NC} mpga v$CLI_VERSION"

# ── Symlink to PATH ──────────────────────────────────
echo ""

_try_link() {
  local target="$1"
  local dir="$(dirname "$target")"
  if [ -L "$target" ] || [ -f "$target" ]; then
    EXISTING=$(readlink "$target" 2>/dev/null || echo "$target")
    if [ "$EXISTING" = "$CLI_BIN" ]; then
      echo -e "${GREEN}✓${NC} Already on PATH: ${BOLD}mpga${NC} ($target)"
      return 0
    fi
  fi
  if mkdir -p "$dir" 2>/dev/null && ln -sf "$CLI_BIN" "$target" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Linked: ${BOLD}mpga${NC} -> $target"
    return 0
  fi
  return 1
}

LINKED=false

# Try /usr/local/bin first (system-wide)
if _try_link "$INSTALL_TARGET"; then
  LINKED=true
fi

# Fallback: ~/.local/bin (user-local, no sudo)
if ! $LINKED; then
  LOCAL_BIN="$HOME/.local/bin"
  if _try_link "$LOCAL_BIN/mpga"; then
    LINKED=true
    # Ensure ~/.local/bin is on PATH
    if ! echo "$PATH" | tr ':' '\n' | grep -qx "$LOCAL_BIN"; then
      SHELL_RC=""
      if [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
      elif [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
      elif [ -f "$HOME/.bash_profile" ]; then
        SHELL_RC="$HOME/.bash_profile"
      fi

      if [ -n "$SHELL_RC" ]; then
        if ! grep -q '\.local/bin' "$SHELL_RC" 2>/dev/null; then
          echo '' >> "$SHELL_RC"
          echo '# MPGA CLI' >> "$SHELL_RC"
          echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
          echo -e "${GREEN}✓${NC} Added ~/.local/bin to PATH in $(basename "$SHELL_RC")"
          echo -e "${BOLD}  Run: source $SHELL_RC${NC}  (or open a new terminal)"
        fi
      fi
    fi
  fi
fi

if ! $LINKED; then
  echo -e "${RED}!${NC} Could not link mpga to PATH."
  echo -e "${DIM}  Try: sudo ln -sf $CLI_BIN $INSTALL_TARGET${NC}"
fi

# ── Spoke (optional TTS) ─────────────────────────────
if $WITH_SPOKE; then
  echo ""
  echo -e "${BOLD}Setting up Trump voice TTS...${NC}"
  if [ -f "$SPOKE_DIR/setup.sh" ]; then
    bash "$SPOKE_DIR/setup.sh"
    echo -e "${GREEN}✓${NC} Spoke TTS ready — run: ${BOLD}mpga spoke \"Hello America\"${NC}"
  else
    echo -e "${RED}✗${NC} Spoke setup script not found at $SPOKE_DIR/setup.sh"
  fi
else
  echo ""
  echo -e "${DIM}Tip: Run with --with-spoke to install Trump voice TTS${NC}"
fi

# ── Done ──────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}MPGA is installed — your projects are about to be GREAT AGAIN!${NC}"
echo ""
echo -e "  ${BOLD}Quick start:${NC}"
echo -e "    cd your-project"
echo -e "    mpga init --from-existing"
echo -e "    mpga sync"
echo -e "    mpga status"
echo ""
echo -e "  ${BOLD}All commands:${NC}  mpga --help"
echo -e "  ${BOLD}Uninstall:${NC}     bash $REPO_ROOT/install.sh --uninstall"
echo ""
