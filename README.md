# 🔥 MacStress — macOS Stress Test & System Monitor

Real-time system monitoring + stress testing for macOS.

![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-macOS-blue)
![Arch](https://img.shields.io/badge/arch-Apple%20Silicon%20%7C%20Intel-orange)

## ⚡ MacStress Lite — Zero Dependencies (Recommended)

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

Full-featured version with web dashboard, menu bar, Metal GPU stress, and drag & drop tiles.

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

### Standalone App (Apple Silicon only):

```bash
curl -fsSL https://github.com/vzekalo/MacStressMonitor/releases/download/v1.0.0/MacStress.zip -o /tmp/MacStress.zip && unzip -o /tmp/MacStress.zip -d /Applications && open /Applications/MacStress.app
```

### Full Features:
- **Web Dashboard** on `http://localhost:9630` with live charts
- **Temperature Sensors** — CPU & GPU via IOKit HID
- **Power Consumption** — CPU/GPU/Total watts via `powermetrics`
- **Stress Tests** — CPU, GPU (Metal), Memory, Disk I/O
- **Menu Bar** — Live stats: `CPU 56%  RAM 84%  52°C  17.1W`
- **Drag & Drop Tiles** — Reorder dashboard with animations

### Compatibility:

| macOS | Python Source | Mode |
|-------|-------------|------|
| 14+ (Sonoma) | System / CLT | Full native app |
| 11-13 (Big Sur–Ventura) | CLT / python.org | Full native app |
| 10.15 (Catalina) | python.org 3.12 | Full native app |
| 10.9-10.14 (Mavericks–Mojave) | python.org 3.9 | Web-only dashboard |
| 10.8 (Mountain Lion) | python.org 3.7 | Web-only dashboard |

### Requirements:
- macOS 10.8+ (Mountain Lion or later)
- Internet connection (for first install)
- No App Store, no Homebrew needed

---

## 🔐 Admin Access

Temperature and power monitoring use `powermetrics`, which requires admin privileges.

- **Lite version**: asks for password once at startup via `sudo`
- **Full version**: creates a sudoers rule (one-time password dialog)

## 📄 License

MIT
