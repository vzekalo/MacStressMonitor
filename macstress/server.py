"""HTTP server and API endpoints."""

import json, time, threading, os, sys
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

from . import VERSION, GITHUB_REPO
from .dashboard import DASHBOARD_HTML
from .popover import POPOVER_HTML
from .benchmark import run_disk_benchmark, get_bench_status
from .updater import check_for_updates, self_update


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


# Module-level references set by __main__
_mc = None
_sm = None
_si = None


def set_globals(mc, sm, si):
    global _mc, _sm, _si
    _mc, _sm, _si = mc, sm, si


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._ok("text/html", DASHBOARD_HTML.encode())
        elif self.path == "/popover":
            self._ok("text/html", POPOVER_HTML.encode())
        elif self.path == "/events":
            self.send_response(200)
            for k, v in [("Content-Type","text/event-stream"),("Cache-Control","no-cache"),
                         ("Connection","keep-alive"),("Access-Control-Allow-Origin","*")]:
                self.send_header(k, v)
            self.end_headers()
            self._send_event(json.dumps({"sys_info": _si, "active": _sm.get_active()}))
            try:
                while True:
                    self._send_event(json.dumps({
                        "metrics": _mc.get_snapshot(), "active": _sm.get_active(), "sys_info": _si
                    }))
                    time.sleep(2.0)
            except (BrokenPipeError, ConnectionResetError, OSError): pass
        elif self.path == "/api/status":
            self._ok("application/json", json.dumps({"metrics": _mc.get_snapshot(), "active": _sm.get_active(), "sys_info": _si}).encode())
        elif self.path == "/api/details":
            details = _mc.get_details()
            from . import launchd
            details["launchd_installed"] = launchd.is_installed()
            self._ok("application/json", json.dumps(details).encode())
        elif self.path == "/api/launchd_status":
            from . import launchd
            self._ok("application/json", json.dumps({"installed": launchd.is_installed()}).encode())
        elif self.path == "/api/disk_bench_result":
            self._ok("application/json", json.dumps(get_bench_status()).encode())
        elif self.path == "/api/check_update":
            result = check_for_updates(silent=True)
            has_update = False
            latest_ver = VERSION
            if result:
                has_update, latest_ver = result
            self._ok("application/json", json.dumps({
                "current": VERSION,
                "latest": latest_ver,
                "has_update": has_update,
                "url": f"https://github.com/{GITHUB_REPO}/releases/latest",
                "custom_ver": VERSION
            }).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path.startswith("/api/toggle?"):
            t = self.path.split("test=")[-1].split("&")[0]
            if t in ("cpu","gpu","memory","disk"):
                threading.Thread(target=_sm.toggle, args=(t,), daemon=True).start()
            self._ok("application/json", b'{"ok":true}')
        elif self.path.startswith("/api/toggle_all"):
            on = "on=1" in self.path
            dur = 600
            try:
                qs = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(qs)
                dur = int(params.get('dur', ['600'])[0])
            except: pass
            if on:
                threading.Thread(target=_sm.start_all, args=(dur,), daemon=True).start()
            else:
                threading.Thread(target=_sm.stop_all, daemon=True).start()
            self._ok("application/json", b'{"ok":true}')
        elif self.path == "/api/disk_bench":
            status = get_bench_status()
            if status["running"]:
                self._ok("application/json", json.dumps({"error": "Benchmark already running"}).encode())
            else:
                threading.Thread(target=run_disk_benchmark, daemon=True).start()
                self._ok("application/json", json.dumps({"ok": True, "status": "started"}).encode())
        elif self.path.startswith("/api/do_update"):
            try:
                ver = None
                qs = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(qs)
                ver = params.get('ver', [None])[0]
                ok, msg = self_update(target_ver=ver)
                self._ok("application/json", json.dumps({"ok": ok, "error": msg if not ok else None}).encode())
                if ok:
                    threading.Thread(target=lambda: (time.sleep(1), os.execv(sys.executable, [sys.executable] + sys.argv)), daemon=True).start()
            except Exception as e:
                self._ok("application/json", json.dumps({"ok": False, "error": str(e)}).encode())
        elif self.path == "/api/open_dashboard":
            self._ok("application/json", b'{"ok":true}')
        elif self.path == "/api/quit_app":
            self._ok("application/json", b'{"ok":true}')
            def _quit():
                time.sleep(0.3)
                _sm.stop_all()
                _mc.stop()
                # Try NSApp terminate for clean native app shutdown
                try:
                    from AppKit import NSApp
                    NSApp.performSelectorOnMainThread_withObject_waitUntilDone_(
                        'terminate:', None, False
                    )
                except Exception:
                    pass
                # Always force-exit after a short grace period
                time.sleep(1.0)
                os._exit(0)
            threading.Thread(target=_quit, daemon=True).start()
        elif self.path == "/api/install_dock":
            from .launcher import create_app_launcher
            try:
                path = create_app_launcher("full", add_to_dock=True)
                self._ok("application/json", json.dumps({"ok": True, "path": path}).encode())
            except Exception as e:
                self._ok("application/json", json.dumps({"ok": False, "error": str(e)}).encode())
        elif self.path.startswith("/api/toggle_stress"):
            qs = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(qs)
            action = params.get('action', [''])[0]
            if action == 'start':
                threading.Thread(target=_sm.start_all, args=(600,), daemon=True).start()
            elif action == 'stop':
                threading.Thread(target=_sm.stop_all, daemon=True).start()
            self._ok("application/json", b'{"ok":true}')
        elif self.path == "/api/request_sudo":
            # Prompt for sudo password via osascript dialog and restart powermetrics
            def _do_sudo():
                try:
                    import subprocess as sp
                    # Ask for password via native dialog
                    result = sp.run(
                        ['osascript', '-e',
                         'display dialog "Enter admin password to enable power metrics:" '
                         'default answer "" with hidden answer with title "MacStressMonitor"'],
                        capture_output=True, text=True, timeout=60
                    )
                    if result.returncode == 0 and 'text returned:' in result.stdout:
                        pwd = result.stdout.split('text returned:')[1].strip()
                        if pwd:
                            # Validate password
                            check = sp.run(
                                ['sudo', '-S', '-k', 'true'],
                                input=pwd + '\n', capture_output=True, text=True, timeout=10
                            )
                            if check.returncode == 0:
                                _mc._sudo_pw = pwd
                                # Restart powermetrics loop
                                threading.Thread(target=_mc._powermetrics_loop, daemon=True).start()
                except Exception:
                    pass
            threading.Thread(target=_do_sudo, daemon=True).start()
            self._ok("application/json", b'{"ok":true}')
        elif self.path == "/api/toggle_launchd":
            from . import launchd
            enabled, msg = launchd.toggle()
            self._ok("application/json", json.dumps({"ok": True, "enabled": enabled, "message": msg}).encode())
        else:
            self.send_error(404)

    def _ok(self, ct, body):
        self.send_response(200); self.send_header("Content-Type", ct); self.end_headers(); self.wfile.write(body)

    def _send_event(self, data):
        self.wfile.write(f"data: {data}\n\n".encode()); self.wfile.flush()
