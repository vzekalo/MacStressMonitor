#!/bin/bash
# ⚡ MacStress — Auto-installer (zero-dependency)
# Works on ANY Mac — installs everything automatically

echo ""
echo "  ⚡  MacStress — Native macOS Stress Test & Monitor"
echo ""

# ── 1. Ensure REAL python3 (not macOS stub) ───────────────
PY_OK=0
python3 --version 2>/dev/null | grep -q "Python 3" && PY_OK=1

if [ "$PY_OK" -eq 0 ]; then
    echo "  📦  Потрібні Command Line Tools (включає Python 3)."
    echo "  📦  Встановлюю..."
    echo ""

    # Trigger CLT install dialog
    xcode-select --install 2>/dev/null

    echo "  ⏳  Натисніть 'Install' в діалозі macOS."
    echo "  ⏳  Чекаю завершення встановлення..."
    echo ""

    # Wait for CLT to finish installing (check every 10 seconds)
    while true; do
        sleep 10
        if python3 --version 2>/dev/null | grep -q "Python 3"; then
            echo ""
            echo "  ✅  Command Line Tools встановлено!"
            break
        fi
        # Also check if xcode-select path exists (CLT installed)
        if xcode-select -p &>/dev/null; then
            sleep 5  # Give it a moment
            if python3 --version 2>/dev/null | grep -q "Python 3"; then
                echo ""
                echo "  ✅  Command Line Tools встановлено!"
                break
            fi
        fi
        printf "."
    done
fi

echo "  ✅  $(python3 --version 2>&1)"

# ── 2. Ensure pip works ──────────────────────────────────
if ! python3 -m pip --version &>/dev/null; then
    echo "  📦  Встановлюю pip..."
    python3 -m ensurepip --upgrade &>/dev/null || {
        curl -fsSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
        python3 /tmp/get-pip.py --user &>/dev/null
    }
fi

# ── 3. Install PyObjC ────────────────────────────────────
if ! python3 -c "import objc" &>/dev/null; then
    echo "  📦  Встановлюю PyObjC (1-2 хв, це один раз)..."
    python3 -m pip install --user -q pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null \
    || python3 -m pip install -q --break-system-packages pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null \
    || python3 -m pip install -q pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null \
    || {
        echo "  ❌  PyObjC не встановився. Спробуйте:"
        echo "      python3 -m pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit"
        exit 1
    }
    echo "  ✅  PyObjC встановлено!"
else
    echo "  ✅  PyObjC: OK"
fi

# ── 4. Download & launch ─────────────────────────────────
DEST="$HOME/.local/bin/macstress.py"
mkdir -p "$(dirname "$DEST")"
echo "  📥  Завантажую MacStress..."
curl -fsSL https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/macstress.py -o "$DEST"

echo ""
echo "  🚀  Запуск! Dashboard: http://localhost:9630"
echo ""
exec python3 "$DEST"
