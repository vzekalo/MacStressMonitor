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
    
    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
        PY_TRIPLE="aarch64-apple-darwin"
    else
        PY_TRIPLE="x86_64-apple-darwin"
    fi
    
    # Discover latest release tag from GitHub API, fallback to known-good
    PY_TAG=$(curl -fsSL "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest" 2>/dev/null | grep '"tag_name"' | head -1 | sed 's/.*"tag_name"[^"]*"\([^"]*\)".*/\1/')
    [ -z "$PY_TAG" ] && PY_TAG="20260211"
    info "Release tag: $PY_TAG"
    
    mkdir -p "$INSTALL_DIR"
    TMP_TAR="/tmp/macstress_python.tar.gz"
    DOWNLOADED=""
    
    # Try multiple Python versions — releases may bundle different ones
    for PY_VER in 3.13.3 3.13.2 3.13.1 3.12.10 3.12.9 3.11.12 3.11.11 3.10.19 3.10.18; do
        PY_FILE="cpython-${PY_VER}+${PY_TAG}-${PY_TRIPLE}-install_only.tar.gz"
        PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PY_TAG}/${PY_FILE}"
        info "Trying Python ${PY_VER}..."
        if curl -fSL --connect-timeout 10 "$PY_URL" -o "$TMP_TAR" 2>/dev/null; then
            DOWNLOADED="yes"
            break
        fi
    done
    
    if [ -n "$DOWNLOADED" ]; then
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
        warn "All download attempts failed"
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

info "Downloading MacStress..."
curl -fsSL "https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/macstress.py" -o "$APP_FILE"
curl -fsSL "https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/macstress_lite.sh" -o "$INSTALL_DIR/macstress_lite.sh" 2>/dev/null
chmod +x "$INSTALL_DIR/macstress_lite.sh" 2>/dev/null

# Create a launch script for easy re-launch
cat > "$INSTALL_DIR/launch.sh" << LAUNCH
#!/bin/bash
exec "$PY3" "$APP_FILE"
LAUNCH
chmod +x "$INSTALL_DIR/launch.sh"

# ══════════════════════════════════════════════════════════
# 5. CREATE APP LAUNCHERS IN ~/Applications
# ══════════════════════════════════════════════════════════
info "Creating app launchers..."

APPS_DIR="$HOME/Applications"
mkdir -p "$APPS_DIR"

# MacStress.app (full version)
MS_APP="$APPS_DIR/MacStress.app"
mkdir -p "$MS_APP/Contents/MacOS"
cat > "$MS_APP/Contents/MacOS/MacStress" << 'MSLAUNCH'
#!/bin/bash
osascript -e 'tell app "Terminal" to do script "~/.macstress/launch.sh"' \
    -e 'tell app "Terminal" to activate'
MSLAUNCH
chmod 755 "$MS_APP/Contents/MacOS/MacStress"
cat > "$MS_APP/Contents/Info.plist" << MSPLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>   <string>MacStress</string>
    <key>CFBundleIdentifier</key>   <string>com.macstress.full</string>
    <key>CFBundleName</key>         <string>MacStress</string>
    <key>CFBundlePackageType</key>  <string>APPL</string>
</dict>
</plist>
MSPLIST
ok "MacStress.app → ~/Applications/"

# MacStress Lite.app
if [ -f "$INSTALL_DIR/macstress_lite.sh" ]; then
    ML_APP="$APPS_DIR/MacStress Lite.app"
    mkdir -p "$ML_APP/Contents/MacOS"
    cat > "$ML_APP/Contents/MacOS/MacStressLite" << MLLAUNCH
#!/bin/bash
osascript -e 'tell app "Terminal" to do script "bash \"$INSTALL_DIR/macstress_lite.sh\""' \\
    -e 'tell app "Terminal" to activate'
MLLAUNCH
    chmod 755 "$ML_APP/Contents/MacOS/MacStressLite"
    cat > "$ML_APP/Contents/Info.plist" << MLPLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>   <string>MacStressLite</string>
    <key>CFBundleIdentifier</key>   <string>com.macstress.lite</string>
    <key>CFBundleName</key>         <string>MacStress Lite</string>
    <key>CFBundlePackageType</key>  <string>APPL</string>
</dict>
</plist>
MLPLIST
    ok "MacStress Lite.app → ~/Applications/"
fi

printf "\n"
printf "  ${G}============================================${N}\n"
if [ "$NATIVE_OK" -eq 1 ]; then
    printf "  ${G}*${N} ${B}MacStress ready (native + web)${N}\n"
else
    printf "  ${Y}*${N} ${B}MacStress ready (web-only mode)${N}\n"
fi
printf "  ${C}Dashboard:${N} http://localhost:9630\n"
printf "  ${C}Re-launch:${N} ~/.macstress/launch.sh\n"
printf "  ${C}Apps:${N}      ~/Applications/MacStress.app\n"
printf "  ${G}============================================${N}\n"
printf "\n"

exec "$PY3" "$APP_FILE"
