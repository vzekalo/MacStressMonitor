# 🔥 MacStress — macOS Stress Test & System Monitor

Real-time system monitoring + stress testing for macOS.  
Native menu bar app with web dashboard, disk benchmarks, and auto-update.

![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-macOS-blue)
![Arch](https://img.shields.io/badge/arch-Apple%20Silicon%20%7C%20Intel-orange)
![Version](https://img.shields.io/github/v/release/vzekalo/MacStressMonitor)

---

## 🚀 Встановлення — один рядок

**Працює на БУДЬ-ЯКОМУ Mac (Apple Silicon + Intel). Без Homebrew, без App Store.**

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/install.sh)
```

> Автоматично: завантажить Python → встановить залежності → створить `.app` → запустить

---

## 📦 Завантажити .app (Apple Silicon)

Готовий додаток — скачай, розпакуй, запусти. **Без Python, без інтернету, без терміналу.**

### [⬇ Скачати MacStress-v1.5.1.zip](https://github.com/vzekalo/MacStressMonitor/releases/latest/download/MacStress-v1.5.1.zip)

> ⚠️ Цей білд для **Apple Silicon** (M1/M2/M3/M4). Для Intel Mac використовуй install.sh вище.

---

## ⚡ MacStress Lite — Zero Dependencies

**Працює на будь-якому Mac (2010+). Тільки bash, нічого не встановлює.**

```bash
curl -fsSL "https://raw.githubusercontent.com/vzekalo/MacStressMonitor/main/macstress_lite.sh" -o /tmp/ms.sh && bash /tmp/ms.sh
```

Моніторинг: CPU · RAM · Swap · Load · Disk I/O · Temperature · Power · Battery  
Керування: `[1]` CPU stress · `[2]` RAM · `[3]` Disk · `[4]` ALL · `[5]` Benchmark · `[u]` Update · `[q]` Quit

---

## 🖥 Можливості

- **Web Dashboard** — `http://localhost:9630` з live-графіками, drag & drop плитками
- **Menu Bar** — живий CPU/RAM/Temp/Power: `CPU 56% RAM 84% 52°C 17.1W`
- **Stress Tests** — CPU, GPU (Metal), Memory, Disk I/O з таймером
- **Disk Benchmark** — Sequential 1MB/256K/64K + Random 4K
- **Temperature** — CPU & GPU via IOKit HID (Apple Silicon) або powermetrics (Intel)
- **Power** — CPU/GPU/Total watts via powermetrics
- **Auto-Update** — one-click з dashboard або tray
- **Локалізація** — українська 🇺🇦

---

## 🔄 Auto-Update

**Dashboard:** Check for Updates → Оновити → завантажує з GitHub release → перевіряє синтаксис → atomic replace → рестарт

**Tray:** Check for Updates... → Оновити → той самий флоу через native alert

**Lite:** `[u]` → `[y/N]` → завантажує → замінює → `exec` рестарт

---

## 📊 Сумісність

| macOS | Режим |
|-------|-------|
| 14+ (Sonoma/Sequoia) | Повний native app |
| 11-13 (Big Sur–Ventura) | Повний native app |
| 10.15 (Catalina) | Повний native app |
| 10.9-10.14 | Web-only dashboard |

---

## 📝 Changelog

| Версія | Зміни |
|--------|-------|
| **1.5.1** | Fix CPU usage & frequency on Apple Silicon M2 Max, WKWebView auto-retry |
| **1.5.0** | Modular package architecture, standalone .app builder, popover details |
| **1.4.4** | Rounded macOS squircle icon + icon cache nuke |
| **1.4.3** | Lite: background disk I/O, auto-update |
| **1.4.0** | Auto-update mechanism: download, replace, restart |

---

## 📁 Структура проекту

```
MacStress/
├── macstress/               # Python package (modular)
│   ├── __main__.py          # Entry point
│   ├── metrics.py           # System metrics (CPU, RAM, disk, temp, power)
│   ├── dashboard.py         # Web dashboard HTML
│   ├── native_app.py        # Native macOS app (menu bar, WKWebView)
│   ├── popover.py           # Menu bar popover
│   ├── server.py            # HTTP server + SSE
│   ├── stress.py            # Stress test workers
│   ├── benchmark.py         # Disk benchmark
│   └── updater.py           # Self-update from GitHub
├── macstress_lite.sh        # Lite version (pure bash, zero deps)
├── install.sh               # Universal installer
├── build_standalone.sh      # Self-contained .app builder
└── icons/                   # App icons (.icns + .png)
```

## 📄 License

MIT
