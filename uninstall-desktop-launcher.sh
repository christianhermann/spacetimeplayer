#!/usr/bin/env bash
# Uninstalls PBS Space Time Companion desktop entry from Ubuntu / Linux desktops
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ENTRY="$HOME/.local/share/applications/spacetimeplayer.desktop"
DESKTOP_EN="$HOME/Desktop/spacetimeplayer.desktop"
DESKTOP_DE="$HOME/Schreibtisch/spacetimeplayer.desktop"
LOCAL_ENTRY="$SCRIPT_DIR/spacetimeplayer.desktop"

REMOVED=0

# Remove application menu entry
if [ -f "$APP_ENTRY" ]; then
    rm -f "$APP_ENTRY"
    echo "- Removed: $APP_ENTRY"
    REMOVED=1
fi

# Remove desktop shortcuts
if [ -f "$DESKTOP_EN" ]; then
    rm -f "$DESKTOP_EN"
    echo "- Removed: $DESKTOP_EN"
    REMOVED=1
fi

if [ -f "$DESKTOP_DE" ]; then
    rm -f "$DESKTOP_DE"
    echo "- Removed: $DESKTOP_DE"
    REMOVED=1
fi

# Remove locally generated .desktop file
if [ -f "$LOCAL_ENTRY" ]; then
    rm -f "$LOCAL_ENTRY"
    echo "- Removed: $LOCAL_ENTRY"
    REMOVED=1
fi

# Refresh desktop database if tool is installed
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

if [ "$REMOVED" -eq 1 ]; then
    echo "PBS Space Time Companion desktop shortcuts successfully uninstalled."
else
    echo "No desktop shortcuts were found to remove."
fi
