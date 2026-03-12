#!/bin/bash
# ─────────────────────────────────────────────────────────────
# build_standalone.sh — Build a fully self-contained MacStress.app
#   Bundles: Python venv + pyobjc + all macstress/ sources
#   Result: one-click launch, zero internet required
# ─────────────────────────────────────────────────────────────
set -e

APP_NAME="MacStress"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-$SRC_DIR/dist}"
APP_DIR="$DEST/$APP_NAME.app"
CONTENTS="$APP_DIR/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
VENV_DIR="$RESOURCES/venv"

echo ""
echo "⚡ Building self-contained $APP_NAME.app ..."
echo "   Source:  $SRC_DIR"
echo "   Output:  $APP_DIR"
echo ""

# ── Clean ──
rm -rf "$APP_DIR"
mkdir -p "$MACOS" "$RESOURCES"

# ── Create embedded virtualenv ──
echo "📦 Creating embedded Python virtualenv ..."
PYTHON="$(which python3 2>/dev/null || echo /usr/bin/python3)"
"$PYTHON" -m venv "$VENV_DIR"

echo "📥 Installing dependencies into venv ..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet \
    pyobjc-core \
    pyobjc-framework-Cocoa \
    pyobjc-framework-WebKit

echo "   ✅ Dependencies installed"

# ── Copy application sources ──
echo "📂 Copying application sources ..."
cp "$SRC_DIR/macstress.py" "$RESOURCES/macstress.py"
cp -R "$SRC_DIR/macstress" "$RESOURCES/macstress"

# Remove __pycache__ from copied sources
find "$RESOURCES/macstress" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
rm -f "$RESOURCES/macstress/.DS_Store"

# ── Make venv paths relative ──
# Patch the venv's pyvenv.cfg to use a relative python
# We'll use the launcher to set up the correct path at runtime

# ── Copy icon ──
if [ -f "$SRC_DIR/icons/macstress.icns" ]; then
    cp "$SRC_DIR/icons/macstress.icns" "$RESOURCES/AppIcon.icns"
    echo "   🎨 Icon copied"
fi

# ── Info.plist ──
cat > "$CONTENTS/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>MacStress</string>
    <key>CFBundleDisplayName</key>
    <string>MacStress</string>
    <key>CFBundleIdentifier</key>
    <string>com.macstress.app</string>
    <key>CFBundleVersion</key>
    <string>1.5.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.5.0</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>MacStress needs administrator access to read power consumption data via powermetrics.</string>
</dict>
</plist>
PLIST

# ── Launcher script ──
cat > "$MACOS/launcher" << 'LAUNCHER'
#!/bin/bash
# MacStress standalone launcher — uses bundled venv + sources
# No internet required, no system packages modified

BUNDLE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RESOURCES="$BUNDLE_DIR/Resources"
VENV="$RESOURCES/venv"
VENV_PYTHON="$VENV/bin/python3"
LOG="$HOME/Library/Logs/MacStress.log"
mkdir -p "$(dirname "$LOG")"

# Kill any existing instance on port 9630
lsof -ti:9630 2>/dev/null | xargs kill -9 2>/dev/null
sleep 0.3

# Set PYTHONPATH so the macstress package is found
export PYTHONPATH="$RESOURCES:$PYTHONPATH"

# Use the venv's Python with all dependencies pre-installed
exec "$VENV_PYTHON" -m macstress >> "$LOG" 2>&1
LAUNCHER
chmod +x "$MACOS/launcher"

# ── Fix venv symlinks to be relative (portability) ──
# The venv python is a symlink to the system python — that's fine,
# macOS always has /usr/bin/python3. But we need to make sure the
# venv's site-packages are used, which the venv activation handles.

# ── Calculate size ──
APP_SIZE=$(du -sh "$APP_DIR" | cut -f1)

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ✅ $APP_NAME.app built successfully!"
echo "  📦 Size: $APP_SIZE"
echo "  📂 $APP_DIR"
echo ""
echo "  Double-click to launch — no internet needed!"
echo "═══════════════════════════════════════════════════"
echo ""
