#!/bin/bash
# ⚡ MacStress — Auto-installer
# Works on any Mac, no Python or Xcode needed beforehand

echo ""
echo "  ⚡  MacStress — Native macOS Stress Test & Monitor"
echo ""

# ── 1. Ensure python3 exists ──────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "  📦  Python 3 не знайдено."
    echo "  📦  Встановлюю Xcode Command Line Tools..."
    echo ""
    xcode-select --install 2>/dev/null
    echo ""
    echo "  ⏳  Натищніть 'Install' в діалозі macOS і зачекайте."
    echo "  ⏳  Після завершення — запустіть цю команду ЩЕ РАЗ:"
    echo ""
    echo "      bash <(curl -fsSL https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/install.sh)"
    echo ""
    exit 0
fi

echo "  ✅  Python 3: $(python3 --version 2>&1)"

# ── 2. Install PyObjC (for native menu bar + WebView) ─────
if ! python3 -c "import objc; from AppKit import NSApplication; import WebKit" 2>/dev/null; then
    echo "  📦  Встановлюю PyObjC..."
    # Try multiple methods — different macOS versions need different flags
    python3 -m pip install --user --quiet pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null \
    || python3 -m pip install --quiet --break-system-packages pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null \
    || python3 -m pip install --quiet pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null \
    || {
        echo "  ❌  Не вдалось встановити PyObjC."
        echo "  💡  Спробуйте: python3 -m pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit"
        exit 1
    }
    echo "  ✅  PyObjC встановлено!"
else
    echo "  ✅  PyObjC: вже встановлено"
fi

# ── 3. Download latest MacStress ──────────────────────────
DEST="$HOME/.local/bin/macstress.py"
mkdir -p "$(dirname "$DEST")"
echo "  📥  Завантажую MacStress..."
curl -fsSL https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/macstress.py -o "$DEST"

if [ ! -f "$DEST" ]; then
    echo "  ❌  Не вдалось завантажити. Перевірте інтернет-з'єднання."
    exit 1
fi

echo "  ✅  Завантажено: $DEST"

# ── 4. Launch ─────────────────────────────────────────────
echo ""
echo "  🚀  Запускаю MacStress..."
echo "      Dashboard: http://localhost:9630"
echo ""
exec python3 "$DEST"
