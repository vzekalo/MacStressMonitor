# MacStress — Documentation

## Contents

| Document | Description |
|----------|-------------|
| [Full Version](full-version.md) | `macstress.py` — architecture, API, components |
| [Lite Version](lite-version.md) | `macstress_lite.sh` — bash version, structure |

## Overview

MacStress is a macOS stress testing and system monitoring tool. It ships in two variants:

- **Full** (`macstress.py`, 1537 lines) — Python single-file app with web dashboard, native menu bar, Metal GPU stress, auto-update
- **Lite** (`macstress_lite.sh`, 460 lines) — Pure bash, zero dependencies, works on any Mac from 2010+

## Project Files

| File | Purpose |
|------|---------|
| `macstress.py` | Full version — single-file Python app |
| `macstress_lite.sh` | Lite version — pure bash |
| `install.sh` | Universal installer (downloads Python, PyObjC) |
| `build_app.sh` | PyInstaller .app builder |
| `setup.py` | Python package config |
| `icons/*.icns` | App icons (squircle, alpha, 10 sizes) |
| `icons/*.png` | Source PNGs |

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.4.5 | 2026-02-18 | Sync lite version, icon cache fix (no sudo) |
| 1.4.4 | 2026-02-18 | Rounded macOS squircle icon with alpha |
| 1.4.3 | 2026-02-18 | Lite: background disk I/O, auto-update |
| 1.4.2 | 2026-02-18 | Fix auto-update CDN cache |
| 1.4.0 | 2026-02-18 | Auto-update: download, replace, restart |
| 1.3.3 | 2026-02-18 | Fix metrics collection blocking |
| 1.3.2 | 2026-02-18 | Fix update check, UX hint bar |

## Quick Links

- **GitHub:** [vzekalo/MacStressMonitor](https://github.com/vzekalo/MacStressMonitor)
- **Dashboard:** `http://localhost:9630`
- **License:** MIT
