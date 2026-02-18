#!/bin/bash
# Build MacStress.app — double-click to launch from Finder (no terminal)
set -e

APP_NAME="MacStress"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR/$APP_NAME.app"
CONTENTS="$APP_DIR/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

echo "⚡ Building $APP_NAME.app..."

# Clean old build
rm -rf "$APP_DIR"

# Create bundle structure
mkdir -p "$MACOS" "$RESOURCES"

# -- Info.plist --
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
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
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

# -- Launcher script (fast startup — caches dependency check) --
cat > "$MACOS/launcher" << 'LAUNCHER'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")/../Resources" && pwd)"

# Find Python 3
PYTHON="$(which python3 2>/dev/null || echo /usr/bin/python3)"

# Quick check: skip pip install if already verified
STAMP="$HOME/.cache/macstress/deps_ok"
if [ ! -f "$STAMP" ]; then
    "$PYTHON" -c "import objc; from AppKit import NSApplication; import WebKit" 2>/dev/null || {
        "$PYTHON" -m pip install --quiet pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null
    }
    mkdir -p "$(dirname "$STAMP")" && touch "$STAMP"
fi

exec "$PYTHON" "$SCRIPT_DIR/macstress.py"
LAUNCHER
chmod +x "$MACOS/launcher"

# -- Copy main script --
cp "$SCRIPT_DIR/macstress.py" "$RESOURCES/macstress.py"

# -- Generate app icon from emoji if no icon exists --
if [ -f "$SCRIPT_DIR/icon.icns" ]; then
    cp "$SCRIPT_DIR/icon.icns" "$RESOURCES/AppIcon.icns"
else
    # Generate a simple icon using system tools
    ICON_DIR=$(mktemp -d)
    ICONSET="$ICON_DIR/AppIcon.iconset"
    mkdir -p "$ICONSET"

    # Create icon with sips from a generated PNG
    python3 -c "
import subprocess, tempfile, os
# Use AppKit to render an icon
try:
    from AppKit import NSImage, NSBitmapImageRep, NSPNGFileType, NSGraphicsContext, NSColor, NSFont, NSString, NSMakeRect, NSFontAttributeName, NSForegroundColorAttributeName
    from Foundation import NSDictionary, NSMakePoint
    for size in [16, 32, 64, 128, 256, 512, 1024]:
        img = NSImage.alloc().initWithSize_((size, size))
        img.lockFocus()
        # Dark background
        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.08, 0.09, 0.12, 1.0).set()
        from AppKit import NSBezierPath
        NSBezierPath.fillRect_(NSMakeRect(0, 0, size, size))
        # Lightning bolt emoji
        attrs = {NSFontAttributeName: NSFont.systemFontOfSize_(size * 0.65), NSForegroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_(1.0, 0.6, 0.0, 1.0)}
        s = NSString.stringWithString_('⚡')
        text_size = s.sizeWithAttributes_(attrs)
        x = (size - text_size.width) / 2
        y = (size - text_size.height) / 2
        s.drawAtPoint_withAttributes_(NSMakePoint(x, y), attrs)
        img.unlockFocus()
        rep = NSBitmapImageRep.alloc().initWithData_(img.TIFFRepresentation())
        png = rep.representationUsingType_properties_(NSPNGFileType, None)
        fname = f'icon_{size}x{size}.png'
        png.writeToFile_atomically_('$ICONSET/' + fname, True)
        if size <= 512:
            fname2 = f'icon_{size}x{size}@2x.png'  # @2x for retina
except Exception as e:
    print(f'Icon generation skipped: {e}')
" 2>/dev/null

    # Convert iconset to icns
    if [ -d "$ICONSET" ] && [ "$(ls -1 "$ICONSET" | wc -l)" -gt 0 ]; then
        iconutil -c icns "$ICONSET" -o "$RESOURCES/AppIcon.icns" 2>/dev/null || true
    fi
    rm -rf "$ICON_DIR"
fi

echo ""
echo "✅ $APP_NAME.app created!"
echo "   📂 $APP_DIR"
echo ""
echo "   Double-click to launch from Finder"
echo "   Or: open '$APP_DIR'"
echo ""
