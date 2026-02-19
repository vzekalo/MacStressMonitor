"""MacStress entry point — python3 -m macstress"""

import os, sys, time, signal, socket, subprocess, threading
import multiprocessing as mp

from . import VERSION
from .system import detect_system
from .metrics import MetricsCollector
from .stress_manager import StressManager
from .server import ThreadedHTTPServer, Handler, set_globals
from .updater import check_for_updates
from .launcher import create_app_launcher, ensure_app_bundle
from .sudo import pre_elevate_sudo


def main():
    # Handle CLI flags
    if "--install-app" in sys.argv:
        create_app_launcher("full")
        return
    if "--install-lite-app" in sys.argv:
        create_app_launcher("lite")
        return
    if "--check-update" in sys.argv:
        check_for_updates()
        return
    if "--version" in sys.argv:
        print(f"MacStressMonitor v{VERSION}")
        return

    print("\n" + "="*60)
    print(f"  ⚡ MacStressMonitor v{VERSION} — Native macOS Stress Test + Monitor")
    print("="*60)

    si = detect_system()
    si["has_sudo"] = os.geteuid() == 0
    print(f"\n  🖥  {si['model_name']}  ({si['model_id']})")
    print(f"  🧠 {si['cpu']}  ·  {si['cores']} cores ({si['perf_cores']}P+{si['eff_cores']}E)")
    print(f"  🎮 {si['gpu']}")
    print(f"  💾 {si['ram_gb']} GB  ·  {si['arch'].upper()}")
    print(f"  💿 {si['os']}")

    # Background update check
    threading.Thread(target=check_for_updates, args=(True,), daemon=True).start()

    # Pre-elevate sudo
    sudo_pw = pre_elevate_sudo()
    si["has_sudo"] = os.geteuid() == 0 or sudo_pw is not None

    mc = MetricsCollector(si)
    if sudo_pw:
        mc._sudo_pw = sudo_pw
        del sudo_pw
    sm = StressManager(si)
    mc.start()

    # Set globals for server handlers
    set_globals(mc, sm, si)

    # Auto-create/update .app bundle
    ensure_app_bundle()

    port = 9630
    subprocess.run(f"lsof -ti:{port} | xargs kill -9 2>/dev/null", shell=True, capture_output=True)
    time.sleep(0.3)

    server = ThreadedHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
    except: pass

    print(f"\n  🌐 http://localhost:{port}")
    print(f"  📱 http://{ip}:{port}")

    # Decide: native app or browser fallback
    use_native = True
    try:
        import objc
        from AppKit import NSApplication
        import WebKit
    except ImportError:
        use_native = False
        print("\n  ⚠️  PyObjC not installed — falling back to browser mode")
        print("  Install: pip install pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-WebKit")

    if use_native:
        print("\n  🚀 Starting native macOS app...")
        print("  📊 Menu bar: CPU / RAM / SSD live stats")
        print("  🖱  Left-click: detailed popover  ·  Right-click: menu")
        print("="*60 + "\n")

        def sig_handler(sig, frame):
            sm.stop_all()
            mc.stop()
            server.shutdown()
            print("\n  ✅ Done. Goodbye!")
            os._exit(0)

        signal.signal(signal.SIGINT, sig_handler)
        signal.signal(signal.SIGTERM, sig_handler)

        from .native_app import run_native_app
        run_native_app(port, mc, sm)
    else:
        import webbrowser
        url = f"http://localhost:{port}"
        webbrowser.open(url)
        print("\n  ⏳ Dashboard ready — start stress tests from the UI")
        print("="*60 + "\n")

        def cleanup(sig=None, frame=None):
            print("\n  🛑 Stopping...")
            sm.stop_all()
            mc.stop()
            server.shutdown()
            print("  ✅ Done. Goodbye!\n")
            sys.exit(0)

        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            cleanup()


if __name__ == "__main__":
    mp.set_start_method("fork", force=True)
    main()
