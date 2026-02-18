#!/bin/bash
# MacStress — Universal Installer
# Works on ANY Mac (2010+), even with blocked updates
# Downloads everything from GitHub / python.org — no App Store needed

set -e

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

printf "\n"
printf "  ${Y}*${N} ${B}MacStress — Universal Installer${N}\n"
printf "  ${C}Works on ANY Mac (2010+)${N}\n"
printf "\n"

# ══════════════════════════════════════════════════════════
# 1. FIND OR INSTALL PYTHON 3
# ══════════════════════════════════════════════════════════
PY3=""

find_python3() {
    # Check common Python 3 locations
    for p in python3 /usr/local/bin/python3 /usr/bin/python3 \
             /Library/Frameworks/Python.framework/Versions/3.*/bin/python3 \
             /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
        if "$p" --version 2>/dev/null | grep -q "Python 3"; then
            PY3="$p"
            return 0
        fi
    done
    return 1
}

info "Checking for Python 3..."

if find_python3; then
    ok "Found: $($PY3 --version 2>&1)"
else
    warn "Python 3 not found. Trying to install..."
    
    # Strategy A: Command Line Tools (works on macOS 10.9+)
    info "Trying Command Line Tools..."
    xcode-select --install 2>/dev/null && {
        printf "  Press 'Install' in the macOS dialog.\n"
        printf "  Waiting"
        i=0
        while [ "$i" -lt 60 ]; do
            sleep 10
            printf "."
            if find_python3; then
                printf "\n"
                ok "CLT installed: $($PY3 --version 2>&1)"
                break
            fi
            i=$((i + 1))
        done
    }

    # Strategy B: Download Python from python.org
    if [ -z "$PY3" ]; then
        info "Downloading Python from python.org..."
        
        # Detect architecture
        ARCH=$(uname -m)
        OSVER=$(sw_vers -productVersion 2>/dev/null || echo "10.9")
        MAJOR=$(echo "$OSVER" | cut -d. -f1)
        MINOR=$(echo "$OSVER" | cut -d. -f2)
        
        # Choose Python version based on macOS
        # Python 3.9.x — last version for macOS 10.9+
        # Python 3.8.x — works on macOS 10.9+
        if [ "$MAJOR" -ge 11 ] 2>/dev/null || [ "$MINOR" -ge 15 ] 2>/dev/null; then
            # macOS 10.15+ or 11+: can use latest Python 3.12
            PY_URL="https://www.python.org/ftp/python/3.12.8/python-3.12.8-macos11.pkg"
        elif [ "$MINOR" -ge 9 ] 2>/dev/null; then
            # macOS 10.9-10.14: Python 3.9.x (last supporting 10.9)
            PY_URL="https://www.python.org/ftp/python/3.9.21/python-3.9.21-macosx10.9.pkg"
        else
            # macOS 10.8 or older: Python 3.7.x (last supporting 10.6)
            PY_URL="https://www.python.org/ftp/python/3.7.9/python-3.7.9-macosx10.9.pkg"
        fi
        
        PY_PKG="/tmp/macstress_python.pkg"
        info "Downloading: $PY_URL"
        if curl -fSL "$PY_URL" -o "$PY_PKG" 2>/dev/null; then
            info "Installing Python (needs admin password)..."
            sudo installer -pkg "$PY_PKG" -target / < /dev/tty 2>/dev/null && {
                rm -f "$PY_PKG"
                # Refresh path
                export PATH="/Library/Frameworks/Python.framework/Versions/3.12/bin:/Library/Frameworks/Python.framework/Versions/3.9/bin:/Library/Frameworks/Python.framework/Versions/3.7/bin:/usr/local/bin:$PATH"
                if find_python3; then
                    ok "Python from python.org: $($PY3 --version 2>&1)"
                fi
            }
        else
            warn "Could not download Python .pkg"
        fi
    fi

    if [ -z "$PY3" ]; then
        fail "Could not find or install Python 3."
        printf "\n"
        printf "  Try manually installing Python from:\n"
        printf "  https://www.python.org/downloads/\n"
        printf "\n"
        printf "  Or use MacStress Lite (zero dependencies):\n"
        printf "  curl -fsSL https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/macstress_lite.sh | bash\n"
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
    info "Installing pip..."
    
    # Try ensurepip first
    "$PY3" -m ensurepip --upgrade >/dev/null 2>&1 && {
        ok "pip via ensurepip"
    } || {
        # Download get-pip.py from GitHub (works even if PyPI TLS fails)
        info "Downloading get-pip.py from GitHub..."
        curl -fsSL "https://bootstrap.pypa.io/get-pip.py" -o /tmp/get-pip.py 2>/dev/null \
        || curl -fsSL "https://github.com/pypa/get-pip/raw/main/public/get-pip.py" -o /tmp/get-pip.py 2>/dev/null
        
        if [ -f /tmp/get-pip.py ]; then
            "$PY3" /tmp/get-pip.py --user >/dev/null 2>&1 && ok "pip from bootstrap" \
            || warn "pip install failed"
            rm -f /tmp/get-pip.py
        else
            warn "Could not download get-pip.py"
        fi
    }
fi

# ══════════════════════════════════════════════════════════
# 3. INSTALL PyObjC (optional — app works without it)
# ══════════════════════════════════════════════════════════
NATIVE_OK=0

info "Checking PyObjC (native menu bar)..."

if "$PY3" -c "import objc" >/dev/null 2>&1; then
    ok "PyObjC installed"
    NATIVE_OK=1
else
    info "Installing PyObjC (may take 1-2 min)..."
    
    # Try multiple pip strategies
    "$PY3" -m pip install --user -q pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null \
    || "$PY3" -m pip install -q --break-system-packages pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null \
    || "$PY3" -m pip install -q pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit 2>/dev/null
    
    if "$PY3" -c "import objc" >/dev/null 2>&1; then
        ok "PyObjC installed"
        NATIVE_OK=1
    else
        warn "PyObjC failed — will run in web-only mode"
        warn "Dashboard works in any browser, no menu bar"
    fi
fi

# ══════════════════════════════════════════════════════════
# 4. DOWNLOAD & LAUNCH
# ══════════════════════════════════════════════════════════
DEST="$HOME/.local/bin/macstress.py"
mkdir -p "$(dirname "$DEST")"

info "Downloading MacStress..."
curl -fsSL "https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/macstress.py" -o "$DEST"

printf "\n"
printf "  ${G}================================================${N}\n"

if [ "$NATIVE_OK" -eq 1 ]; then
    printf "  ${G}*${N} ${B}Starting MacStress (native app + web)${N}\n"
else
    printf "  ${Y}*${N} ${B}Starting MacStress (web-only mode)${N}\n"
fi

printf "  ${C}Dashboard:${N} http://localhost:9630\n"
printf "  ${G}================================================${N}\n"
printf "\n"

exec "$PY3" "$DEST"
