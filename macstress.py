#!/usr/bin/env python3
"""
MacStress — Native macOS Stress Test + System Monitor
Backward-compatibility wrapper: runs the macstress package.

Usage:
  python3 macstress.py          (menu bar monitor + dashboard)
  sudo python3 macstress.py     (adds power consumption data)
  python3 -m macstress          (preferred new way)
"""
import multiprocessing as mp
mp.set_start_method("fork", force=True)

from macstress.__main__ import main
main()
