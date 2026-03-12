#!/usr/bin/env python3
"""
MacStress — Native macOS Stress Test + System Monitor
Backward-compatibility wrapper: re-execs as 'python3 -m macstress'.

Usage:
  python3 macstress.py          (menu bar monitor + dashboard)
  sudo python3 macstress.py     (adds power consumption data)
  python3 -m macstress          (preferred new way)
"""
import os, sys

# Ensure macstress/ package is findable regardless of CWD
script_dir = os.path.dirname(os.path.abspath(__file__))
env = os.environ.copy()
pp = env.get("PYTHONPATH", "")
env["PYTHONPATH"] = script_dir + (":" + pp if pp else "")

# Re-exec as module to avoid shadowing macstress/ package
os.execve(sys.executable, [sys.executable, "-m", "macstress"] + sys.argv[1:], env)
