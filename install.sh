#!/bin/bash
# ⚡ MacStress — Auto-installer
# Works on any Mac, no Python or Xcode needed beforehand
set -e

echo ""
echo "  ⚡  MacStress — Native macOS Stress Test & Monitor"
echo ""

# ── 1. Ensure python3 exists ──────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "  📦  Python 3 не знайдено. Встановлюю Xcode Command Line Tools..."
    xcode-select --install 2>/dev/null || true
    # Wait for installation to complete
    echo "  ⏳  Зачекайте завершення встановлення в діалозі macOS."
    echo "      Після цього запустіть команду ще раз."
    echo ""
    until command -v python3 &>/dev/null; do sleep 5; done
    echo "  ✅  Python 3 встановлено!"
fi

# ── 2. Install PyObjC (for native menu bar + WebView) ─────
echo "  📦  Перевірка залежностей..."
python3 -c "import objc; from AppKit import NSApplication; import WebKit" 2>/dev/null || {
    echo "  📦  Встановлюю PyObjC..."
    python3 -m pip install --quiet --break-system-packages \
        pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null || \
    python3 -m pip install --quiet \
        pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null
    echo "  ✅  PyObjC встановлено!"
}

# ── 3. Download latest MacStress ──────────────────────────
DEST="$HOME/.local/bin/macstress.py"
mkdir -p "$(dirname "$DEST")"
echo "  📥  Завантажую MacStress..."
curl -fsSL https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/macstress.py -o "$DEST"

# ── 4. Launch ─────────────────────────────────────────────
echo "  🚀  Запускаю MacStress..."
echo ""
exec python3 "$DEST"
