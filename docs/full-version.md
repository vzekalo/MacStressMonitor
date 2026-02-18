# MacStress Full Version — Architecture & Reference

> `macstress.py` — 1537 lines, single-file Python app  
> [← Back to Index](index.md) · [Lite Version →](lite-version.md)

---

## Table of Contents

- [Component Map](#component-map)
- [System Detection](#system-detection)
- [Temperature Sensor](#temperature-sensor)
- [Stress Workers](#stress-workers)
- [Metrics Collector](#metrics-collector)
- [Dashboard](#dashboard)
- [Stress Manager](#stress-manager)
- [Web Server & API](#web-server--api)
- [Native macOS App](#native-macos-app)
- [Disk Benchmark](#disk-benchmark)
- [Auto-Update](#auto-update)
- [App Launcher & Icon](#app-launcher--icon)
- [Main Entry Point](#main-entry-point)
- [System Commands Reference](#system-commands-reference)
- [Ports & Paths](#ports--paths)

---

## Component Map

```
main() ─────────────────────────────────────────────────
│
├── detect_system()           → sys_info dict
├── _pre_elevate_sudo()       → sudo password (osascript)
│
├── MetricsCollector(sys_info)
│   ├── _collect_loop()       → CPU / RAM / Swap / Disk (2s)
│   ├── _sensor_loop()        → Temperature via IOKit HID (1.5s)
│   └── _powermetrics_loop()  → Power via sudo powermetrics (3s)
│
├── StressManager(sys_info)
│   ├── cpu_stress_worker()   → math loops / yes (Intel)
│   ├── gpu_stress_worker()   → Metal compute shader
│   ├── memory_stress_worker()→ mmap allocation + read
│   └── disk_stress_worker()  → tempfile 256MB write/read
│
├── ThreadedHTTPServer(:9630)
│   └── Handler
│       ├── GET /             → Dashboard HTML
│       ├── GET /events       → SSE stream
│       └── POST /api/*       → REST endpoints
│
├── run_native_app(port)      [if PyObjC available]
│   └── AppDelegate
│       ├── Menu bar          → live CPU/RAM/Temp/Power
│       ├── Tray menu         → Dashboard / Start / Stop / Update / Quit
│       └── WKWebView         → embedded dashboard
│
├── check_for_updates()       → GitHub Releases API
├── self_update()             → download + replace + os.execv
└── create_app_launcher()     → .app bundle + icon cache nuke
```

---

## System Detection

**Function:** `detect_system()` (lines 29–58)

Returns dict with: `arch`, `cores`, `cpu_brand`, `gpu`, `ram_gb`, `model`, `os_ver`, `is_intel`

Sources: `platform.machine()`, `sysctl`, `system_profiler SPDisplaysDataType`

---

## Temperature Sensor

**Lines:** 59–142

Inline C source compiled at runtime via `clang -framework IOKit -framework CoreFoundation`.

| Platform | Method |
|----------|--------|
| Apple Silicon | IOKit HID API (`IOHIDEventSystemClient`) — reads all `AppleSilicon*` sensors |
| Intel | Falls back to `powermetrics --samplers smc` |

Binary compiled to `/tmp/macstress_temp_sensor`, runs in `_sensor_loop` thread.

---

## Stress Workers

**Lines:** 146–216

| Worker | Function | Mechanism | Stop |
|--------|----------|-----------|------|
| CPU | `cpu_stress_worker(stop_event, core_id, is_intel)` | `math.sin/cos` loop; Intel: `yes > /dev/null` | `threading.Event` |
| GPU | `gpu_stress_worker(stop_event, sys_info)` | Metal compute shader via PyObjC | `threading.Event` |
| Memory | `memory_stress_worker(stop_event, target_gb)` | `mmap` alloc + continuous read/write | `threading.Event` |
| Disk | `disk_stress_worker(stop_event, worker_id)` | `tempfile` 256MB write/read cycles | `threading.Event` |

All workers run as daemon threads. → See [Stress Manager](#stress-manager) for orchestration.

---

## Metrics Collector

**Class:** `MetricsCollector` (lines 220–446)

### Threads

| Thread | Interval | Data |
|--------|----------|------|
| `_collect_loop` | 2s | CPU %, RAM GB, Swap, Disk I/O |
| `_sensor_loop` | 1.5s | CPU/GPU temperature (°C) |
| `_powermetrics_loop` | 3s | CPU/GPU/Total power (W) |

### Snapshot Dict Keys

`cpu_usage`, `cpu_temp`, `gpu_temp`, `mem_used_gb`, `mem_total_gb`, `swap_used_gb`, `swap_total_gb`, `disk_read_mbs`, `disk_write_mbs`, `cpu_power_w`, `gpu_power_w`, `total_power_w`

### Data Sources

| Metric | Command |
|--------|---------|
| CPU % | `ps -A -o %cpu` / core count |
| RAM | `vm_stat` (pages → GB) |
| Swap | `sysctl vm.swapusage` |
| Disk I/O | `iostat -d -c 2` |
| Temp | Compiled C binary (IOKit HID) |
| Power | `powermetrics` via `osascript` sudo |

---

## Dashboard

**Lines:** 448–738. Single `DASHBOARD_HTML` string with embedded CSS + JS.

### Tiles

CPU Usage · Memory · Temperature (arc gauges) · Power · Disk I/O · System Info (+ update button) · Disk Benchmark

### Features

- Drag & drop tile reorder with animations
- SVG arc gauges for temperature
- Canvas sparkline charts for CPU/RAM history
- SSE live updates (1s interval)
- Update check + one-click auto-update button

### Key JS Functions

| Function | Purpose |
|----------|---------|
| `upd(metrics)` | Update all tile values |
| `ch(id, data, col, mx)` | Draw sparkline canvas |
| `ga(arc, val, bg, temp, max, col)` | Update SVG arc gauge |
| `mkC(active)` | Create control buttons |
| `tog(btn)` | Toggle single test |
| `tA(on)` | Toggle all tests |
| `checkUpd()` | Check for updates |
| `doUpdate(btn, ver)` | Trigger auto-update |
| `diskBench()` | Run disk benchmark |
| `sse()` | Start SSE connection |

---

## Stress Manager

**Class:** `StressManager` (lines 740–819)

Thread-safe test orchestrator.

| Method | Action |
|--------|--------|
| `start_test(name)` | Start single test ("cpu"/"gpu"/"memory"/"disk") |
| `stop_test(name)` | Stop single test |
| `toggle(name)` | Toggle test on/off |
| `start_all(duration=600)` | Start all 4 tests with auto-stop timer |
| `stop_all()` | Stop everything |
| `get_active()` | Return list of active test names |

Auto-stop via `threading.Timer`. → Workers defined in [Stress Workers](#stress-workers).

---

## Web Server & API

**Lines:** 822–918. `ThreadedHTTPServer` on port `9630`.

### Endpoints

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET | `/` | — | Dashboard HTML |
| GET | `/events` | — | SSE: `{metrics, active, sys_info}` |
| GET | `/api/status` | — | JSON snapshot |
| GET | `/api/check_update` | — | `{has_update, latest, current, url}` |
| GET | `/api/disk_bench_result` | — | `{running, results[]}` |
| POST | `/api/toggle` | `{test, action}` | `{ok, active}` |
| POST | `/api/toggle_all` | `{action, duration?}` | `{ok, active}` |
| POST | `/api/disk_bench` | — | `{ok, status}` |
| POST | `/api/do_update?ver=X` | — | `{ok, error?}` |

### SSE Event Format

```json
{
  "metrics": { "cpu_usage": 45.2, "cpu_temp": 52.3, "mem_used_gb": 12.4, ... },
  "active": ["cpu", "memory"],
  "sys_info": { "arch": "arm64", "cores": 10, "ram_gb": 16, ... }
}
```

---

## Native macOS App

**Function:** `run_native_app(port)` (lines 922–1106)

Requires PyObjC. Falls back to browser if unavailable.

### AppDelegate

| Selector | Action |
|----------|--------|
| `applicationDidFinishLaunching_` | Create menu bar + tray menu |
| `checkUpdate_` | Update check alert → auto-update |
| `updateMenuBar_` | Refresh stats every 2s |
| `openDashboard_` | Open/focus WKWebView window |
| `startAll_` / `stopAll_` | Stress test control |
| `quit_` | Graceful shutdown |

**Menu bar format:** `CPU 56%  RAM 84%  52°C  17.1W`

**Policy:** `NSApplicationActivationPolicyAccessory` (no dock icon)

---

## Disk Benchmark

**Lines:** 1108–1162. 4-pass `dd`-based test.

| Pass | Block Size | Total | Measures |
|------|-----------|-------|----------|
| Seq 1MB | 1m × 512 | 512 MB | Write + Read MB/s |
| Seq 256K | 256k × 1024 | 256 MB | Write + Read MB/s |
| Seq 64K | 64k × 2048 | 128 MB | Write + Read MB/s |
| Rnd 4K | 4k × 8192 | 32 MB | Write + Read MB/s |

Runs in background thread. Results polled via `/api/disk_bench_result`.

---

## Auto-Update

**Lines:** 1214–1292

### Flow

```
check_for_updates() → GitHub Releases API → (has_update, latest_ver)
    │
    ▼
self_update(target_ver)
    │ Download from raw.githubusercontent.com/v{tag}/macstress.py
    │ ast.parse() → syntax validation
    │ regex VERSION extract → newer check
    │ os.replace() → atomic file swap
    ▼
os.execv() → process restart
```

**Key:** downloads from release tag URL (not `main` branch) to avoid CDN cache (3-5 min delay).

### Trigger Points

| Where | Mechanism |
|-------|-----------|
| Dashboard | `checkUpd()` → `doUpdate(btn, ver)` → `POST /api/do_update?ver=X` |
| Tray menu | `checkUpdate_` → NSAlert → `self_update(target_ver=latest)` |

---

## App Launcher & Icon

**Function:** `create_app_launcher(app_type)` (lines 1297–1416)

Creates `.app` bundle in `~/Applications/`:

```
MacStress.app/
└── Contents/
    ├── MacOS/MacStress       ← bash launcher (opens Terminal)
    ├── Resources/macstress.icns  ← icon (squircle, alpha)
    └── Info.plist            ← bundle metadata
```

### Icon Cache Clearing

1. `lsregister -u` (unregister old bundle)
2. `getconf DARWIN_USER_CACHE_DIR` → clear `com.apple.dock.iconcache` + `com.apple.iconservices`
3. `find /private/var/folders/` (no sudo)
4. Clear `~/Library/Caches/com.apple.iconservices.store`
5. `killall iconservicesd`
6. `lsregister -f` (re-register)
7. Touch `.app` + `Info.plist`
8. `defaults write com.apple.dock ResetLaunchPad`
9. `killall Dock Finder`

---

## Main Entry Point

**Function:** `main()` (lines 1421–1537)

### CLI Arguments

| Arg | Action |
|-----|--------|
| `--install` | Create .app bundle and exit |
| `--lite` | Create Lite .app bundle |
| `--check-update` | Check for updates and exit |
| `--update` | Run auto-update |
| (none) | Start full app |

### Startup Sequence

1. Parse args → `detect_system()`
2. `compile_temp_sensor()` (Apple Silicon)
3. `_pre_elevate_sudo()` → native password dialog
4. `MetricsCollector.start()`
5. `ThreadedHTTPServer` on port 9630
6. Try `run_native_app(port)` (PyObjC)
7. Fallback: `webbrowser.open(url)`

### Shutdown

Signal handlers (`SIGINT`, `SIGTERM`) → `cleanup()` → stop metrics, stop stress tests, shutdown server.

---

## System Commands Reference

| Command | Purpose | Used by |
|---------|---------|---------|
| `ps -A -o %cpu` | CPU usage | `_collect_loop` |
| `vm_stat` | Memory pages | `_collect_loop` |
| `sysctl vm.swapusage` | Swap usage | `_collect_loop` |
| `iostat -d -c 2` | Disk I/O | `_collect_loop` |
| `powermetrics` | Power/temp | `_powermetrics_loop` |
| `clang` | Compile temp sensor | `compile_temp_sensor` |
| `dd` | Disk benchmark | `_dd_bench` |
| `osascript` | Sudo dialog | `_pre_elevate_sudo` |
| `lsregister` | Icon cache | `create_app_launcher` |
| `getconf DARWIN_USER_CACHE_DIR` | Cache path | `create_app_launcher` |

## Ports & Paths

| Resource | Location |
|----------|----------|
| HTTP server | `localhost:9630` |
| Temp sensor binary | `/tmp/macstress_temp_sensor` |
| App bundle | `~/Applications/MacStress.app` |
| Icon source | `icons/macstress.icns` |
