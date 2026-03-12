"""Update checking and self-updating."""

import os, sys, re, json
from . import VERSION, GITHUB_REPO

# All package modules to download during self-update
_PKG_MODULES = [
    "__init__.py", "__main__.py", "benchmark.py", "dashboard.py",
    "launchd.py", "launcher.py", "metrics.py", "native_app.py",
    "popover.py", "server.py", "stress.py", "stress_manager.py",
    "sudo.py", "system.py", "updater.py",
]


def _ver_tuple(v):
    """Parse version string to tuple: '1.3.0' -> (1, 3, 0)."""
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0,)


def check_for_updates(silent=False):
    """Check GitHub for newer version. Returns (has_update, latest_ver) or None."""
    try:
        import urllib.request
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "MacStress"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            latest = data.get("tag_name", "").lstrip("v")
            if latest and _ver_tuple(latest) > _ver_tuple(VERSION):
                print(f"\n  🆕 Нова версія доступна: v{latest} (поточна: v{VERSION})")
                print(f"  📥 https://github.com/{GITHUB_REPO}/releases/latest")
                return True, latest
            elif not silent:
                print(f"  ✅ Актуальна версія: v{VERSION}")
            return False, VERSION
    except Exception:
        if not silent:
            print("  ⚠️  Не вдалося перевірити оновлення")
        return None, VERSION


def self_update(target_ver=None):
    """Download latest from GitHub and replace local files.
    Returns (success: bool, message: str)."""
    try:
        import urllib.request, ast

        if not target_ver:
            result = check_for_updates(silent=True)
            if result and result[0]:
                target_ver = result[1]
            else:
                return False, "Немає доступних оновлень"

        base_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/v{target_ver}"

        # Download macstress.py wrapper
        raw_url = f"{base_url}/macstress.py"
        req = urllib.request.Request(raw_url, headers={
            "User-Agent": "MacStress",
            "Cache-Control": "no-cache",
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            new_wrapper = r.read()
        ast.parse(new_wrapper)

        # Download all package modules
        pkg_dir = os.path.dirname(os.path.abspath(__file__))
        dl_ok = 0
        for mod in _PKG_MODULES:
            try:
                mod_url = f"{base_url}/macstress/{mod}"
                req = urllib.request.Request(mod_url, headers={
                    "User-Agent": "MacStress",
                    "Cache-Control": "no-cache",
                })
                with urllib.request.urlopen(req, timeout=15) as r:
                    mod_code = r.read()
                ast.parse(mod_code)
                tmp_path = os.path.join(pkg_dir, mod + ".tmp")
                with open(tmp_path, "wb") as f:
                    f.write(mod_code)
                os.replace(tmp_path, os.path.join(pkg_dir, mod))
                dl_ok += 1
            except Exception:
                pass  # Non-critical: module might not exist in new version

        # Read new version from updated __init__.py
        init_path = os.path.join(pkg_dir, "__init__.py")
        with open(init_path, "r") as f:
            init_code = f.read()
        m = re.search(r'VERSION\s*=\s*["\']([\d.]+)["\']', init_code)
        new_ver = m.group(1) if m else target_ver

        if _ver_tuple(new_ver) <= _ver_tuple(VERSION):
            return False, f"Завантажена версія ({new_ver}) не новіша за поточну ({VERSION})"

        # Update wrapper script
        script_dir = os.path.dirname(pkg_dir)
        wrapper_path = os.path.join(script_dir, "macstress.py")
        if os.path.exists(wrapper_path):
            tmp_path = wrapper_path + ".tmp"
            with open(tmp_path, "wb") as f:
                f.write(new_wrapper)
            os.replace(tmp_path, wrapper_path)

        print(f"  ✅ Оновлено: v{VERSION} → v{new_ver} ({dl_ok} модулів)")
        return True, new_ver
    except Exception as e:
        return False, str(e)
