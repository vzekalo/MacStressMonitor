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

### Monitors:
CPU · RAM · Swap · Load · Disk I/O · Temperature · Power · Battery

### Controls:
`[1]` CPU stress · `[2]` RAM · `[3]` Disk · `[4]` ALL · `[5]` Benchmark · `[u]` Update · `[i]` Install .app · `[x]` Stop · `[q]` Quit

### Requirements:
- macOS 10.8+, bash 3.2+, admin password for temp/power

---

## 🖥 MacStress Full — Native macOS App

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/install.sh)
```

### Features:
- **Web Dashboard** — `http://localhost:9630` with live charts, drag & drop tiles
- **Menu Bar** — live CPU/RAM/Temp/Power: `CPU 56% RAM 84% 52°C 17.1W`
- **Stress Tests** — CPU, GPU (Metal), Memory, Disk I/O with timer
- **Disk Benchmark** — Sequential 1MB/256K/64K + Random 4K
- **Temperature** — CPU & GPU via IOKit HID (Apple Silicon) or powermetrics (Intel)
- **Power** — CPU/GPU/Total watts via powermetrics
- **Auto-Update** — one-click from dashboard or tray (see below)
- **Localization** — Ukrainian UI 🇺🇦

### Installer does:
1. Downloads portable Python (`python-build-standalone`)
2. Extracts to `~/.macstress/python/` (no system changes)
3. Installs PyObjC for native menu bar (falls back to web-only)
4. Creates `.app` bundle in `~/Applications/` with custom icon

---

## 🔄 Auto-Update

### Dashboard:
**Check for Updates** → **⬇ Оновити** → downloads from release tag → validates syntax → atomic replace → restarts

### Tray:
**Check for Updates...** → **Оновити** → same flow via native alert

### Lite:
`[u]` → detects version → `[y/N]` → downloads → replaces → `exec` restart

### Technical:
1. Fetches from `raw.githubusercontent.com/v{tag}/macstress.py` (not `main` — CDN caches for 3-5 min)
2. `ast.parse()` validates syntax
3. `os.replace()` atomic file swap
4. `os.execv()` process restart

---

## 🎨 App Icon

Rounded macOS squircle with alpha transparency. All 10 sizes (16–1024px).

**Custom icon:** replace `icons/macstress.icns` and reinstall `.app`.

Icon cache fix runs automatically: clears `/var/folders/` icon caches, kills `iconservicesd`, resets Launchpad DB, restarts Dock + Finder.

---

## 📊 Compatibility

| macOS | Mode |
|-------|------|
| 14+ (Sonoma) | Full native app |
| 11-13 (Big Sur–Ventura) | Full native app |
| 10.15 (Catalina) | Full native app |
| 10.9-10.14 | Web-only dashboard |
| 10.8 (Mountain Lion) | Web-only dashboard |

---

## 📝 Changelog

| Version | Changes |
|---------|---------|
| **1.4.4** | Rounded macOS squircle icon with alpha + comprehensive icon cache nuke |
| **1.4.3** | Lite: background disk I/O, auto-update, less flicker |
| **1.4.2** | Fix auto-update CDN cache — download from release tag URL |
| **1.4.0** | Auto-update mechanism: download, replace, restart |
| **1.3.3** | Fix metrics: `top -l 2` blocking, `iostat` hanging |
| **1.3.2** | Fix: Check for Updates tuple unpacking, UX hint bar |
| **1.3.1** | NSAlert import, disk benchmark tile, SSE 1s interval |

---

## 📁 Project Structure

```
MacStress/
├── macstress.py         # Full version (1537 lines, single file)
├── macstress_lite.sh    # Lite version (pure bash, zero deps)
├── install.sh           # Universal installer
├── build_app.sh         # PyInstaller .app builder
├── setup.py             # Python package config
├── icons/               # App icons (.icns + .png)
└── docs/                # Project documentation
    ├── TOC.md           # Table of contents
    └── XREF.md          # Cross-reference / architecture
```

## 📄 License

MIT
