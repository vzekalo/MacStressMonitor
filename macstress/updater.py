"""Update checking and self-updating."""

import os, sys, re, json
from . import VERSION, GITHUB_REPO


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
        import urllib.request

        if not target_ver:
            result = check_for_updates(silent=True)
            if result and result[0]:
                target_ver = result[1]
            else:
                return False, "Немає доступних оновлень"

        # Download from release tag (not main branch — CDN caches main for 3-5 min)
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/v{target_ver}/macstress.py"
        req = urllib.request.Request(raw_url, headers={
            "User-Agent": "MacStress",
            "Cache-Control": "no-cache",
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            new_code = r.read()

        import ast
        ast.parse(new_code)

        m = re.search(rb'VERSION\s*=\s*["\'](\d[\d.]+)["\']', new_code)
        if not m:
            return False, "Не вдалося визначити версію нового файлу"
        new_ver = m.group(1).decode()
        if _ver_tuple(new_ver) <= _ver_tuple(VERSION):
            return False, f"Завантажена версія ({new_ver}) не новіша за поточну ({VERSION})"

        # Atomic replace
        script_path = os.path.abspath(sys.modules['__main__'].__file__)
        tmp_path = script_path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(new_code)
        os.replace(tmp_path, script_path)

        print(f"  ✅ Оновлено: v{VERSION} → v{new_ver}")
        return True, new_ver
    except Exception as e:
        return False, str(e)
