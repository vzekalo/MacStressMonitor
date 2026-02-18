# 🔥 MacStress — Native macOS Stress Test & System Monitor

Real-time system monitoring + stress testing for macOS, built with Python & PyObjC.

![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-macOS-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-yellow)
![Arch](https://img.shields.io/badge/arch-Apple%20Silicon%20%7C%20Intel-orange)

## ⚡ One-Line Install & Run

**Standalone app — ніяких залежностей:**

```bash
curl -fsSL https://github.com/vzekalo/MacStressMonitor/releases/download/v1.0.0/MacStress.zip -o /tmp/MacStress.zip && unzip -o /tmp/MacStress.zip -d /Applications && open /Applications/MacStress.app
```

> ⚠️ Apple Silicon only (M1/M2/M3/M4). For Intel use:
> ```bash
> bash <(curl -fsSL https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/install.sh)
> ```

## ✨ Features

- **System Monitor** — CPU, RAM, Swap, Disk I/O with live charts
- **Temperature Sensors** — CPU & GPU via IOKit HID (no sudo needed)
- **Power Consumption** — CPU/GPU/Total watts via `powermetrics` (admin prompt)
- **Stress Tests** — CPU, GPU (Metal), Memory, Disk I/O with timer
- **Native macOS App** — Menu bar status item + WKWebView dashboard
- **Drag & Drop Tiles** — Reorder dashboard tiles with animations
- **Apple Silicon + Intel** — Optimized for both architectures

## 📸 Dashboard

The web dashboard runs on `http://localhost:9630` and shows:

| Tile | Metrics |
|------|---------|
| CPU Usage | Usage %, load average, per-core charts |
| Temperatures | CPU & GPU °C with circular gauges |
| Power | CPU / GPU / Total watts |
| Memory | Used %, GB breakdown, pressure |
| Swap | SSD→RAM swap usage & pressure bar |
| Disk I/O | Read / Write MB/s with live chart |
| System Info | Model, OS, CPU, GPU, Architecture |

## 🖥 Menu Bar

Live stats in your menu bar: `CPU 56%  RAM 84%  52°C  17.1W`

## 🚀 Usage

### Quick Start
```bash
python3 macstress.py
```

### Build .app Bundle
```bash
chmod +x build_app.sh
./build_app.sh
open MacStress.app
```

### Requirements
- macOS 11+ (Big Sur or later)
- Python 3.8+
- PyObjC (auto-installed for native app)

## 🔐 Admin Access

Power consumption monitoring requires `powermetrics`, which needs admin privileges.
MacStress uses `osascript` to request access with a native password dialog — 
the password is cached by macOS for several minutes after the first entry.

## 📄 License

MIT
