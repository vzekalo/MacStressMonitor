# MacStress — Cross-Reference & Architecture

> Token-friendly reference. Covers data flow, dependencies, API surface, and component relationships.

## Component Dependency Graph

```
main()
├── detect_system() → sys_info dict
├── _pre_elevate_sudo() → sudo password
├── MetricsCollector(sys_info)
│   ├── _collect_loop() → CPU/RAM/Swap/Disk metrics
│   ├── _sensor_loop() → Temperature (IOKit HID)
│   └── _powermetrics_loop() → Power (sudo powermetrics)
├── StressManager(sys_info)
│   ├── cpu_stress_worker()
│   ├── gpu_stress_worker()
│   ├── memory_stress_worker()
│   └── disk_stress_worker()
├── ThreadedHTTPServer + Handler
│   ├── GET / → DASHBOARD_HTML
│   ├── GET /events → SSE(MetricsCollector + StressManager)
│   └── POST /api/* → StressManager / self_update()
├── run_native_app(port)  [if PyObjC available]
│   └── AppDelegate → menu bar + WKWebView
├── check_for_updates() → GitHub API
├── self_update() → download + replace + execv
└── create_app_launcher() → .app bundle
```

## Data Flow

```
[System Hardware]
    │
    ▼
[MetricsCollector]  ←── ps, vm_stat, iostat, IOKit HID, powermetrics
    │
    ▼ get_snapshot()
[Handler /events]   ←── SSE push every 1s
    │
    ▼ JSON
[Dashboard HTML]    ←── JavaScript: upd(), ch(), ga()
    │
    ▼ fetch()
[Handler /api/*]    → StressManager.toggle/start_all/stop_all
```

## Global State

| Variable | Type | Scope | Purpose |
|----------|------|-------|---------|
| `_mc` | MetricsCollector | Module | Singleton metrics instance |
| `_sm` | StressManager | Module | Singleton stress manager |
| `_si` | dict | Module | System info cache |
| `VERSION` | str | Module | Current version ("1.4.4") |
| `GITHUB_REPO` | str | Module | "vzekalo/MacStressMonitor" |
| `_disk_bench_running` | bool | Module | Benchmark lock |
| `_disk_bench_results` | list | Module | Benchmark output |

## Key Classes

### MetricsCollector

```
Fields: sys_info, data (dict), _stop (Event), sudo_pw
Threads: _collect_loop, _sensor_loop, _powermetrics_loop
API: start(), stop(), get_snapshot() → dict
```

**Snapshot dict keys:** `cpu_usage`, `cpu_temp`, `gpu_temp`, `mem_used_gb`, `mem_total_gb`, `swap_used_gb`, `swap_total_gb`, `disk_read_mbs`, `disk_write_mbs`, `cpu_power_w`, `gpu_power_w`, `total_power_w`

### StressManager

```
Fields: sys_info, workers (dict), stop_events (dict), active (set), _timer
API: start_test(name), stop_test(name), toggle(name),
     start_all(duration=600), stop_all(), get_active() → list
```

**Test names:** `"cpu"`, `"gpu"`, `"memory"`, `"disk"`

### Handler (HTTP)

```
Inherits: BaseHTTPRequestHandler
Suppresses: log_message
Custom: _ok(ct, body), _send_event(data)
```

### AppDelegate (PyObjC)

```
Inherits: NSObject
Selectors: applicationDidFinishLaunching_, checkUpdate_,
           updateMenuBar_, openDashboard_, startAll_,
           stopAll_, quit_
```

## API Reference

### REST Endpoints

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/` | GET | — | HTML dashboard |
| `/events` | GET | — | SSE: `{metrics, active, sys_info}` |
| `/api/status` | GET | — | `{metrics, active, sys_info}` |
| `/api/check_update` | GET | — | `{has_update, latest, current, url}` |
| `/api/toggle` | POST | `{test, action}` | `{ok, active}` |
| `/api/toggle_all` | POST | `{action, duration?}` | `{ok, active}` |
| `/api/disk_bench` | POST | — | `{ok, status}` |
| `/api/disk_bench_result` | GET | — | `{running, results[]}` |
| `/api/do_update?ver=X` | POST | — | `{ok, error?}` |

### SSE Event Format

```json
{
  "metrics": {
    "cpu_usage": 45.2,
    "cpu_temp": 52.3,
    "gpu_temp": 48.1,
    "mem_used_gb": 12.4,
    "mem_total_gb": 16.0,
    "swap_used_gb": 0.5,
    "swap_total_gb": 2.0,
    "disk_read_mbs": 125.3,
    "disk_write_mbs": 89.7,
    "cpu_power_w": 8.5,
    "gpu_power_w": 3.2,
    "total_power_w": 17.1
  },
  "active": ["cpu", "memory"],
  "sys_info": { "arch": "arm64", "cores": 10, ... }
}
```

## File Cross-Reference

| File | Lines | Purpose | Dependencies |
|------|-------|---------|-------------|
| `macstress.py` | 1537 | Full version | stdlib, PyObjC (optional) |
| `macstress_lite.sh` | 460 | Lite version (bash) | bash 3.2+, curl, iostat, ps, vm_stat |
| `install.sh` | ~300 | Universal installer | curl, python-build-standalone |
| `build_app.sh` | ~100 | PyInstaller builder | PyInstaller, PyObjC |
| `setup.py` | ~30 | Package config | setuptools |
| `icons/macstress.icns` | — | App icon (squircle, alpha) | Generated via iconutil |
| `icons/macstress.png` | — | Source PNG (1024x1024) | — |

## System Commands Used

| Command | Purpose | Caller |
|---------|---------|--------|
| `ps -A -o %cpu` | CPU usage | MetricsCollector |
| `vm_stat` | Memory pages | MetricsCollector |
| `sysctl vm.swapusage` | Swap usage | MetricsCollector |
| `iostat -d -c 2` | Disk I/O | MetricsCollector |
| `powermetrics` | Power/temp (Intel) | MetricsCollector |
| `dd if= of= bs= count=` | Disk benchmark | _dd_bench |
| `clang -o ... -framework IOKit` | Compile temp sensor | compile_temp_sensor |
| `osascript 'do shell script'` | Sudo dialog | _pre_elevate_sudo |
| `lsregister -u/-f` | Icon cache | create_app_launcher |
| `killall iconservicesd/Dock/Finder` | Refresh UI | create_app_launcher |
| `curl` / `urllib.request` | GitHub API + downloads | check_for_updates, self_update |

## Ports & Paths

| Resource | Value |
|----------|-------|
| HTTP server | `localhost:9630` |
| Temp sensor binary | `/tmp/macstress_temp_sensor` |
| Temp sensor C source | `/tmp/macstress_temp_sensor.c` |
| Benchmark temp files | `/tmp/macstress_bench_*` |
| Powermetrics data | internal (stdout parsing) |
| App bundle | `~/Applications/MacStress.app` |
| Lite app bundle | `~/Applications/MacStress Lite.app` |
| Disk I/O cache (Lite) | `/tmp/macstress_dio` |
| Powermetrics cache (Lite) | `/tmp/macstress_pm_data` |

## Update Flow

```
[User clicks "Check for Updates"]
    │
    ▼
check_for_updates(silent=True)
    │ GET https://api.github.com/repos/{REPO}/releases/latest
    ▼
{has_update: true, latest: "1.4.4"}
    │
    ▼
[User clicks "⬇ Оновити"]
    │
    ▼ POST /api/do_update?ver=1.4.4
self_update(target_ver="1.4.4")
    │ GET https://raw.githubusercontent.com/{REPO}/v1.4.4/macstress.py
    │ ast.parse(new_code)          ← syntax validation
    │ re.search VERSION            ← version extraction
    │ _ver_tuple comparison        ← newer check
    │ os.replace(tmp, script)      ← atomic swap
    ▼
{ok: true}
    │
    ▼ Thread: sleep(1) → os.execv(sys.executable, sys.argv)
[Process restarts with new code]
```
