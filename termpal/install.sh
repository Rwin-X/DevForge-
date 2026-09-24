#!/usr/bin/env bash
#
# TERMPAL install script.
# Creates an isolated virtual environment, installs the package into
# it, and drops a thin launcher script on the user's PATH so `termpal`
# works from any directory afterward.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${REPO_DIR}/.venv"
LAUNCHER_DIR="${HOME}/.local/bin"
LAUNCHER_PATH="${LAUNCHER_DIR}/termpal"

echo "== TERMPAL installer =="

# --- check for Python 3.10+ -------------------------------------------------

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 was not found on PATH." >&2
    echo "Install it first:" >&2
    echo "  Debian/Ubuntu : sudo apt install python3 python3-venv" >&2
    echo "  Fedora        : sudo dnf install python3" >&2
    echo "  Arch          : sudo pacman -S python" >&2
    exit 1
fi

PYTHON_VERSION="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
PYTHON_MAJOR="$(python3 -c 'import sys; print(sys.version_info[0])')"
PYTHON_MINOR="$(python3 -c 'import sys; print(sys.version_info[1])')"

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo "Error: TERMPAL requires Python 3.10+, found ${PYTHON_VERSION}." >&2
    exit 1
fi

echo "Found Python ${PYTHON_VERSION}."

# --- check that the venv module and curses are available -------------------

if ! python3 -c "import venv" >/dev/null 2>&1; then
    echo "Error: the 'venv' module is not available for this Python install." >&2
    echo "Install it first:" >&2
    echo "  Debian/Ubuntu : sudo apt install python3-venv" >&2
    echo "  Fedora        : sudo dnf install python3" >&2
    echo "  Arch          : sudo pacman -S python" >&2
    exit 1
fi

if ! python3 -c "import curses" >/dev/null 2>&1; then
    echo "Error: the 'curses' module is not available for this Python install." >&2
    echo "This is unusual on Linux/macOS - it ships with the standard library." >&2
    echo "On Debian/Ubuntu it can be provided separately:" >&2
    echo "  sudo apt install python3-dev" >&2
    exit 1
fi

# --- create the virtual environment -----------------------------------------

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at ${VENV_DIR}..."
    python3 -m venv "$VENV_DIR"
else
    echo "Reusing existing virtual environment at ${VENV_DIR}."
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "Installing TERMPAL..."
pip install --quiet --upgrade pip
pip install --quiet "${REPO_DIR}"

deactivate

# --- install the launcher ----------------------------------------------------

mkdir -p "$LAUNCHER_DIR"
cat > "$LAUNCHER_PATH" <<EOF
#!/usr/bin/env bash
exec "${VENV_DIR}/bin/termpal" "\$@"
EOF
chmod +x "$LAUNCHER_PATH"

echo ""
echo "TERMPAL installed."
echo "Launcher written to ${LAUNCHER_PATH}"

if ! command -v termpal >/dev/null 2>&1; then
    echo ""
    echo "NOTE: ${LAUNCHER_DIR} is not on your PATH yet. Add it with:"
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
    echo "  source ~/.bashrc"
fi

echo ""
echo "Run it with: termpal"
