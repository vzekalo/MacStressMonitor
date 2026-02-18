# 🔥 MacStress — macOS Stress Test & System Monitor

Real-time system monitoring + stress testing for macOS.  
Single-file Python app with auto-update, web dashboard, native menu bar, and disk benchmarks.

![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-macOS-blue)
![Arch](https://img.shields.io/badge/arch-Apple%20Silicon%20%7C%20Intel-orange)
![Version](https://img.shields.io/github/v/release/vzekalo/MacStressMonitor)

---

## ⚡ MacStress Lite — Zero Dependencies

**Works on ANY Mac (2010+). No Python, no Xcode, nothing to install.**

```bash
curl -fsSL "https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/macstress_lite.sh" -o /tmp/ms.sh && bash /tmp/ms.sh
```

### What it monitors:

| Metric | Source |
|--------|--------|
| CPU Usage | `ps` (real-time %, color bar) |
| RAM Usage | `vm_stat` (active+wired+compressed) |
| Swap | `sysctl vm.swapusage` |
| Load Average | `sysctl vm.loadavg` |
| Disk I/O | `iostat` (live R/W MB/s) |
| Temperature | `powermetrics` (CPU/GPU °C) |
| Power | `powermetrics` (CPU/GPU watts) |
| Battery | `pmset` (charge %) |

### Stress tests:

| Key | Test | Duration |
|-----|------|----------|
| `[1]` | CPU — all cores 100% | 2 min |
| `[2]` | RAM — allocate 512MB | 2 min |
| `[3]` | Disk — continuous R/W 256MB | 2 min |
| `[4]` | ALL — disk bench (4 sizes) + CPU+RAM+Disk stress | 3 min |
| `[5]` | Disk Benchmark — Seq 1MB/256K/64K + Rnd 4K | ~30s |
| `[x]` | Stop stress test | — |
| `[q]` | Quit | — |

### Requirements:
- macOS 10.8+ (any Mac from 2010)
- bash 3.2+ (built into macOS)
- Admin password (one-time, for temperature/power)

---

## 🖥 MacStress Full — Native macOS App

Full-featured version with web dashboard, menu bar, Metal GPU stress, drag & drop tiles, and auto-update.

### Universal Install (any Mac):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/install.sh)
```

The installer automatically:
1. **Downloads portable Python** from GitHub (`python-build-standalone`) — no `.pkg`, no `installer`, no admin
2. **Extracts to `~/.macstress/python/`** — fully self-contained, no system changes
3. **Bootstraps pip** — from `ensurepip` or GitHub
4. **Tries PyObjC** — for native menu bar; if it fails → web-only dashboard in browser
5. **Creates `~/.macstress/launch.sh`** — for easy re-launch
6. **Creates `.app` bundle** in `~/Applications/` with custom icon

### Full Features:
- **Web Dashboard** on `http://localhost:9630` with live charts
- **Temperature Sensors** — CPU & GPU via IOKit HID
- **Power Consumption** — CPU/GPU/Total watts via `powermetrics`
- **Stress Tests** — CPU, GPU (Metal), Memory, Disk I/O
- **Disk Benchmark** — Sequential (1MB, 256K, 64K) + Random 4K read/write
- **Menu Bar** — Live stats: `CPU 56%  RAM 84%  52°C  17.1W`
- **Drag & Drop Tiles** — Reorder dashboard with animations
- **Auto-Update** — one-click update from the dashboard or menu bar (see below)
- **Localization** — Ukrainian UI 🇺🇦

---

## 🔄 Auto-Update

MacStress can update itself with zero manual steps.

### From the Dashboard:
1. Click **🔄 Check for Updates** in the System Info tile
2. If a new version is available, click **⬇ Оновити**
3. The app downloads the latest `macstress.py`, validates it, replaces the file, and restarts automatically

### From the Menu Bar / Tray:
1. Click the MacStress tray icon → **Check for Updates...**
2. If a new version is available, click **Оновити** in the alert dialog
3. App updates and restarts

### How it works:
1. Fetches `macstress.py` from `raw.githubusercontent.com`
2. Validates the downloaded file has correct Python syntax (`ast.parse`)
3. Verifies the version is actually newer than the current one
4. Atomically replaces the local file (`os.replace`)
5. Restarts the process (`os.execv`)

---

## 🎨 Custom App Icon

MacStress creates a `.app` bundle in `~/Applications/` with a custom icon.

### Replacing the icon:
1. Place your `.icns` file in the `icons/` directory:
   - `icons/macstress.icns` — for the Full version
   - `icons/macstress_lite.icns` — for the Lite version
2. Re-run the app: `python3 macstress.py`

The app automatically:
- Deletes the old `.app` bundle
- Copies the new icon to `Contents/Resources/`
- Clears macOS icon caches (`iconservicesd`, `com.apple.iconservices.store`)
- Unregisters and re-registers with LaunchServices
- Restarts Dock and Finder to refresh icons everywhere

> **Note:** macOS aggressively caches app icons. If the icon doesn't update, try:
> ```bash
> sudo find /var/folders -name "com.apple.iconservices*" -exec rm -rf {} + 2>/dev/null
> killall Dock Finder
> ```

---

## 📊 Compatibility

| macOS | Python Source | Mode |
|-------|-------------|------|
| 14+ (Sonoma) | System / CLT | Full native app |
| 11-13 (Big Sur–Ventura) | CLT / python.org | Full native app |
| 10.15 (Catalina) | python.org 3.12 | Full native app |
| 10.9-10.14 (Mavericks–Mojave) | python.org 3.9 | Web-only dashboard |
| 10.8 (Mountain Lion) | python.org 3.7 | Web-only dashboard |

### Requirements:
- macOS 10.8+ (Mountain Lion or later)
- Internet connection (for first install and updates)
- No App Store, no Homebrew needed

---

## 🔐 Admin Access

Temperature and power monitoring use `powermetrics`, which requires admin privileges.

- **Lite version**: asks for password once at startup via `sudo`
- **Full version**: creates a sudoers rule (one-time password dialog)

---

## 📝 Changelog

### v1.4.1
- Fix: app icon cache — clear `iconservicesd` + `com.apple.iconservices.store` + restart Finder

### v1.4.0
- **Auto-update**: download, replace, restart — zero user effort
- Dashboard + tray: "⬇ Оновити" button instead of "Open GitHub"
- All update UI localized to Ukrainian

### v1.3.3
- Fix: metrics collection loop — `top -l 2` blocked 3-5s, `iostat` hung indefinitely
- Replaced with fast `ps -A -o %cpu` (0.04s) and fixed `iostat` arguments

### v1.3.2
- Fix: "Check for Updates" — `check_for_updates()` returns tuple, callers now unpack correctly
- UX hint bar: inline explanation of stress test controls

### v1.3.1
- Fix: "Check for Updates" menu — added missing `NSAlert` import
- Fix: CPU metrics — interval-based measurement via `top`
- Fix: Disk I/O — proper 1s interval sampling
- Disk Benchmark tile with industry-standard file sizes
- Memory worker: reduced I/O contention
- SSE: 1s update interval for less overhead

---

## 📄 License

MIT
