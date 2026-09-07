#!/usr/bin/env bash
set -e

echo "Installing passcheck..."

if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not found."
    exit 1
fi

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo ""
echo "Installation complete."
echo "Run with: $VENV_DIR/bin/python -m passcheck.main"
