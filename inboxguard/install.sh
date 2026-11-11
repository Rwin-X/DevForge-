#!/usr/bin/env bash
# InboxGuard installer: creates a private virtualenv, a launcher and a desktop entry.
set -euo pipefail

APP="inboxguard"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${XDG_DATA_HOME:-$HOME/.local/share}/$APP"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required but was not found." >&2
    exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "Python 3.10 or newer is required (found $(python3 --version))." >&2
    exit 1
fi
if ! python3 -c 'import venv, ensurepip' >/dev/null 2>&1; then
    echo "The venv module is missing. Install it first:" >&2
    echo "  Debian / Ubuntu : sudo apt install python3-venv" >&2
    echo "  Fedora          : sudo dnf install python3" >&2
    echo "  Arch            : sudo pacman -S python" >&2
    exit 1
fi

# Qt's xcb platform plugin needs libxcb-cursor0 on recent Qt versions.
if [ "$(uname -s)" = "Linux" ] && ! ldconfig -p 2>/dev/null | grep -q "libxcb-cursor"; then
    echo "Warning: libxcb-cursor was not found; the window may fail to start on X11." >&2
    echo "  Debian / Ubuntu : sudo apt install libxcb-cursor0" >&2
    echo "  Fedora          : sudo dnf install xcb-util-cursor" >&2
    echo "  Arch            : sudo pacman -S xcb-util-cursor" >&2
fi

echo "Creating virtual environment in $PREFIX/venv"
mkdir -p "$PREFIX" "$BIN_DIR" "$DESKTOP_DIR"
python3 -m venv "$PREFIX/venv"
"$PREFIX/venv/bin/pip" install --quiet --upgrade pip
"$PREFIX/venv/bin/pip" install --quiet "$SRC_DIR"

cat > "$BIN_DIR/$APP" <<EOF_LAUNCHER
#!/usr/bin/env bash
exec "$PREFIX/venv/bin/inboxguard" "\$@"
EOF_LAUNCHER
chmod +x "$BIN_DIR/$APP"

sed "s|__LAUNCHER__|$BIN_DIR/$APP|" "$SRC_DIR/packaging/$APP.desktop" > "$DESKTOP_DIR/$APP.desktop"

echo
echo "Installed. Start it with:  $APP"
echo "Headless mode:             $APP --headless"
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "Note: add $BIN_DIR to your PATH to use the '$APP' command." ;;
esac
