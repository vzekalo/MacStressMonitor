#!/bin/bash
# MacStress — Universal Installer
# Works on ANY Mac (2010+), no App Store, no Homebrew, no .pkg installer
# Downloads portable Python from GitHub → extracts → runs

R=$'\033[0;31m'
G=$'\033[0;32m'
Y=$'\033[0;33m'
C=$'\033[0;36m'
B=$'\033[1m'
N=$'\033[0m'

ok()   { printf "  ${G}OK${N}  %s\n" "$1"; }
warn() { printf "  ${Y}!!${N}  %s\n" "$1"; }
fail() { printf "  ${R}ERR${N} %s\n" "$1"; }
info() { printf "  ${C}>>${N}  %s\n" "$1"; }

INSTALL_DIR="$HOME/.macstress"
PY_DIR="$INSTALL_DIR/python"
APP_FILE="$INSTALL_DIR/macstress.py"

printf "\n"
printf "  ${Y}*${N} ${B}MacStress — Universal Installer${N}\n"
printf "  ${C}No App Store, no Homebrew, no admin needed${N}\n"
printf "\n"

# ══════════════════════════════════════════════════════════
# 1. FIND OR DOWNLOAD PYTHON 3
# ══════════════════════════════════════════════════════════
PY3=""
ARCH=$(uname -m)

# Check if we already have portable Python installed
if [ -x "$PY_DIR/bin/python3" ]; then
    PY3="$PY_DIR/bin/python3"
    ok "Portable Python: $($PY3 --version 2>&1)"
fi

# Check system Python 3
if [ -z "$PY3" ]; then
    for p in python3 /usr/local/bin/python3 /usr/bin/python3 \
             /Library/Frameworks/Python.framework/Versions/*/bin/python3; do
        if "$p" --version 2>/dev/null | grep -q "Python 3"; then
            PY3="$p"
            ok "System Python: $($PY3 --version 2>&1)"
            break
        fi
    done
fi

# Download portable Python from GitHub (no installer, no sudo, no .pkg)
if [ -z "$PY3" ]; then
    info "Downloading portable Python from GitHub..."
    
    # python-build-standalone by astral-sh — fully relocatable builds
    # These work on macOS 10.9+ without any installation
    PY_VER="3.12.9"
    PY_TAG="20250210"
    
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
        PY_TRIPLE="aarch64-apple-darwin"
    else
        PY_TRIPLE="x86_64-apple-darwin"
    fi
    
    PY_FILE="cpython-${PY_VER}+${PY_TAG}-${PY_TRIPLE}-install_only.tar.gz"
    PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PY_TAG}/${PY_FILE}"
    
    info "URL: $PY_URL"
    info "Size: ~40MB, downloading..."
    
    mkdir -p "$INSTALL_DIR"
    TMP_TAR="/tmp/macstress_python.tar.gz"
    
    if curl -fSL "$PY_URL" -o "$TMP_TAR" 2>/dev/null; then
        info "Extracting to $PY_DIR..."
        rm -rf "$PY_DIR"
        mkdir -p "$PY_DIR"
        tar xf "$TMP_TAR" -C "$INSTALL_DIR" 2>/dev/null
        rm -f "$TMP_TAR"
        
        if [ -x "$PY_DIR/bin/python3" ]; then
            PY3="$PY_DIR/bin/python3"
            ok "Portable Python: $($PY3 --version 2>&1)"
        else
            # tar might extract to a subdirectory, find it
            PY_BIN=$(find "$INSTALL_DIR" -name "python3" -type f -perm +111 2>/dev/null | head -1)
            if [ -n "$PY_BIN" ]; then
                PY3="$PY_BIN"
                PY_DIR=$(dirname "$(dirname "$PY_BIN")")
                ok "Portable Python: $($PY3 --version 2>&1)"
            fi
        fi
    else
        warn "Download failed. Trying older Python 3.11..."
        
        # Fallback: try Python 3.11
        PY_VER="3.11.11"
        PY_TAG="20250210"
        PY_FILE="cpython-${PY_VER}+${PY_TAG}-${PY_TRIPLE}-install_only.tar.gz"
        PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PY_TAG}/${PY_FILE}"
        
        if curl -fSL "$PY_URL" -o "$TMP_TAR" 2>/dev/null; then
            rm -rf "$PY_DIR"
            mkdir -p "$PY_DIR"
            tar xf "$TMP_TAR" -C "$INSTALL_DIR" 2>/dev/null
            rm -f "$TMP_TAR"
            PY_BIN=$(find "$INSTALL_DIR" -name "python3" -type f -perm +111 2>/dev/null | head -1)
            if [ -n "$PY_BIN" ]; then
                PY3="$PY_BIN"
                ok "Portable Python: $($PY3 --version 2>&1)"
            fi
        fi
    fi
    
    if [ -z "$PY3" ]; then
        fail "Could not find or download Python 3."
        printf "\n"
        printf "  Use MacStress Lite instead (zero dependencies):\n"
        printf "  ${C}curl -fsSL https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/macstress_lite.sh | bash${N}\n"
        printf "\n"
        exit 1
    fi
fi

# ══════════════════════════════════════════════════════════
# 2. ENSURE PIP
# ══════════════════════════════════════════════════════════
info "Checking pip..."

if "$PY3" -m pip --version >/dev/null 2>&1; then
    ok "pip ready"
else
    info "Bootstrapping pip..."
    "$PY3" -m ensurepip --upgrade >/dev/null 2>&1 \
    || {
        curl -fsSL "https://bootstrap.pypa.io/get-pip.py" -o /tmp/get-pip.py 2>/dev/null \
        || curl -fsSL "https://github.com/pypa/get-pip/raw/main/public/get-pip.py" -o /tmp/get-pip.py 2>/dev/null
        [ -f /tmp/get-pip.py ] && "$PY3" /tmp/get-pip.py --user >/dev/null 2>&1
        rm -f /tmp/get-pip.py
    }
    "$PY3" -m pip --version >/dev/null 2>&1 && ok "pip ready" || warn "pip not available"
fi

# ══════════════════════════════════════════════════════════
# 3. TRY PyObjC (optional — app works without it)
# ══════════════════════════════════════════════════════════
NATIVE_OK=0

info "Checking PyObjC..."

if "$PY3" -c "import objc" >/dev/null 2>&1; then
    ok "PyObjC installed"
    NATIVE_OK=1
else
    info "Installing PyObjC (1-2 min, for native menu bar)..."
    "$PY3" -m pip install --user -q pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null \
    || "$PY3" -m pip install -q --break-system-packages pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null \
    || "$PY3" -m pip install -q pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null \
    || true

    if "$PY3" -c "import objc" >/dev/null 2>&1; then
        ok "PyObjC installed"
        NATIVE_OK=1
    else
        warn "PyObjC unavailable — web-only mode (dashboard in browser)"
    fi
fi

# ══════════════════════════════════════════════════════════
# 4. DOWNLOAD & LAUNCH
# ══════════════════════════════════════════════════════════
mkdir -p "$INSTALL_DIR"

info "Downloading MacStress app..."
curl -fsSL "https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/macstress.py" -o "$APP_FILE"

# Create a launch script for easy re-launch
cat > "$INSTALL_DIR/launch.sh" << LAUNCH
#!/bin/bash
exec "$PY3" "$APP_FILE"
LAUNCH
chmod +x "$INSTALL_DIR/launch.sh"

printf "\n"
printf "  ${G}============================================${N}\n"
if [ "$NATIVE_OK" -eq 1 ]; then
    printf "  ${G}*${N} ${B}MacStress ready (native + web)${N}\n"
else
    printf "  ${Y}*${N} ${B}MacStress ready (web-only mode)${N}\n"
fi
printf "  ${C}Dashboard:${N} http://localhost:9630\n"
printf "  ${C}Re-launch:${N} ~/.macstress/launch.sh\n"
printf "  ${G}============================================${N}\n"
printf "\n"

exec "$PY3" "$APP_FILE"
