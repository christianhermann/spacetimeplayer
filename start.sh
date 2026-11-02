#!/usr/bin/env bash
# PBS Space Time Companion — Launcher for Linux / Ubuntu
set -e

# Resolve script directory (even if invoked through a symlink)
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
cd "$SCRIPT_DIR"

# Set terminal window title
printf '\033]0;%s\007' "pbs_spacetime_player_terminal" 2>/dev/null || true

# Locate Python 3
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "Error: Python 3 not found in PATH." >&2
    echo "Install it with: sudo apt update && sudo apt install python3 python3-pip" >&2
    exit 1
fi

echo "=========================================="
echo "  PBS Space Time Companion (Linux/Ubuntu)"
echo "=========================================="
echo "Starting local companion server..."

exec "$PYTHON_BIN" app.py "$@"
