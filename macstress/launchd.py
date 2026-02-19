"""Launchd service management — Start at Login."""

import os, sys, subprocess, plistlib
from pathlib import Path


PLIST_LABEL = "com.macstressmonitor"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"
LOG_PATH = Path.home() / "Library" / "Logs" / "MacStressMonitor.log"


def _python_path():
    """Get the current python executable path."""
    return sys.executable


def _pkg_dir():
    """Get the package root directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_installed():
    """Check if launchd service is installed."""
    return PLIST_PATH.exists()


def is_loaded():
    """Check if launchd service is currently loaded."""
    try:
        r = subprocess.run(
            ["launchctl", "list", PLIST_LABEL],
            capture_output=True, text=True, timeout=5
        )
        return r.returncode == 0
    except Exception:
        return False


def install():
    """Install launchd plist for Start at Login.
    Returns (success, message)."""
    try:
        PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)

        python = _python_path()
        pkg_dir = _pkg_dir()

        plist_data = {
            "Label": PLIST_LABEL,
            "ProgramArguments": [python, "-m", "macstress"],
            "WorkingDirectory": pkg_dir,
            "RunAtLoad": True,
            "KeepAlive": False,
            "StandardOutPath": str(LOG_PATH),
            "StandardErrorPath": str(LOG_PATH),
            "EnvironmentVariables": {
                "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin",
            },
        }

        with open(PLIST_PATH, "wb") as f:
            plistlib.dump(plist_data, f)

        # Load the service
        subprocess.run(
            ["launchctl", "load", str(PLIST_PATH)],
            capture_output=True, timeout=5
        )

        print(f"  ✅ Start at Login enabled")
        print(f"  📄 {PLIST_PATH}")
        return True, "Enabled"
    except Exception as e:
        return False, str(e)


def uninstall():
    """Remove launchd plist.
    Returns (success, message)."""
    try:
        # Unload first
        if is_loaded():
            subprocess.run(
                ["launchctl", "unload", str(PLIST_PATH)],
                capture_output=True, timeout=5
            )

        # Remove plist file
        if PLIST_PATH.exists():
            PLIST_PATH.unlink()

        print(f"  ✅ Start at Login disabled")
        return True, "Disabled"
    except Exception as e:
        return False, str(e)


def toggle():
    """Toggle Start at Login on/off.
    Returns (is_now_enabled, message)."""
    if is_installed():
        ok, msg = uninstall()
        return False, msg
    else:
        ok, msg = install()
        return ok, msg
