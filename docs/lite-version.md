# MacStress Lite — Architecture & Reference

> `macstress_lite.sh` — 460 lines, pure bash, zero dependencies  
> [← Back to Index](index.md) · [Full Version →](full-version.md)

---

## Table of Contents

- [Overview](#overview)
- [Setup & Initialization](#setup--initialization)
- [Metrics Collection](#metrics-collection)
- [Stress Tests](#stress-tests)
- [Disk Benchmark](#disk-benchmark)
- [Auto-Update](#auto-update)
- [App Installer](#app-installer)
- [Main Loop & Display](#main-loop--display)
- [Key Differences from Full Version](#key-differences-from-full-version)

---

## Overview

```
macstress_lite.sh
├── Setup: colors, sysctl, sudo prompt
├── Powermetrics: background daemon + parser
├── Background disk I/O: async iostat → temp file
├── Main loop (3s interval):
│   ├── Collect: ps, vm_stat, sysctl, iostat
│   ├── Display: tput cursor positioning, color bars
│   └── Input: single-key commands
├── Stress: s_cpu, s_mem, s_disk, s_all
├── Benchmark: 4-pass dd test
├── Update: GitHub API → download → exec restart
└── Install: create .app bundle
```

---

## Setup & Initialization

**Lines:** 1–48

| Variable | Source | Purpose |
|----------|--------|---------|
| `VERSION` | hardcoded | Current version |
| `MODEL` | `sysctl -n hw.model` | Mac model |
| `CPU_BRAND` | `sysctl -n machdep.cpu.brand_string` | CPU name |
| `CORES` | `sysctl -n hw.ncpu` | Core count |
| `RAM_GB` | `sysctl -n hw.memsize` / 1GB | Total RAM |
| `OS_VER` | `sw_vers -productVersion` | macOS version |
| `ARCH` | `uname -m` | arm64 / x86_64 |

**Sudo:** prompts via `sudo -v < /dev/tty` for temperature/power access.

---

## Metrics Collection

### Powermetrics (lines 49–78)

Background daemon: `sudo powermetrics --samplers {smc|cpu_power,gpu_power} -i 3000`

Parser thread reads `/tmp/macstress_pm_raw` every 4s, writes key=value to `/tmp/macstress_pm_data`.

| Key | Parsed from |
|-----|-------------|
| `cpu_temp` | "die temperature" / "thermal level" (CPU) |
| `gpu_temp` | "die temperature" / "thermal level" (GPU) |
| `cpu_power` | "cpu power" / "package power" / "intel energy" |
| `gpu_power` | "gpu power" |

### Disk I/O (lines 332–352)

**Background process** writes to `/tmp/macstress_dio` every 4s. Main loop reads from file (non-blocking).

```
iostat -d -c 2 → tail -1 → R:{read} W:{write} MB/s → /tmp/macstress_dio
```

### Inline Metrics (main loop)

| Metric | Command | Inline |
|--------|---------|--------|
| CPU % | `ps -A -o %cpu` / cores | Yes |
| RAM | `vm_stat` → `parse_vm()` | Yes |
| Swap | `sysctl vm.swapusage` | Yes |
| Load | `sysctl -n vm.loadavg` | Yes |
| Battery | `pmset -g batt` | Yes |
| Disk I/O | `/tmp/macstress_dio` | Async |
| Temp/Power | `/tmp/macstress_pm_data` | Async |

---

## Stress Tests

**Lines:** 106–167

| Function | Test | Mechanism | Default Duration |
|----------|------|-----------|-----------------|
| `s_cpu` | CPU | Infinite `while :; do :; done` × cores | 120s |
| `s_mem` | RAM | `dd` 64MB chunks from `/dev/urandom` → continuous `cat` | 120s |
| `s_disk` | Disk | `dd` 256MB write/read cycles | 120s |
| `s_all` | ALL | Phase 1: benchmark → Phase 2: CPU+RAM+Disk combined | 180s |

All workers tracked via `$SPIDS`. Auto-stop via background `sleep $d; kill`.

**Cleanup:** `stop_s()` kills all PIDs, removes `/tmp/macstress_mem_*`, `/tmp/macstress_disk_*`.

---

## Disk Benchmark

**Lines:** 169–243

### Passes

| Pass | Block Size | Count | Total |
|------|-----------|-------|-------|
| Seq 1MB | 1m | 512 | 512 MB |
| Seq 256K | 256k | 1024 | 256 MB |
| Seq 64K | 64k | 2048 | 128 MB |
| Rnd 4K | 4k | 8192 | 32 MB |

### Timing

Uses `perl -MTime::HiRes` for millisecond precision. Falls back to `date +%s` (second precision).

`sudo purge` between write and read to clear disk cache.

---

## Auto-Update

**Lines:** 264–330

### Flow

```
[u] key pressed
    │
    ▼
check_updates()
    │ curl GitHub Releases API → latest tag
    │ Semantic version comparison (major.minor.patch)
    ▼
"Нова версія: v1.4.5 (поточна: v1.4.2)"
"Оновити зараз? [y/N]"
    │
    ▼ [y]
curl raw.githubusercontent.com/v{latest}/macstress_lite.sh → /tmp/
    │ Verify: grep VERSION, grep bash
    │ cp → script path, chmod +x
    ▼
exec bash "$my_path" → restart with new version
```

**Key:** downloads from release tag URL (not `main`) to avoid CDN cache.

---

## App Installer

**Function:** `install_app()` (lines 293–326)

Creates `~/Applications/MacStress Lite.app`:

```
MacStress Lite.app/
└── Contents/
    ├── MacOS/MacStressLite  ← bash: osascript → Terminal
    └── Info.plist           ← bundle metadata
```

> **Note:** Lite .app does NOT include icon (no icons dir when run from `/tmp/`). Use Full version for icon support.

---

## Main Loop & Display

**Lines:** 360–460

### Display Layout (tput cursor positioning)

```
  * MacStress Lite v1.4.5
  ================================================
  Model   MacBookAir9,1
  CPU     Apple M1
  Cores   8   RAM  16 GB   macOS  15.3 (arm64)
  ================================================
  Controls:
  [1] CPU  [2] RAM  [3] Disk  [4] ALL
  [5] Bench [u] Update [i] Install [x] Stop [q] Quit
  ================================================

  CPU    45.2%  [#########...........]        ← line 13+
  RAM    67.1%  [#############.......]  10.7/16GB
  Disk   R:125.3 W:89.7 MB/s  Batt 85%
  Swap   0.5 MB  Load 3.21
  Temp   CPU:52.3C GPU:48.1C Pwr:8.5W GPU:3.2W
  Test   CPU (8 cores) 95s left
  Bench  Seq 1MB   Write:  512 MB/s  Read:  890 MB/s
  ------------------------------------------------
```

### Loop Timing

- `read -t 3 -n 1 key` — 3s timeout, single keypress
- Disk I/O from background cache file (no blocking)
- Powermetrics from background parser (no blocking)

### Key Bindings

| Key | Action |
|-----|--------|
| `1` | `s_cpu 120` |
| `2` | `s_mem 512 120` |
| `3` | `s_disk 120` |
| `4` | `s_all 180` |
| `5` | `disk_bench` (interactive) |
| `u` | `check_updates` |
| `i` | `install_app` |
| `x` | `stop_s` |
| `q` | `exit 0` → cleanup trap |

---

## Key Differences from Full Version

| Feature | Full (`macstress.py`) | Lite (`macstress_lite.sh`) |
|---------|----------------------|---------------------------|
| **Dependencies** | Python 3, PyObjC (optional) | bash 3.2 only |
| **UI** | Web dashboard + menu bar | Terminal TUI |
| **GPU Stress** | ✅ Metal compute shader | ❌ |
| **Temperature** | IOKit HID (Apple Silicon) | powermetrics only |
| **Charts** | Canvas sparklines + SVG arcs | ASCII progress bars |
| **Drag & Drop** | ✅ Tile reorder | ❌ |
| **Auto-Update** | Dashboard button + tray alert | `[u]` key + y/N prompt |
| **Icon** | ✅ .icns with cache nuke | ❌ No icon support |
| **Compatibility** | macOS 10.8+ | macOS 10.8+ |
| **File size** | ~75 KB | ~18 KB |

---

## Temp Files

| Path | Purpose | Cleanup |
|------|---------|---------|
| `/tmp/macstress_pm_data` | Powermetrics parsed values | On exit |
| `/tmp/macstress_pm_raw` | Powermetrics raw output | On exit |
| `/tmp/macstress_dio` | Cached disk I/O reading | On exit |
| `/tmp/macstress_mem_*` | Memory stress chunks | On stop/exit |
| `/tmp/macstress_disk_*` | Disk stress files | On stop/exit |
| `/tmp/macstress_bench_*` | Benchmark temp files | On stop/exit |
