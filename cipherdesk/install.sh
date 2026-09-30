#!/usr/bin/env bash
set -euo pipefail

# Cipherdesk installer - creates a virtual environment and installs
# dependencies. Run this once, then use run.sh (or the launcher your
# platform prefers) to start the app.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "Cipherdesk — installer"
echo "======================="

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r "$SCRIPT_DIR/requirements.txt" --quiet

echo
echo "Done. Start the app with:"
echo "  ./run.sh"
