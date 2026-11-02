#!/usr/bin/env bash
# Installs PBS Space Time Companion desktop entry on Ubuntu / Linux desktops
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_FILE="$SCRIPT_DIR/spacetimeplayer.desktop"

# Pre-generate transparent PNG logo if python is available
if command -v python3 >/dev/null 2>&1; then
    python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); from app import ensure_transparent_logo; ensure_transparent_logo()" 2>/dev/null || true
elif command -v python >/dev/null 2>&1; then
    python -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); from app import ensure_transparent_logo; ensure_transparent_logo()" 2>/dev/null || true
fi

cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Type=Application
Name=PBS Space Time Companion
Comment=Watch, organize, and track PBS Space Time episodes
Exec="$SCRIPT_DIR/start.sh"
Path=$SCRIPT_DIR
Icon=$SCRIPT_DIR/static/pbsspacetime-logo.png
Terminal=true
Categories=AudioVideo;Player;Education;Science;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE" 2>/dev/null || true
chmod +x "$SCRIPT_DIR/start.sh" 2>/dev/null || true

# Install to user applications menu (~/.local/share/applications) so it shows up in Ubuntu Dash / search
APP_DIR="$HOME/.local/share/applications"
mkdir -p "$APP_DIR"
cp "$DESKTOP_FILE" "$APP_DIR/"

# Also install to desktop folder if present
if [ -d "$HOME/Desktop" ]; then
    cp "$DESKTOP_FILE" "$HOME/Desktop/"
    chmod +x "$HOME/Desktop/spacetimeplayer.desktop" 2>/dev/null || true
    gio set "$HOME/Desktop/spacetimeplayer.desktop" metadata::trusted true 2>/dev/null || true
elif [ -d "$HOME/Schreibtisch" ]; then
    cp "$DESKTOP_FILE" "$HOME/Schreibtisch/"
    chmod +x "$HOME/Schreibtisch/spacetimeplayer.desktop" 2>/dev/null || true
    gio set "$HOME/Schreibtisch/spacetimeplayer.desktop" metadata::trusted true 2>/dev/null || true
fi

echo "PBS Space Time Companion launcher installed!"
echo "- Application menu entry: $APP_DIR/spacetimeplayer.desktop"
echo "You can now launch 'PBS Space Time Companion' directly from Ubuntu's app launcher or dock."
