"""Sudo pre-elevation via native macOS dialog."""

import os, subprocess


def pre_elevate_sudo():
    """Get sudo password early via native macOS dialog.
    Returns the password string (to pipe via sudo -S), or None if not needed/failed."""
    if os.geteuid() == 0:
        return None
    try:
        r = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=5)
        if r.returncode == 0:
            print("  🔐 sudo: вже авторизовано")
            return None
    except Exception:
        pass
    try:
        dialog_script = (
            'text returned of (display dialog '
            '"MacStress потребує пароль для моніторингу '
            'температури та споживання енергії" '
            'with title "MacStress" default answer "" with hidden answer '
            'with icon caution)'
        )
        proc = subprocess.run(
            ["osascript", "-e", dialog_script],
            capture_output=True, text=True, timeout=120
        )
        if proc.returncode == 0 and proc.stdout.strip():
            pw = proc.stdout.strip()
            sv = subprocess.run(
                ["sudo", "-S", "-v"],
                input=pw + "\n", capture_output=True, text=True, timeout=10
            )
            if sv.returncode == 0:
                print("  🔐 sudo: авторизовано через діалог")
                return pw
            else:
                print("  ❌ sudo: невірний пароль")
                del pw
    except Exception as e:
        print(f"  ⚠️  sudo dialog: {e}")
    print("  ⚠️  Дані температури/енергії можуть бути недоступні")
    return None
