# MacStress — Table of Contents

> Token-friendly documentation index. Each section maps to a code region in `macstress.py` or `macstress_lite.sh`.

## Full Version (`macstress.py` — 1537 lines)

### Core Architecture

| # | Section | Lines | Description |
|---|---------|-------|-------------|
| 1 | [Imports & Constants](#1-imports--constants) | 1–26 | Stdlib imports, VERSION, GITHUB_REPO |
| 2 | [System Detection](#2-system-detection) | 29–58 | `detect_system()` — arch, cores, RAM, GPU, model |
| 3 | [Temperature Sensor](#3-temperature-sensor) | 59–142 | IOKit HID C source, `compile_temp_sensor()` |
| 4 | [Stress Workers](#4-stress-workers) | 146–216 | CPU, GPU (Metal), Memory, Disk workers |
| 5 | [Metrics Collector](#5-metrics-collector) | 220–446 | `MetricsCollector` class — CPU/RAM/Disk/Temp/Power |
| 6 | [HTML Dashboard](#6-html-dashboard) | 448–738 | Single-page app: CSS, tiles, charts, JS |
| 7 | [Stress Manager](#7-stress-manager) | 740–819 | `StressManager` class — start/stop/toggle tests |
| 8 | [Web Server](#8-web-server) | 822–918 | `Handler` (HTTP) — SSE, REST API endpoints |
| 9 | [Native macOS App](#9-native-macos-app) | 922–1106 | PyObjC `AppDelegate` — menu bar, WKWebView |
| 10 | [Disk Benchmark](#10-disk-benchmark) | 1108–1162 | 4-pass dd benchmark (Seq 1MB/256K/64K + Rnd 4K) |
| 11 | [Sudo Pre-Elevation](#11-sudo-pre-elevation) | 1166–1210 | Native macOS password dialog via osascript |
| 12 | [Update System](#12-update-system) | 1214–1292 | `check_for_updates()`, `self_update()` |
| 13 | [App Launcher](#13-app-launcher) | 1297–1416 | `create_app_launcher()` — .app bundle + icon cache |
| 14 | [Main](#14-main) | 1421–1537 | CLI args, server start, signal handling |

### Lite Version (`macstress_lite.sh` — 460 lines)

| # | Section | Lines | Description |
|---|---------|-------|-------------|
| L1 | Setup & Password | 1–48 | Version, colors, system info, sudo prompt |
| L2 | Powermetrics | 49–78 | Background powermetrics + parser |
| L3 | Stress Functions | 80–167 | `s_cpu`, `s_mem`, `s_disk`, `s_all` |
| L4 | Disk Benchmark | 169–243 | `run_dd_bench`, `disk_bench_quiet`, `disk_bench` |
| L5 | Helpers | 245–263 | `parse_vm`, `bar` (progress bar) |
| L6 | Update System | 264–330 | `check_updates()` with auto-download + exec restart |
| L7 | Background Disk I/O | 332–352 | Async iostat cache (temp file, not blocking) |
| L8 | Main Loop | 360–460 | TUI rendering, key handler, 3s poll |

---

## 1. Imports & Constants

- **Zero external deps** for core (stdlib only)
- PyObjC optional (for native menu bar)
- `VERSION` = semver string, `GITHUB_REPO` = GitHub owner/repo

## 2. System Detection

`detect_system()` returns dict: `arch`, `cores`, `cpu_brand`, `gpu`, `ram_gb`, `model`, `os_ver`, `is_intel`

## 3. Temperature Sensor

- Inline C source compiled at runtime via `clang`
- Uses IOKit HID API (`IOHIDEventSystemClient`)
- Apple Silicon: reads all `AppleSilicon*` sensors
- Intel: falls back to `powermetrics`

## 4. Stress Workers

| Worker | Method | Mechanism |
|--------|--------|-----------|
| CPU | `cpu_stress_worker()` | `math.sin/cos` loops or `yes>/dev/null` (Intel) |
| GPU | `gpu_stress_worker()` | Metal compute shader via PyObjC |
| Memory | `memory_stress_worker()` | `mmap` allocation + continuous read |
| Disk | `disk_stress_worker()` | `tempfile` write/read 256MB blocks |

All workers accept `stop_event` (threading.Event) for graceful shutdown.

## 5. Metrics Collector

**Threads:** `_collect_loop` (CPU/RAM/Disk, 2s), `_sensor_loop` (temp, compiled C binary), `_powermetrics_loop` (power, via sudo)

| Metric | Source | Update |
|--------|--------|--------|
| CPU % | `ps -A -o %cpu` / cores | 2s |
| RAM | `vm_stat` pages → GB | 2s |
| Swap | `sysctl vm.swapusage` | 2s |
| Disk I/O | `iostat -d -c 2` | 2s |
| Temp | IOKit HID C binary | 1.5s |
| Power | `powermetrics` via sudo | 3s |

## 6. HTML Dashboard

Single `DASHBOARD_HTML` string with embedded CSS + JS.

**Tiles:** CPU, Memory, Temperature, Power, Disk I/O, System Info (with update button), Disk Benchmark

**Features:** drag & drop reorder, SVG arc gauges, canvas sparkline charts, SSE live updates

## 7. Stress Manager

`StressManager` — thread-safe test orchestrator. Methods: `start_test(name)`, `stop_test(name)`, `toggle(name)`, `start_all(duration)`, `stop_all()`

Auto-stop timer via `threading.Timer`.

## 8. Web Server

`ThreadedHTTPServer` + `Handler` on port 9630.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Dashboard HTML |
| GET | `/events` | SSE stream (1s interval) |
| GET | `/api/status` | JSON snapshot |
| GET | `/api/check_update` | Version check |
| POST | `/api/toggle` | Start/stop single test |
| POST | `/api/toggle_all` | Start/stop all tests |
| POST | `/api/disk_bench` | Start benchmark |
| GET | `/api/disk_bench_result` | Poll benchmark results |
| POST | `/api/do_update?ver=X` | Trigger auto-update |

## 9. Native macOS App

`run_native_app(port)` — PyObjC `AppDelegate` with:
- **Menu bar** status item with live stats (2s timer)
- **Tray menu:** Dashboard, Start All, Stop All, Check for Updates, Quit
- **WKWebView** window loading `localhost:{port}`
- `NSApplicationActivationPolicyAccessory` (no dock icon)

## 10. Disk Benchmark

4-pass `dd`-based benchmark:

| Pass | Block Size | Count | Total |
|------|-----------|-------|-------|
| Seq 1MB | 1m | 512 | 512 MB |
| Seq 256K | 256k | 1024 | 256 MB |
| Seq 64K | 64k | 2048 | 128 MB |
| Rnd 4K | 4k | 8192 | 32 MB |

Results: write MB/s, read MB/s per pass.

## 11. Sudo Pre-Elevation

`_pre_elevate_sudo()` — native macOS password dialog via `osascript 'do shell script ... with administrator privileges'`. Returns password for `sudo -S` piping.

## 12. Update System

- `_ver_tuple(v)` — `"1.4.4"` → `(1, 4, 4)`
- `check_for_updates()` — GitHub Releases API → compare versions
- `self_update(target_ver)` — download from tag URL → `ast.parse` → `os.replace` → caller does `os.execv`

## 13. App Launcher

`create_app_launcher(app_type)` — creates `.app` bundle in `~/Applications/`:
- `Contents/MacOS/{name}` — bash launcher (opens Terminal)
- `Contents/Resources/{name}.icns` — icon from `icons/` dir
- `Contents/Info.plist` — bundle metadata

Icon cache nuke: lsregister unregister/register, clear `/var/folders/` + `iconservices.store`, kill `iconservicesd`, reset Launchpad DB, restart Dock + Finder.

## 14. Main

CLI argument parsing → system detection → metrics collector → stress manager → web server → native app (or browser fallback). Signal handlers for graceful shutdown.
