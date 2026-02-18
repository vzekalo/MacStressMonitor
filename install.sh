#!/bin/bash
# ⚡ MacStress — Auto-installer
# Works on any Mac, even without Python or Xcode

echo ""
echo "  ⚡  MacStress — Native macOS Stress Test & Monitor"
echo ""

# ── 1. Check if python3 ACTUALLY works (not just the macOS stub) ──
if ! python3 --version &>/dev/null; then
    echo "  📦  Python 3 не знайдено або потребує Xcode Command Line Tools."
    echo ""
    echo "  ⏳  Встановлюю Command Line Tools..."
    xcode-select --install 2>/dev/null
    echo ""
    echo "  👉  Натисніть 'Install' в діалозі macOS."
    echo "  👉  Після завершення (2-5 хв) запустіть ЦЮ САМУ команду ще раз:"
    echo ""
    echo "      bash <(curl -fsSL https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/install.sh)"
    echo ""
    exit 0
fi

echo "  ✅  Python 3: $(python3 --version 2>&1)"

# ── 2. Ensure pip works ──────────────────────────────────
if ! python3 -m pip --version &>/dev/null; then
    echo "  📦  Встановлюю pip..."
    python3 -m ensurepip --upgrade 2>/dev/null || {
        curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
        python3 /tmp/get-pip.py --user 2>/dev/null
    }
fi

# ── 3. Install PyObjC (for native menu bar + WebView) ─────
if ! python3 -c "import objc; from AppKit import NSApplication; import WebKit" 2>/dev/null; then
    echo "  📦  Встановлюю PyObjC..."
    python3 -m pip install --user --quiet pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null \
    || python3 -m pip install --quiet --break-system-packages pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null \
    || python3 -m pip install --quiet pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null \
    || {
        echo ""
        echo "  ❌  Не вдалось встановити PyObjC auto."
        echo "  💡  Спробуйте вручну:"
        echo "      python3 -m pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit"
        echo ""
        exit 1
    }
    echo "  ✅  PyObjC встановлено!"
else
    echo "  ✅  PyObjC: вже встановлено"
fi

# ── 4. Download latest MacStress ──────────────────────────
DEST="$HOME/.local/bin/macstress.py"
mkdir -p "$(dirname "$DEST")"
echo "  📥  Завантажую MacStress..."
curl -fsSL https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/macstress.py -o "$DEST"

if [ ! -f "$DEST" ]; then
    echo "  ❌  Не вдалось завантажити. Перевірте інтернет."
    exit 1
fi

# ── 5. Launch ─────────────────────────────────────────────
echo ""
echo "  🚀  Запускаю MacStress..."
echo "      Dashboard: http://localhost:9630"
echo ""
exec python3 "$DEST"
